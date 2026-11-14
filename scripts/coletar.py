"""Coleta dados oficiais da Câmara Municipal de Juiz de Fora (sistema iS@l).

Saída:
  data/bruto/proposicoes.json  lista de proposições (tipo, número, ano, autor, ementa, situação, id)
  data/bruto/vereadores.json   vereadores da legislatura atual (nome, apelido, partido, contato de gabinete)
  data/cache/datas.json        data de apresentação de cada proposição (cache incremental)

Se algo vier incompleto ou estranho, o script termina com erro e o site NÃO é republicado.
"""
import datetime as dt
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www.camarajf.mg.gov.br"
UA = ("RadarJF/1.0 (robo de transparencia, coleta lenta 1x por dia; "
      "codigo aberto em https://github.com/alemantini/radar-jf)")
RAIZ = Path(__file__).resolve().parent.parent
BRUTO = RAIZ / "data" / "bruto"
CACHE = RAIZ / "data" / "cache"

# Legislatura 2025-2028
ANO_INICIAL = 2025
TIPOS = {
    "REQ": "Requerimento",
    "IND": "Indicação",
    "PEDIF": "Pedido de Informação",
    "REP": "Representação",
    "MOC": "Moção",
    "PLEI": "Projeto de Lei",
    "PLEIC": "Projeto de Lei Complementar",
    "PELOR": "Projeto de Emenda à Lei Orgânica",
    "PRES": "Projeto de Resolução",
    "PDL": "Projeto de Decreto Legislativo",
}
PAUSA = float(os.environ.get("RADAR_PAUSA", "0.6"))
MAX_DATAS_POR_RODADA = int(os.environ.get("RADAR_MAX_DATAS", "6000"))
TEMPO_MAX_DATAS = int(os.environ.get("RADAR_TEMPO_MAX_DATAS", str(60 * 60)))  # segundos
CONSULTAS_SIMULTANEAS = 3

_local = threading.local()


def _sessao():
    if not hasattr(_local, "s"):
        _local.s = requests.Session()
        _local.s.headers["User-Agent"] = UA
    return _local.s


def baixar(url, params=None, tentativas=4):
    for i in range(tentativas):
        try:
            r = _sessao().get(url, params=params, timeout=120)
            if r.status_code == 200:
                time.sleep(PAUSA)
                try:
                    return r.content.decode("utf-8")
                except UnicodeDecodeError:
                    return r.content.decode("latin-1")
            print(f"  HTTP {r.status_code} em {url}", file=sys.stderr)
        except requests.RequestException as e:
            print(f"  erro {e} em {url}", file=sys.stderr)
        time.sleep(5 * (i + 1))
    raise RuntimeError(f"Falha ao baixar {url} {params}")


def limpa(t):
    return re.sub(r"\s+", " ", (t or "").replace("\xa0", " ")).strip()


def coletar_proposicoes():
    ano_atual = dt.date.today().year
    todas = []
    contagem = {}
    for ano in range(ANO_INICIAL, ano_atual + 1):
        for cod, nome in TIPOS.items():
            params = {
                "orig": "", "numero": "", "ano": str(ano), "numeroprocesso": "",
                "anoprocesso": "", "autor": "", "parlcodigo": "", "ementa": "",
                "palavra": "", "codtipo": cod, "btnprocurar": "Procurar", "out": "csv",
            }
            html = baixar(f"{BASE}/sal/listapropos.php", params)
            soup = BeautifulSoup(html, "html.parser")
            n = 0
            for tr in soup.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) < 11:
                    continue
                link = tr.find("a", href=re.compile(r"proposicaon\.php\?num=\d+"))
                if not link:
                    continue
                pid = int(re.search(r"num=(\d+)", link["href"]).group(1))
                todas.append({
                    "id": pid,
                    "tipo": cod,
                    "tipo_nome": nome,
                    "numero": limpa(tds[0].get_text()).lstrip("0") or "0",
                    "ano": int(limpa(tds[2].get_text()) or ano),
                    "autor": limpa(tds[6].get_text()),
                    "ementa": limpa(tds[8].get_text()),
                    "situacao": limpa(tds[10].get_text()),
                })
                n += 1
            contagem[f"{ano}-{cod}"] = n
            print(f"{ano} {cod}: {n}")
    return todas, contagem


