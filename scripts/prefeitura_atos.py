"""Diário Oficial da Prefeitura de Juiz de Fora ("Atos do Governo"), pesquisável.

Fonte: https://www.pjf.mg.gov.br/e_atos/e_atos.php (busca oficial por período).
A busca devolve até 1.000 atos por consulta; o robô consulta uma semana por vez (cerca de 250 atos)
e, se uma semana passar do limite, consulta dia a dia e, se preciso, tipo a tipo.
Guarda tudo em cache por mês (data/cache/atos/AAAA-MM.json) para não baixar de novo o que já tem;
a cada rodada só confere as últimas semanas (atos podem ser publicados com atraso).

Privacidade: atos sobre a situação pessoal de servidores e contribuintes (aposentadoria, pensão,
advertência, suspensão, demissão, processo disciplinar, decisões fiscais etc.) entram só na contagem,
sem o texto. O link para o ato oficial continua disponível.

Saída: site/dados/prefeitura/atos_resumo.json e site/dados/prefeitura/atos_AAAA.json
"""
import datetime as dt
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www.pjf.mg.gov.br/e_atos"
UA = "RadarJF/1.0 (robo de transparencia, coleta lenta; codigo aberto em https://github.com/alemantini/radar-jf)"
RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "data" / "cache" / "atos"
SAIDA = RAIZ / "site" / "dados" / "prefeitura"
INICIO = dt.date(2025, 1, 1)
LIMITE = 950            # perto do máximo de 1.000 da busca: divide a consulta
PAUSA = 1.5
TEMPO_MAX = int(os.environ.get("RADAR_TEMPO_MAX_ATOS", str(25 * 60)))
REVER_DIAS = 21         # semanas recentes são sempre conferidas de novo

SEM_TEXTO = re.compile(r"aposentadoria|pens[aã]o|advert[eê]ncia|suspens[aã]o|demiss[aã]o|\bPAD\b|reintegra|revers[aã]o|vac[aâ]ncia|arquivamento|^decis[aã]o$", re.I)
GRUPOS = [
    ("Nomeações e exonerações", r"nomea|exonera"),
    ("Situações pessoais (sem nomes)", SEM_TEXTO.pattern),
    ("Contratos, convênios e parcerias", r"^extrato"),
    ("Licitações, compras e dispensas", r"contrata[cç][aã]o direta|preg[aã]o|concorr|convite|credenciamento|chamamento|licita"),
    ("Leis, decretos e portarias", r"^lei|decreto|portaria|resolu|delibera|instru[cç][aã]o normativa|veto"),
]
SIGLAS = {
    "SE": "Secretaria de Educação", "SS": "Secretaria de Saúde", "SRH": "Secretaria de Recursos Humanos",
    "SEDUPP": "Secretaria de Desenvolvimento Urbano com Participação Popular", "SDA": "Secretaria de Desenvolvimento Agrário",
    "SEDIC": "Secretaria de Desenvolvimento Sustentável e Inclusivo, da Inovação e Competitividade",
    "SETUR": "Secretaria de Turismo", "SEL": "Secretaria de Esporte e Lazer", "CESAMA": "Cesama", "EMCASA": "Emcasa",
    "FUNALFA": "Funalfa", "PROCON": "Procon/JF", "DEMLURB": "Demlurb", "SETTRA": "Settra", "AMAC": "AMAC", "JFPREV": "JFPrev",
}
sessao = requests.Session()
sessao.headers["User-Agent"] = UA


def limpa(t):
    return re.sub(r"\s+", " ", (t or "").replace("\xa0", " ")).strip()


def grupo(tipo):
    for nome, rx in GRUPOS:
        if re.search(rx, tipo, re.I):
            return nome
    return "Avisos, editais e outros"


