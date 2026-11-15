import json, collections, requests
d = requests.get("https://alemantini.github.io/radar-jf/dados/prefeitura/alertas.json", timeout=60).json()
A = d["alertas"]
fr = [a for a in A if a["tipo"] == "fracionamento"]
print("fracionamento por elemento:", collections.Counter(a["detalhe"].split("(")[-1].split(")")[0] for a in fr).most_common(15))
for a in fr[:8]: print("  F", a["valor"], a["nome"][:40], "|", a["secretaria"], "|", a["detalhe"][:150])
pu = [a for a in A if a["tipo"] == "punida"]
print("punida:", collections.Counter(a["detalhe"].split(":")[1].split(" aplicada")[0].strip() for a in pu).most_common(10))
for a in pu[:12]: print("  P", a["valor"], a["nome"][:40], "|", a["detalhe"][:220])
for t in ["nova", "situacao", "capital", "concentracao", "emergencia"]:
    for a in [a for a in A if a["tipo"] == t][:4]: print(" ", t, a["valor"], a["nome"][:40], "|", a["detalhe"][:180])
