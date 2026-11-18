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


RODAPE = re.compile(r"\s*,? conforme MP nº 2\.200-2/2001, que institui a Infraestrutura de Chaves Públicas Brasileira - ICP-BRASIL \d+/\d+\s*")


CABECALHO = re.compile(r"\s*\d+ª [A-ZÀ-Ú ]{5,80} do dia \d{2}/\d{2}/\d{4}(?: ATA (?:NÃO )?APROVADA)?\s*")


def sem_rodape(texto):
    """Tira o aviso de assinatura digital e o título que o PDF repete em cada página."""
    return CABECALHO.sub(" ", RODAPE.sub(" ", texto))


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
    texto = sem_rodape(re.sub(r"\s+", " ", texto)).strip()
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
FALA = (r"(?:,? (?!que |o qual |a qual |autora? |relatora? )[^,.]{0,40},?)? (?:comentou|falou|disse|afirmou|mencionou|pediu|solicitou|parabenizou|agradeceu|"
        r"questionou|destacou|ressaltou|explicou|registrou|cobrou|lembrou|informou|defendeu|criticou|relatou|"
        r"apresentou|reclamou|denunciou|sugeriu|manifestou|declarou|enfatizou|esclareceu|argumentou|justificou|"
        r"fez (?!a abertura|a leitura|o encerramento)|usou|ocupou|se manifestou|discursou)")


def nomes_vereadores():
    try:
        vs = json.loads(VEREADORES.read_text(encoding="utf-8"))
    except Exception:
        return []
    saida = []
    for v in vs:
        formas = {sem_acento(v.get("nome") or ""), sem_acento(v.get("apelido") or "").replace("-", " ")}
        formas = sorted((f for f in formas if len(f) >= 4), key=len, reverse=True)
        if formas:
            nome = r"(?:" + "|".join(re.escape(f) for f in formas) + r")"
            saida.append((v["id"], re.compile(r"vereadora? " + nome + FALA), re.compile(r"\b" + nome + r"\b")))
    return saida


