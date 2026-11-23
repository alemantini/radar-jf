"""Conferência: o empenho do Mercado Bellini no combustível de 2026."""
import requests
d = requests.get("https://jflandia.com.br/dados/prefeitura/empenhos_2026.json", headers={"User-Agent": "RadarJF/1.0"}, timeout=120).json()
alvo = set()
for data, u, ic, ie, e, p, hist, num, *_ in d["empenhos"]:
    if ic >= 0 and "Bellini" in d["credores"][ic][1] and "ombust" in d["elementos"][ie]: alvo.add((u, num, ic))
for data, u, ic, ie, e, p, hist, num, *_ in d["empenhos"]:
    if (u, num, ic) in alvo: print("CONF", data, num, d["secretarias"][u], "|", d["elementos"][ie], "|", e, p, "|", hist)