def orgao(texto):
    t = texto.strip()
    m = re.match(r"^([A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,10})(?:/[A-Z/]+)?\s*[–—-]\s", t)
    if m:
        return SIGLAS.get(m.group(1), m.group(1))
    m = re.search(r"\s[-–—]\s*([A-Z]{2,10})\s*[-–—]\s", t[:120])
    if m and (m.group(1) in SIGLAS or len(m.group(1)) <= 7):
        return SIGLAS.get(m.group(1), m.group(1))
    m = re.search(r"(?<![A-ZÀ-Ý])(SUB)?SECRETARIA (D[EOA]S? |DA |DE |DO )?([A-ZÀ-Ý]+(?: (?:E |D[EOA]S? )?[A-ZÀ-Ý]+){0,7}?)(?=,|\.|$| [-–—] | CONFORME| NO USO| E DA SECRETARIA| E SECRETARIA| CONVOCA| EDITAL| AVISO| PROCESSO| PORTARIA| Ref| REF| N[º°.]| [a-z])", t)
    if m:
        nome = (("Subsecretaria " if m.group(1) else "Secretaria ") + (m.group(2) or "") + m.group(3)).strip(" ,")
        return " ".join(p if p.lower() in ("de", "da", "do", "das", "dos", "e", "com") else p.capitalize() for p in nome.lower().split())
    for s in ("CESAMA", "EMCASA", "FUNALFA", "PROCON", "DEMLURB", "SETTRA", "JFPREV", "AMAC"):
        if s in t[:200]:
            return SIGLAS[s]
    return ""


def buscar(d1, d2, tipo=""):
    dados = {"filtro1": tipo, "filtro2": "", "dataArea0": d1.strftime("%d/%m/%Y"),
             "dataArea1": d2.strftime("%d/%m/%Y"), "sb_psq2": "Pesquisar"}
    for i in range(3):
        try:
            r = sessao.post(f"{BASE}/e_atos.php", data=dados, timeout=120)
            if r.status_code == 200:
                time.sleep(PAUSA)
                return ler(r.text)
            print(f"  HTTP {r.status_code} em {dados['dataArea0']}-{dados['dataArea1']}", file=sys.stderr)
        except requests.RequestException as e:
            print(f"  erro {e}", file=sys.stderr)
        time.sleep(10 * (i + 1))
    raise RuntimeError("busca falhou")


def ler(html):
    soup = BeautifulSoup(html, "html.parser")
    atos = []
    for cab in soup.select("div.ato_cab"):
        data = limpa(cab.select_one(".dataatoindex strong").get_text() if cab.select_one(".dataatoindex strong") else "")
        tipo = limpa(cab.select_one(".tp_ato").get_text() if cab.select_one(".tp_ato") else "")
        corpo = cab.find_next_sibling("div", class_="atotextindex")
        if not corpo:
            continue
        link = corpo.find("a", href=re.compile(r"e_atos_vis\.php\?id=\d+"))
        if not link:
            continue
        aid = int(re.search(r"id=(\d+)", link["href"]).group(1))
        texto = limpa(corpo.get_text(" ")).replace("[ Leia Mais ]", "").replace("[Leia Mais]", "").strip(" .")
        texto = re.sub(r"\s*\.\.\.\s*\[?\s*Leia Mais\s*\]?\s*$", "…", texto)
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})", data)
        atos.append({"id": aid, "data": f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else "", "tipo": tipo, "texto": texto})
    return atos


def tipos_disponiveis():
    soup = BeautifulSoup(sessao.get(f"{BASE}/e_atos.php", timeout=60).text, "html.parser")
    sel = soup.find("select", attrs={"name": "filtro1"})
    return [o["value"] for o in sel.find_all("option") if o.get("value")] if sel else []


