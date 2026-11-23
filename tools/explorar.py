"""Exploração 3: históricos completos dos casos duvidosos do combustível."""
import json, re, requests
SITE = "https://jflandia.com.br/dados/prefeitura/"
UA = {"User-Agent": "RadarJF/1.0 (robo de transparencia; https://github.com/alemantini/radar-jf)"}
ALVO = re.compile(r"Anjos Locadora|Prime Consultoria|Mercado Bellini|Federacao Mineira de Handebol|Repelub")
for ano in (2025, 2026):
    d = requests.get(f"{SITE}empenhos_{ano}.json", headers=UA, timeout=120).json()
    for data, u, ic, ie, e, p, hist, num, *_ in d["empenhos"]:
        if ic >= 0 and ALVO.search(d["credores"][ic][1]):
            print(ano, data, num, d["secretarias"][u], "|", d["elementos"][ie], "|", d["credores"][ic][1], "| emp", e, "pago", p, "|", hist)
    # Parati 2025: empenhado x pago por empenho
    if ano == 2025:
        for data, u, ic, ie, e, p, hist, num, *_ in d["empenhos"]:
            if ic >= 0 and "Parati" in d["credores"][ic][1] and (p or 0) > (e or 0) + 1:
                print("PARATI pago>emp", data, num, d["elementos"][ie], e, p, hist[:90])
