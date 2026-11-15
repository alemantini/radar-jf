"""Exploração: ACAV (Associação Cultural Arte e Vida) nas emendas e nos empenhos."""
import csv, io, sys, re, collections, requests
sys.path.insert(0, "scripts")
from prefeitura_emendas import url_planilha
r = requests.get(url_planilha(), timeout=180)
linhas = list(csv.DictReader(io.StringIO(r.content.decode("utf-8", "replace"))))
pat = re.compile(r"arte e vida|acav|13\.?304\.?478", re.I)
print("== EMENDAS ==")
for x in linhas:
    if pat.search(" ".join(str(v) for v in x.values())):
        print(x.get("Ano"), x.get("Identificação da Emenda"), "|", x.get("Proponente"), "|", x.get("Origem dos recursos"), "|",
              x.get("Valor alocado/previsto"), "| pago", x.get("Valor Pago"), "|", x.get("Situação administrativa"), "|", (x.get("Objeto da Despesa") or "")[:120], "|", x.get("Unidade Gestora"))
print("== EMPENHOS ==")
for ano in (2025, 2026):
    d = requests.get(f"https://jflandia.com.br/dados/prefeitura/empenhos_{ano}.json", timeout=120).json()
    ic = [i for i, c in enumerate(d["credores"]) if "13304478000157" in str(c)]
    tot = collections.defaultdict(lambda: [0.0, 0.0])
    for e in d["empenhos"]:
        if e[2] in ic:
            k = (d["secretarias"][e[1]], d["elementos"][e[3]])
            tot[k][0] += e[4]; tot[k][1] += e[5]
    print(ano, "credor idx", ic, "empenhado", round(sum(v[0] for v in tot.values()), 2), "pago", round(sum(v[1] for v in tot.values()), 2))
    for k, v in sorted(tot.items(), key=lambda kv: -kv[1][1]):
        print("  ", k, [round(v[0], 2), round(v[1], 2)])
    # posição da ACAV entre recebedores da SEL
    sel = collections.defaultdict(float)
    for e in d["empenhos"]:
        if "Esporte" in d["secretarias"][e[1]] and e[2] >= 0:
            sel[d["credores"][e[2]][1] if isinstance(d["credores"][e[2]], list) else e[2]] += e[5]
    print("   top SEL:", [(k, round(v)) for k, v in sorted(sel.items(), key=lambda kv: -kv[1])[:6]])