def coletar_periodo(d1, d2, tipos):
    atos = buscar(d1, d2)
    if len(atos) < LIMITE:
        return atos
    if d1 < d2:  # divide em dias
        res, d = [], d1
        while d <= d2:
            res += coletar_periodo(d, d, tipos)
            d += dt.timedelta(days=1)
        return res
    res = []  # um dia só e ainda no limite: tipo a tipo
    for t in tipos:
        res += buscar(d1, d2, t)
    return res


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    feitos_arq = CACHE / "_semanas_feitas.json"
    feitos = set(json.loads(feitos_arq.read_text())) if feitos_arq.exists() else set()
    meses = defaultdict(dict)
    for f in CACHE.glob("20*.json"):
        meses[f.stem] = {int(k): v for k, v in json.loads(f.read_text()).items()}

    hoje = dt.date.today()
    tipos = tipos_disponiveis()
    if not tipos:
        print("Atos: página de busca não respondeu como esperado")
        sys.exit(1)
    inicio_t = time.time()
    semana = INICIO
    novas = 0
    while semana <= hoje:
        fim = min(semana + dt.timedelta(days=6), hoje)
        chave = semana.isoformat()
        recente = fim >= hoje - dt.timedelta(days=REVER_DIAS)
        if chave in feitos and not recente:
            semana += dt.timedelta(days=7)
            continue
        if time.time() - inicio_t > TEMPO_MAX:
            print("Atos: tempo da rodada esgotado; o resto fica para a próxima")
            break
        try:
            atos = coletar_periodo(semana, fim, tipos)
        except RuntimeError:
            print(f"Atos: falha na semana {chave}; tenta de novo na próxima rodada")
            break
        for a in atos:
            if a["data"]:
                meses[a["data"][:7]][a["id"]] = a
        novas += len(atos)
        if not recente:
            feitos.add(chave)
        print(f"  semana {chave}: {len(atos)} atos")
        semana += dt.timedelta(days=7)

    for m, d in meses.items():
        (CACHE / f"{m}.json").write_text(json.dumps({str(k): v for k, v in sorted(d.items())}, ensure_ascii=False))
    feitos_arq.write_text(json.dumps(sorted(feitos)))

    todos = sorted((a for d in meses.values() for a in d.values()), key=lambda a: (a["data"], a["id"]), reverse=True)
    if len(todos) < 1000:
        print(f"Atos: só {len(todos)} atos no cache; ainda não publica")
        sys.exit(1)

    tipos_l, orgaos_l = [], []
    idx_t, idx_o = {}, {}

    def ix(lista, mapa, v):
        if v not in mapa:
            mapa[v] = len(lista)
            lista.append(v)
        return mapa[v]

    por_ano = defaultdict(list)
    cont_g, cont_o, cont_mes = Counter(), Counter(), Counter()
    for a in todos:
        g = grupo(a["tipo"])
        oculto = bool(SEM_TEXTO.search(a["tipo"]))
        o = orgao(a["texto"])
        por_ano[a["data"][:4]].append([a["id"], a["data"], ix(tipos_l, idx_t, a["tipo"]), ix(orgaos_l, idx_o, o),
                                        "" if oculto else a["texto"]])
        cont_g[g] += 1
        if o:
            cont_o[o] += 1
        cont_mes[a["data"][:7]] += 1
    SAIDA.mkdir(parents=True, exist_ok=True)
    for ano, lista in por_ano.items():
        (SAIDA / f"atos_{ano}.json").write_text(json.dumps({"tipos": tipos_l, "orgaos": orgaos_l, "atos": lista},
                                                           ensure_ascii=False, separators=(",", ":")))
    resumo = {
        "fonte": "Diário Oficial Eletrônico do Município (Atos do Governo), Prefeitura de Juiz de Fora",
        "fonte_url": f"{BASE}/e_atos.php",
        "link_ato": f"{BASE}/e_atos_vis.php?id=",
        "coletado_em": dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M"),
        "desde": INICIO.isoformat(), "ate": todos[0]["data"], "total": len(todos),
        "anos": sorted(por_ano), "grupos": dict(cont_g.most_common()),
        "tipo_grupo": {t: grupo(t) for t in tipos_l},
        "tipos_sem_texto": [t for t in tipos_l if SEM_TEXTO.search(t)],
        "orgaos": cont_o.most_common(40), "meses": dict(sorted(cont_mes.items())),
    }
    (SAIDA / "atos_resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, separators=(",", ":")))
    print(f"OK atos: {len(todos)} no total ({novas} lidos nesta rodada), de {resumo['desde']} a {resumo['ate']}")


if __name__ == "__main__":
    main()
