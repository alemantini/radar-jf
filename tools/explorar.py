import json, re, collections, requests, datetime as dt
UA = {"User-Agent": "RadarJF/1.0 (robo de transparencia; https://github.com/alemantini/radar-jf)"}
d = requests.get("https://alemantini.github.io/radar-jf/dados/prefeitura/empenhos_2026.json", timeout=120).json()
print(d.keys(), len(d["empenhos"]), len(d["credores"]))
emp = d["empenhos"]
c = collections.Counter()
for e in emp:
    h = (e[6] or "").upper()
    for k in ["DISPENSA", "INEXIG", "EMERG", "PREGÃO", "PREGAO", "CONCORR", "ADESÃO", "ATA", "CONTRATO", "ADITIVO", "CREDENCIAMENTO", "CONVÊNIO", "TERMO DE COLABORA", "TERMO DE FOMENTO", "PROCESSO"]:
        if k in h: c[k] += 1
print(c)
import random; random.seed(1)
for e in random.sample([e for e in emp if e[2] >= 0], 25):
    print(" ", e[0], e[4], "|", e[6])
for url in ["https://brasilapi.com.br/api/cnpj/v1/18338178000102", "https://minhareceita.org/18338178000102",
            "https://portaldatransparencia.gov.br/download-de-dados/ceis", "https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/ceis/20261114_CEIS.zip"]:
    try:
        r = requests.get(url, headers=UA, timeout=60)
        print("==", url, r.status_code, r.headers.get("content-type"), r.text[:400].replace("\n", " ") if "json" in (r.headers.get("content-type") or "") else len(r.content))
    except Exception as x:
        print("==", url, "erro", x)