def gerar_site(atas):
    vereadores = nomes_vereadores()
    lista = []
    for a in sorted(atas.values(), key=lambda x: (x["data"] or "", x["cod"]), reverse=True):
        a["texto"] = sem_rodape(a["texto"])
        t = sem_acento(a["texto"])
        temas = [nome for nome, rx in TEMAS if re.search(rx, t)]
        vs = [vid for vid, rx, _ in vereadores if rx.search(t)]
        lista.append({"c": a["cod"], "d": a["data"], "t": a["tipo"], "n": a["titulo"],
                      "ap": a["aprovada"], "x": a["texto"][:TRECHO], "tm": temas, "v": vs})
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps({
        "atualizado": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fonte": URL,
        "atas": lista,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Atas: {len(lista)} no índice do site")
    gerar_falas(atas, vereadores)


# ---------- quem fala nas reuniões (mandato atual) ----------
INICIO_MANDATO = "2025-01-01"
TRECHOS_POR_VEREADOR = 20
# Pedidos de rotina não contam como fala: licença para sair, justificar falta etc.
ROTINA = re.compile(r"ausentar|ausencia|mais cedo|liberacao da reuniao|compromisso|se retirar|licenca|comparecer|nao pode estar presente")


def mapa_sem_acento(s):
    """Texto sem acento e minúsculo, com a posição de cada letra no texto original."""
    import unicodedata
    out, pos = [], []
    for i, ch in enumerate(s):
        for c in unicodedata.normalize("NFD", ch):
            if unicodedata.category(c) != "Mn":
                for l in c.lower():
                    out.append(l)
                    pos.append(i)
    return "".join(out), pos


def trecho_da_fala(texto, ini):
    t = texto[ini:ini + 420]
    corte = t.rfind(". ", 0, 330)
    return t[:corte + 1] if corte > 120 else t[:330].rsplit(" ", 1)[0] + "…"


# Assuntos das falas. Procurados sem acento e em minúsculas, só no trecho em que o próprio
# vereador fala (até a vez do próximo orador). Para contar, o assunto precisa aparecer
# pelo menos duas vezes no trecho: uma palavra solta não basta para dizer que ele defendeu o tema.
TEMAS_FALA = [
    ("Saúde", r"saude|hospita|\bubs\b|\bupa\b|medic[oa]s?\b|medicament|\bsus\b|vacina|paciente|consulta|cirurgi|enferm"),
    ("Educação", r"escola|ensino|educac|alun[oa]|estudante|creche|professor|merenda|\bcmei|pedagog"),
    ("Segurança pública", r"seguranca publica|policia|guarda municipal|violencia urbana|criminal|assalto|trafico|homicid"),
    ("Obras e bairros", r"asfalt|buraco|paviment|calcament|drenagem|enchente|alagament|encosta|iluminacao publica|capina|recapea|meio-fio|corrego|bueiro|obras? (?:no|na|do|da|de)\b"),
    ("Transporte e trânsito", r"onibus|transporte (?:publico|coletivo)|transito|tarifa|mobilidade|ciclovia|estacionament|semaforo"),
    ("Contas e fiscalização da Prefeitura", r"orcament|divida|deficit|contas publicas|licitac|contratos?\b|\bcpi\b|fiscaliz|tribunal de contas|\bldo\b|\bloa\b|credito suplementar|emprestimo|financiamento|prestacao de contas|controlador"),
    ("Servidores públicos", r"servidor|funcionalismo|reajuste|terceirizad|concurso publico|piso salarial"),
    ("Assistência social", r"\bcras\b|\bcreas\b|assistencia social|cesta basica|bolsa familia|vulnerab|situacao de rua|moradores? de rua|\bfome\b|cadunico|cadastro unico"),
    ("Causa animal", r"\banimai?s\b|\banimal\b|cachorr|\bcaes\b|\bgatos?\b|castrac|maus-tratos|causa animal"),
    ("Meio ambiente e limpeza urbana", r"meio ambiente|ambiental|arvore|reciclag|coleta de lixo|\blixo\b|demlurb|poluic|desmatament|paraibuna"),
    ("Pessoas idosas", r"\bidos[oa]s?\b|terceira idade"),
    ("Pessoas com deficiência", r"deficien|autis|\btea\b|acessibilidade|\bpcd\b"),
    ("Mulheres", r"\bmulher(?:es)?\b|feminic|violencia domestica|maria da penha"),
    ("Cultura, esporte e lazer", r"cultura|esporte|futebol|\bskate|festival|carnaval|\blazer\b|teatro|museu|atleta"),
    ("Moradia", r"moradia|habitac|minha casa|regularizacao fundiaria|loteamento"),
    ("Impostos e taxas", r"\biptu\b|imposto|tribut|taxa de"),
    ("Emprego e economia", r"emprego|desemprego|comercio|empresari|empreend|industria|geracao de renda"),
]
TEMAS_FALA_RX = [(n, re.compile(r)) for n, r in TEMAS_FALA]
HOMENAGEM = re.compile(r"homenag|parabeniz|titulo de cidadao|medalha|aniversario|boas-vindas|condolenc|votos de pesar|falecimento")
PROXIMO_ORADOR = re.compile(r"(?:o |a )?vereadora? [a-z]|o presidente |a presidente |em discussao|em votacao|ordem do dia")
TEMAS_POR_VEREADOR = 6
EXEMPLOS_POR_TEMA = 2


def falas_na_ata(norm, rx_fala):
    """Trechos (início, fim) em que o vereador fala, sem os pedidos de rotina."""
    for m in rx_fala.finditer(norm):
        if ROTINA.search(norm[m.end():m.end() + 140]):
            continue
        f = PROXIMO_ORADOR.search(norm, m.start() + 25, m.start() + 1500)
        yield m.start(), (f.start() if f else min(len(norm), m.start() + 1200))


def exemplo_do_tema(texto, pos, i, j, k):
    """Trecho da fala que mostra o assunto: o começo da fala, ou a frase onde o assunto aparece."""
    orig = texto[pos[i]:pos[j - 1] + 1]
    fim_1a_frase = orig.find(". ")
    if k < 220 and (fim_1a_frase < 0 or k <= fim_1a_frase):
        return trecho_da_fala(orig, 0)
    ini = pos[i + k] - pos[i]
    frase = orig.rfind(". ", 0, ini)
    return "… " + trecho_da_fala(orig, frase + 2 if frase >= 0 else ini)


def gerar_falas(atas, vereadores):
    reunioes = sorted((a for a in atas.values() if (a["data"] or "") >= INICIO_MANDATO and a["tipo"] != "Outra"),
                      key=lambda a: (a["data"], a["cod"]))
    citado, falou, trechos, homen = {}, {}, {}, {}
    temas, exemplos = {}, {}
    for a in reunioes:
        texto = sem_rodape(a["texto"])
        norm, pos = mapa_sem_acento(texto)
        for vid, rx_fala, rx_nome in vereadores:
            if rx_nome.search(norm):
                citado.setdefault(vid, []).append(a["data"])
            segs = list(falas_na_ata(norm, rx_fala))
            if not segs:
                continue
            falou.setdefault(vid, []).append(a["cod"])
            trechos.setdefault(vid, []).append({"c": a["cod"], "d": a["data"], "t": a["tipo"],
                                                "x": trecho_da_fala(texto, pos[segs[0][0]])})
            vistos = set()
            for i, j in segs:
                seg = norm[i:j]
                if HOMENAGEM.search(seg):
                    vistos.add("_h")
                for nome, rx in TEMAS_FALA_RX:
                    if len(rx.findall(seg)) >= 2 and nome not in vistos:
                        vistos.add(nome)
                        exemplos.setdefault((vid, nome), []).append(
                            {"c": a["cod"], "d": a["data"], "x": exemplo_do_tema(texto, pos, i, j, rx.search(seg).start())})
            for t in vistos:
                if t == "_h":
                    homen[vid] = homen.get(vid, 0) + 1
                else:
                    temas.setdefault(vid, {}).setdefault(t, 0)
                    temas[vid][t] += 1
    resumo, detalhe = {}, {}
    for vid, datas in citado.items():
        de, ate = min(datas), max(datas)  # período em que aparece nas atas = período no mandato
        no_periodo = [a for a in reunioes if de <= a["data"] <= ate]
        todos = sorted(temas.get(vid, {}).items(), key=lambda x: (-x[1], x[0]))
        top = todos[:TEMAS_POR_VEREADOR]
        resumo[vid] = {"de": de, "ate": ate, "reunioes": len(no_periodo), "falou": len(falou.get(vid, [])),
                       "homenagens": homen.get(vid, 0), "temas": [[t, n] for t, n in todos]}
        detalhe[vid] = {"trechos": list(reversed(trechos.get(vid, [])))[:TRECHOS_POR_VEREADOR],
                        "temas": {t: list(reversed(exemplos[(vid, t)]))[:EXEMPLOS_POR_TEMA] for t, _ in top}}
    base = {"atualizado": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "desde": INICIO_MANDATO,
            "total_reunioes": len(reunioes), "ultima": reunioes[-1]["data"] if reunioes else None, "fonte": URL}
    (SAIDA.parent / "atas_falas.json").write_text(json.dumps({**base, "vereadores": resumo},
                                                  ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (SAIDA.parent / "atas_falas_trechos.json").write_text(json.dumps({**base, "vereadores": detalhe},
                                                          ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Falas: {len(resumo)} vereadores, {len(reunioes)} reuniões desde {INICIO_MANDATO}")
    gerar_quente(atas, vereadores)


# ---------- assunto quente do mês ----------
# Pautas concretas que voltam às reuniões. Um assunto é "quente" no mês quando muitos
# vereadores diferentes falam dele: conta quantos falaram e em quantas reuniões.
PAUTAS = [
    ("Chuvas e famílias atingidas", r"(?<!faca )\bchuvas?\b|defesa civil|familias atingidas|pessoas atingidas|atingidos pel|desabrigad|desalojad|enchente|deslizament"),
    ("Plano de saúde do servidor (PAS-JF)", r"saude servidor|pas-jf|plano de (?:assistencia a )?saude (?:dos |do )?servidor"),
    ("CPI na Câmara", r"\bcpi\b|comissao parlamentar de inquerito"),
    ("Empréstimos da Prefeitura", r"operac(?:ao|oes) de credito|emprestimo|financiamento"),
    ("Contas e dívidas da Prefeitura", r"deficit|divida|contas publicas|responsabilidade fiscal|\blrf\b"),
    ("Emendas dos vereadores", r"emendas? (?:parlamentar|impositiva|individua)"),
    ("IPTU", r"\biptu\b"),
    ("Ônibus e tarifa", r"onibus|transporte coletivo|tarifa"),
    ("Hospitais e UPAs", r"hospita|\bhps\b|\bupa\b|santa casa"),
    ("Escolas e creches", r"escolas? municip|creche|merenda"),
    ("Segurança e Guarda Municipal", r"guarda municipal|seguranca publica"),
    ("Causa animal", r"\banimai?s\b|castrac|bem-estar animal"),
    ("Moradia", r"moradia|habitac|auxilio-moradia|aluguel social"),
]
PAUTAS_RX = [(n, re.compile(r)) for n, r in PAUTAS]
PAUTAS_POR_MES = 5
EXEMPLOS_POR_PAUTA = 4


def gerar_quente(atas, vereadores):
    reunioes = sorted((a for a in atas.values() if (a["data"] or "") >= INICIO_MANDATO and a["tipo"] != "Outra"),
                      key=lambda a: (a["data"], a["cod"]))
    meses = {}
    for a in reunioes:
        m = a["data"][:7]
        M = meses.setdefault(m, {"reunioes": 0, "p": {}})
        M["reunioes"] += 1
        texto = sem_rodape(a["texto"])
        norm, pos = mapa_sem_acento(texto)
        for vid, rx_fala, _ in vereadores:
            for i, j in falas_na_ata(norm, rx_fala):
                seg = norm[i:j]
                for nome, rx in PAUTAS_RX:
                    k = rx.search(seg)
                    if not k:
                        continue
                    P = M["p"].setdefault(nome, {"atas": set(), "v": {}, "ex": {}})
                    P["atas"].add(a["cod"])
                    P["v"][vid] = P["v"].get(vid, 0) + 1
                    # um exemplo por vereador: o mais recente
                    P["ex"][vid] = {"c": a["cod"], "d": a["data"], "v": vid,
                                    "x": exemplo_do_tema(texto, pos, i, j, k.start())}
    saida = []
    for m in sorted(meses, reverse=True):
        M = meses[m]
        ps = [(n, P) for n, P in M["p"].items() if len(P["v"]) >= 2]
        ps.sort(key=lambda x: (-len(x[1]["v"]), -len(x[1]["atas"]), x[0]))
        lista = []
        for n, P in ps[:PAUTAS_POR_MES]:
            quem = sorted(P["v"], key=lambda v: -P["v"][v])
            ex = sorted(P["ex"].values(), key=lambda e: (-P["v"][e["v"]], e["d"]))[:EXEMPLOS_POR_PAUTA]
            lista.append({"p": n, "reunioes": len(P["atas"]), "vereadores": quem, "ex": ex})
        todos = {n: len(P["v"]) for n, P in M["p"].items()}
        saida.append({"m": m, "reunioes": M["reunioes"], "pautas": lista, "todos": todos})
    (SAIDA.parent / "atas_quente.json").write_text(json.dumps({
        "atualizado": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "fonte": URL,
        "pautas": [n for n, _ in PAUTAS], "meses": saida,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Assunto do mês: {len(saida)} meses")


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
