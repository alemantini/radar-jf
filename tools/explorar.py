"""Exploração 2: combustível da Prefeitura, filtro estrito, cobertura dos arquivos e campos."""
import json, re, unicodedata, requests
from collections import defaultdict, Counter
SITE = "https://jflandia.com.br/dados/prefeitura/"
UA = {"User-Agent": "RadarJF/1.0 (robo de transparencia; https://github.com/alemantini/radar-jf)"}
def k(t): return "".join(c for c in unicodedata.normalize("NFD", str(t or "")) if unicodedata.category(c) != "Mn").lower()
POS = re.compile(r"(aquisi|fornecimento|abastecimento|compra|referente|despesa|ref)[^.]{0,60}(combustiv|gasolina|diesel|etanol)|oleo diesel b|diesel b original|gasolina comum|etanol hidratado")
NEG = re.compile(r"sem (motorista e sem )?combustiv|bicombustiv|motor (a )?(diesel|gasolina)|a gasolina ou|locacao|aluguel")
CRED = re.compile(r"petroleo|combustiv|\bposto\b|auto posto")
r = requests.get(SITE + "resumo.json", headers=UA, timeout=60).json()
print("resumo chaves", list(r.keys())[:30]); print({k_: r[k_] for k_ in r if not isinstance(r[k_], (list, dict))})
for ano in (2024, 2025, 2026):
    try: d = requests.get(f"{SITE}empenhos_{ano}.json", headers=UA, timeout=120).json()
    except Exception as e: print(ano, "sem arquivo", e); continue
    datas = sorted(x[0] for x in d["empenhos"] if x[0])
    print("\n=====", ano, "campos", d.get("campos"), "n", len(d["empenhos"]), "datas", datas[0], datas[-1])
    print("empenhos por mês (qtd):", Counter(x[5:7] for x in datas))
    els, secs, creds = d["elementos"], d["secretarias"], d["credores"]
    tot = [0.0, 0.0, 0]; sec = defaultdict(lambda: [0.0, 0.0]); cr = defaultdict(lambda: [0.0, 0.0, 0]); tipo = defaultdict(float); fora = Counter()
    for row in d["empenhos"]:
        data, u, ic, ie, e, p, hist, num = row[:8]
        hk = k(hist); ek = k(els[ie]); ck = k(creds[ic][1]) if ic >= 0 else ""
        el_comb = "combustiveis automotivos" in ek
        ok = el_comb or (POS.search(hk) and not NEG.search(hk)) or (CRED.search(ck) and not NEG.search(hk) and "material de consumo" in ek or (CRED.search(ck) and "exercicios anteriores" in ek and not NEG.search(hk)))
        if not ok:
            if re.search(r"combustiv|gasolina|diesel|etanol", hk): fora[(creds[ic][1] if ic >= 0 else "PF", hk[:70])] += 1
            continue
        tot[0] += e or 0; tot[1] += p or 0; tot[2] += 1
        sec[secs[u]][0] += e or 0; sec[secs[u]][1] += p or 0
        if ic >= 0: c = cr[(creds[ic][0], creds[ic][1])]; c[0] += e or 0; c[1] += p or 0; c[2] += 1
        t = "diesel" if "diesel" in hk else "etanol" if re.search(r"etanol|alcool", hk) and "gasolina" not in hk else "gasolina" if "gasolina" in hk else "gasolina e etanol / não diz"
        tipo[t] += p or 0
    print("TOTAL empenhado %.2f pago %.2f n %d" % tuple(tot))
    print("por tipo (pago):", {a: round(b) for a, b in tipo.items()})
    print("secretarias:", [(s, round(v[0]), round(v[1])) for s, v in sorted(sec.items(), key=lambda x: -x[1][1])])
    print("credores:", [(c, round(v[0]), round(v[1]), v[2]) for c, v in sorted(cr.items(), key=lambda x: -x[1][1])[:15]])
    print("ficaram de fora (amostra):", fora.most_common(25))