def coletar_vereadores():
    html = baixar(f"{BASE}/www/vereadores")
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        m = re.search(r"/vereadores/exibir/(\d+)/[^\"']+", a["href"])
        if m and m.group(0) not in [x[1] for x in links]:
            links.append((int(m.group(1)), m.group(0)))
    vereadores = []
    for vid, caminho in links:
        url = BASE + "/www" + caminho if not caminho.startswith("/www") else BASE + caminho
        h = BeautifulSoup(baixar(url), "html.parser")
        h2 = h.find("h2", class_="t-principal")
        if not h2:
            continue
        partes = [limpa(x) for x in h2.get_text("\n").split("\n") if limpa(x)]
        nome = partes[0]
        resto = " ".join(partes[1:])
        parenteses = re.findall(r"\(([^)]*)\)", resto)
        apelido = parenteses[0] if len(parenteses) >= 2 else nome
        observacao = ""
        if " - " in apelido:  # ex.: "Yuri Fófano - vereador substituto de ... a ..."
            apelido, observacao = [x.strip() for x in apelido.split(" - ", 1)]
        partido = parenteses[-1] if parenteses else ""
        if " - " in partido:  # "Partido Liberal - PL" -> "PL"
            partido = min(partido.split(" - "), key=len).strip()
        dados = h.find("p", class_="dadosDiretor")
        texto = limpa(dados.get_text(" ")) if dados else ""
        email = re.search(r"[\w.\-]+@camarajf\.mg\.gov\.br", texto)
        tel = re.search(r"Telefones?:\s*([\d() \-/,]+)", texto)
        texto_ficha = limpa(h.get_text(" "))
        votos = re.search(r"2024\s*-\s*([\d.]+)\s*votos", texto_ficha)
        vereadores.append({
            "votos_2024": int(votos.group(1).replace(".", "")) if votos else None,
            "id": vid,
            "nome": nome,
            "apelido": apelido,
            "partido": partido,
            "observacao": observacao,
            "email_gabinete": email.group(0) if email else "",
            "telefone_gabinete": limpa(tel.group(1)).strip(" ,-") if tel else "",
            "ficha": url,
        })
        print(f"vereador: {apelido} ({partido})")
    return vereadores


def coletar_datas(proposicoes):
    arq = CACHE / "datas.json"
    datas = json.loads(arq.read_text()) if arq.exists() else {}
    faltando = [p["id"] for p in proposicoes if str(p["id"]) not in datas]
    # mais recentes primeiro
    faltando.sort(reverse=True)
    inicio = time.time()
    feitas = 0

    def uma(pid):
        if time.time() - inicio > TEMPO_MAX_DATAS:
            return pid, None
        try:
            html = baixar(f"{BASE}/sal/proposicaon.php", {"num": pid}, tentativas=2)
        except RuntimeError:
            return pid, None
        m = re.search(r"Per(?:&iacute;|í)odo:\s*(\d{2})/(\d{2})/(\d{4})", html)
        return pid, (f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else "")

    # poucas consultas ao mesmo tempo, cada uma com pausa, para não pesar no servidor
    with ThreadPoolExecutor(max_workers=CONSULTAS_SIMULTANEAS) as ex:
        for pid, data in ex.map(uma, faltando[:MAX_DATAS_POR_RODADA]):
            if data is None:
                continue
            datas[str(pid)] = data
            feitas += 1
            if feitas % 500 == 0:
                arq.write_text(json.dumps(datas, ensure_ascii=False, sort_keys=True))
                print(f"  datas coletadas nesta rodada: {feitas}")
    arq.write_text(json.dumps(datas, ensure_ascii=False, sort_keys=True))
    print(f"datas: {feitas} novas, {len(faltando) - feitas} ainda faltando")


def validar(proposicoes, contagem, vereadores):
    """Barra a publicação se a coleta parecer incompleta."""
    problemas = []
    ano_atual = dt.date.today().year
    if len(vereadores) < 20:
        problemas.append(f"só {len(vereadores)} vereadores encontrados (esperado ~24)")
    if contagem.get(f"{ano_atual}-REQ", 0) == 0 and dt.date.today().month > 2:
        problemas.append("nenhum requerimento no ano atual")
    anterior_arq = BRUTO / "contagem.json"
    if anterior_arq.exists():
        anterior = json.loads(anterior_arq.read_text())
        for chave, n_ant in anterior.items():
            n = contagem.get(chave, 0)
            if n_ant >= 20 and n < 0.9 * n_ant:
                problemas.append(f"{chave}: caiu de {n_ant} para {n}")
    ids = [p["id"] for p in proposicoes]
    if len(ids) != len(set(ids)):
        problemas.append("ids repetidos na coleta")
    return problemas


def main():
    BRUTO.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    vereadores = coletar_vereadores()
    proposicoes, contagem = coletar_proposicoes()
    problemas = validar(proposicoes, contagem, vereadores)
    if problemas:
        print("COLETA REJEITADA, o site continua com a última versão boa:")
        for p in problemas:
            print(" -", p)
        sys.exit(1)
    if os.environ.get("RADAR_SEM_DATAS") != "1":
        coletar_datas(proposicoes)
    (BRUTO / "proposicoes.json").write_text(json.dumps(proposicoes, ensure_ascii=False))
    (BRUTO / "vereadores.json").write_text(json.dumps(vereadores, ensure_ascii=False, indent=1))
    (BRUTO / "contagem.json").write_text(json.dumps(contagem, indent=1, sort_keys=True))
    (BRUTO / "coletado_em.txt").write_text(dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M"))
    print(f"OK: {len(proposicoes)} proposições, {len(vereadores)} vereadores")


if __name__ == "__main__":
    main()
