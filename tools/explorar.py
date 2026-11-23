"""Exploração: combustível da Prefeitura nos empenhos já publicados no próprio site do Radar."""
import json, re, unicodedata, requests
from collections import defaultdict, Counter
SITE = "https://jflandia.com.br/dados/prefeitura/"
UA = {"User-Agent": "RadarJF/1.0 (robo de transparencia; https://github.com/alemantini/radar-jf)"}
def k(t): return "".join(c for c in unicodedata.normalize("NFD", str(t or "")) if unicodedata.category(c) != "Mn").lower()
COMB = re.compile(r"combustiv|gasolina|oleo diesel|\bdiesel\b|etanol|\balcool\b|\bgnv\b|abastecimento")
for ano in (2025, 2026):
    d = requests.get(f"{SITE}empenhos_{ano}.json", headers=UA, timeout=120).json()
    print("\n=====", ano, "chaves", list(d.keys()), "n", len(d["empenhos"]))
    print("exemplo", d["empenhos"][0])
    els = d["elementos"]; secs = d["secretarias"]; creds = d["credores"]
    print("elementos com combust:", [e for e in els if COMB.search(k(e))])
    tot = defaultdict(lambda: [0.0, 0.0, 0]); sec = defaultdict(float); cr = defaultdict(float); mes = [0.0]*12; amostra = []
    lit = 0; nlit = 0; ex_el = Counter()
    for row in d["empenhos"]:
        data, u, ic, ie, e, p, hist, num = row[:8]
        hk = k(hist); ek = k(els[ie]); ck = k(creds[ic][1]) if ic >= 0 else ""
        if not (COMB.search(hk) or COMB.search(ek)): continue
        if re.search(r"locacao|manutencao|seguro|pneu|lubrificante|oleo lubr|filtro|agua|gas liquefeito|glp|botij", hk) and not re.search(r"combustiv|gasolina|diesel|etanol", hk): continue
        ex_el[els[ie]] += 1
        t = tot["x"]; t[0] += e or 0; t[1] += p or 0; t[2] += 1
        sec[secs[u]] += p or 0
        if ic >= 0: cr[(creds[ic][0], creds[ic][1])] += p or 0
        if data and len(data) >= 7: mes[int(data[5:7]) - 1] += p or 0
        m = re.search(r"(\d{1,3}(?:\.\d{3})+|\d+)\s*(?:litros|lts?\b|l\b)", hk)
        if m: nlit += 1; lit += int(m.group(1).replace(".", ""))
        if len(amostra) < 25: amostra.append((data, secs[u], els[ie], creds[ic][1] if ic >= 0 else "PF", e, p, hist[:160]))
    print("TOTAL empenhado %.2f pago %.2f n %d" % tuple(tot["x"]))
    print("elementos:", ex_el.most_common(10))
    print("meses pago:", [round(x) for x in mes])
    print("secretarias:", sorted(sec.items(), key=lambda x: -x[1])[:15])
    print("credores:", sorted(cr.items(), key=lambda x: -x[1])[:15])
    print("histórico com litros:", nlit, "soma litros", lit)
    for a in amostra: print("  ", a)
