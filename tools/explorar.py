"""Amostra dos novos sinais publicados."""
import json, requests, collections
A = requests.get("https://jflandia.com.br/dados/prefeitura/alertas.json", timeout=60).json()
for t in ("comissionado", "atividade"):
    xs = [a for a in A["alertas"] if a["tipo"] == t]
    print("==", t, len(xs))
    for a in xs[:15]:
        print(round(a["valor"]), "|", a["nome"], "|", a["detalhe"][:330])
cats = collections.Counter(a["detalhe"].split("empenhos de ")[1].split(" (")[0] for a in A["alertas"] if a["tipo"] == "atividade")
print(cats)
