"""Atas da Câmara de Juiz de Fora (reuniões, audiências públicas e demais sessões).

Cada ata é um PDF em https://www.camarajf.mg.gov.br/sal/ata.php?cod=N, com N em sequência.
O robô percorre os números, lê o texto de cada PDF e guarda:
  - data/cache/atas/AAAA.jsonl.gz  texto completo, um arquivo por ano (base para análises);
  - site/dados/atas.json           índice leve lido pela página #/atas.

Uso:
  python scripts/camara_atas.py                         # dia a dia: só o que é novo ou ainda não aprovado
  python scripts/camara_atas.py --inicio 1 --fim 6000   # carga completa (workflow "Atas da Câmara")
  python scripts/camara_atas.py --so-gerar              # só monta site/dados/atas.json a partir do cache
"""
import argparse
import datetime as dt
import gzip
import io
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from camara_agenda import TEMAS, sem_acento  # mesma regra de assuntos da Agenda

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "data" / "cache" / "atas"
SAIDA = RAIZ / "site" / "dados" / "atas.json"
VEREADORES = RAIZ / "data" / "bruto" / "vereadores.json"
URL = "https://www.camarajf.mg.gov.br/sal/ata.php?cod={}"
H = {"User-Agent": "Mozilla/5.0 (RadarJF; robo de transparencia)"}

PAUSA = float(os.environ.get("RADAR_PAUSA_ATAS", "1.0"))  # coleta devagar, para não pesar na Câmara
SEM_ATA_PARA_PARAR = 60  # números seguidos sem ata depois da última conhecida = chegamos ao fim
REVISAR = 40             # revisita as últimas (a ata passa de "não aprovada" para "aprovada")
TRECHO = 300

TIPOS = [
    ("AUDIENCIA PUBLICA", "Audiência pública"),
    ("REUNIAO EXTRAORDINARIA", "Reunião extraordinária"),
    ("REUNIAO ORDINARIA", "Reunião ordinária"),
    ("REUNIAO SOLENE", "Reunião solene"),
    ("REUNIAO ESPECIAL", "Reunião especial"),
    ("CAMARA ITINERANTE", "Câmara itinerante"),
    ("REUNIAO PREPARATORIA", "Reunião preparatória"),
    ("COMISSAO", "Comissão"),
]
LIXO = [
    r"Câmara Municipal\s*\n\s*de Juiz de Fora",  # só o cabeçalho (duas linhas), não o nome no meio do texto
    r"Home Page: www\.camarajf\.mg\.gov\.br\s*e-mail: \S+",
    r"Rua Halfeld, 955 - Fone: [\d() -]+",
    r"36016-000 - Juiz de Fora - Minas Gerais - Brasil",
    r"Documento assinado digitalmente",
    r"A validade das assinaturas poder\w+ ser verificadas? no endereço \S+, código verificador: \S+",
    r"Powered by TCPDF \(www\.tcpdf\.org\)",
]


# ---------- cache (um arquivo por ano, para o repositório não crescer a cada dia) ----------
def ano_de(a):
    return (a.get("data") or "0000")[:4]


def carregar():
    atas = {}
    for f in sorted(CACHE.glob("*.jsonl.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as g:
            for linha in g:
                if linha.strip():
                    a = json.loads(linha)
                    atas[a["cod"]] = a
    return atas


def salvar(atas):
    CACHE.mkdir(parents=True, exist_ok=True)
    por_ano = {}
    for a in atas.values():
        por_ano.setdefault(ano_de(a), []).append(a)
    for ano, lista in por_ano.items():
        dados = "".join(json.dumps(a, ensure_ascii=False) + "\n" for a in sorted(lista, key=lambda x: x["cod"]))
        destino = CACHE / f"{ano}.jsonl.gz"
        novo = gzip.compress(dados.encode("utf-8"), mtime=0)  # mtime fixo: sem mudança, sem commit
        if not destino.exists() or destino.read_bytes() != novo:
            destino.write_bytes(novo)


# ---------- leitura de uma ata ----------
def ler_pdf(conteudo):
    from pypdf import PdfReader
    leitor = PdfReader(io.BytesIO(conteudo))
    return "\n".join((p.extract_text() or "") for p in leitor.pages)


def baixar(sessao, cod):
    """Texto da ata, ou None se o número não tem ata. Erro de rede levanta exceção."""
    r = sessao.get(URL.format(cod), headers=H, timeout=90)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    if not r.content.lstrip().startswith(b"%PDF"):
        return None
    t = ler_pdf(r.content)
    return t if t.strip() else None


def interpretar(cod, bruto):
    titulo = data = None
    m = re.search(r"([^\n]{3,120}?) do dia (\d{2})/(\d{2})/(\d{4})", bruto)
    if m:
        titulo = re.sub(r"\s+", " ", m.group(1)).strip()
        titulo = re.sub(r"^.*?de Juiz de Fora\s*", "", titulo, flags=re.I) or titulo
        data = f"{m.group(4)}-{m.group(3)}-{m.group(2)}"
    texto = bruto
    for p in LIXO:
        texto = re.sub(p, " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    i = texto.upper().find("ATA DA")
    corpo = texto[i:] if i >= 0 else texto
    if not data:  # sem o cabeçalho, tenta "realizada aos 12 dias do mês de fevereiro de 2026"
        meses = "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".split()
        m2 = re.search(r"aos (\d{1,2}) dias do mês de (\w+) de (\d{4})", corpo[:800], flags=re.I)
        if m2 and m2.group(2).lower() in meses:
            data = f"{m2.group(3)}-{meses.index(m2.group(2).lower()) + 1:02d}-{int(m2.group(1)):02d}"
    cabeca = sem_acento(titulo or corpo[:300]).upper()
    tipo = next((nome for chave, nome in TIPOS if chave in cabeca), "Outra")
    return {
        "cod": cod,
        "data": data,
        "tipo": tipo,
        "titulo": titulo or f"Ata nº {cod}",
        "aprovada": "ATA APROVADA" in bruto.upper(),
        "texto": corpo,
    }


# ---------- índice do site ----------
# Quem falou: "o Vereador Fulano comentou/pediu/cobrou...". Só citar o nome não basta,
# porque toda ata traz a lista de presença e as votações com quase todos os vereadores.
FALA = (r"(?:,? [^,.]{0,40},?)? (?:comentou|falou|disse|afirmou|mencionou|pediu|solicitou|parabenizou|agradeceu|"
        r"questionou|destacou|ressaltou|explicou|registrou|cobrou|lembrou|informou|defendeu|criticou|relatou|"
        r"apresentou|reclamou|denunciou|sugeriu|manifestou|declarou|enfatizou|esclareceu|argumentou|justificou|"
        r"fez|usou|ocupou|se manifestou|discursou)")


def nomes_vereadores():
    try:
        vs = json.loads(VEREADORES.read_text(encoding="utf-8"))
    except Exception:
        return []
    saida = []
    for v in vs:
        formas = {sem_acento(v.get("nome") or ""), sem_acento(v.get("apelido") or "")}
        formas = [f for f in formas if len(f) >= 6]
        if formas:
            saida.append((v["id"], re.compile(r"vereadora? (?:" + "|".join(re.escape(f) for f in formas) + r")" + FALA)))
    return saida


def gerar_site(atas):
    vereadores = nomes_vereadores()
    lista = []
    for a in sorted(atas.values(), key=lambda x: (x["data"] or "", x["cod"]), reverse=True):
        t = sem_acento(a["texto"])
        temas = [nome for nome, rx in TEMAS if re.search(rx, t)]
        vs = [vid for vid, rx in vereadores if rx.search(t)]
        lista.append({"c": a["cod"], "d": a["data"], "t": a["tipo"], "n": a["titulo"],
                      "ap": a["aprovada"], "x": a["texto"][:TRECHO], "tm": temas, "v": vs})
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps({
        "atualizado": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fonte": URL,
        "atas": lista,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Atas: {len(lista)} no índice do site")


# ---------- coleta ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inicio", type=int)
    ap.add_argument("--fim", type=int)
    ap.add_argument("--so-gerar", action="store_true")
    ap.add_argument("--minutos", type=float, default=float(os.environ.get("RADAR_TEMPO_MAX_ATAS_MIN", "330")))
    args = ap.parse_args()

    atas = carregar()
    print(f"Atas no cache: {len(atas)}")
    if args.so_gerar:
        gerar_site(atas)
        return

    if args.inicio:
        numeros, fim_aberto = range(args.inicio, (args.fim or args.inicio + 8000) + 1), args.fim is None
    else:
        ultima = max(atas) if atas else 0
        if not atas:
            print("Cache vazio. Para a primeira carga rode com --inicio 1 --fim 6000.")
        numeros, fim_aberto = range(max(1, ultima - REVISAR), ultima + 3000), True

    sessao = requests.Session()
    comeco = time.time()
    novas = sem_ata = erros = 0
    for cod in numeros:
        if (time.time() - comeco) / 60 > args.minutos:
            print("Tempo máximo desta rodada; o resto fica para a próxima.")
            break
        if cod in atas and atas[cod]["aprovada"]:
            continue  # já temos a versão final
        try:
            bruto = baixar(sessao, cod)
        except Exception as e:
            erros += 1
            print(cod, "erro:", e)
            if erros >= 15:
                print("Muitos erros seguidos; parando para não insistir com o servidor da Câmara.")
                break
            time.sleep(20)
            continue
        erros = 0
        if bruto is None:
            sem_ata += 1
            if fim_aberto and sem_ata >= SEM_ATA_PARA_PARAR and cod > max(atas, default=0):
                print(f"{SEM_ATA_PARA_PARAR} números seguidos sem ata: fim da lista.")
                break
        else:
            sem_ata = 0
            a = interpretar(cod, bruto)
            novas += cod not in atas
            atas[cod] = a
            print(cod, a["data"], a["titulo"])
            if novas and novas % 250 == 0:
                salvar(atas)  # guarda no meio do caminho
        time.sleep(PAUSA)

    salvar(atas)
    gerar_site(atas)
    print(f"Atas: {novas} novas nesta rodada, {len(atas)} no total")


if __name__ == "__main__":
    main()
