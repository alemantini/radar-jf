"""Exploração: roda o coletor do PNCP e mostra tempo e amostras."""
import json, subprocess, sys, time
t = time.time()
subprocess.run([sys.executable, "scripts/prefeitura_pncp.py"], check=False)
print("tempo", round(time.time() - t), "s")
d = json.load(open("site/dados/prefeitura/pncp_sinais.json"))
for s in d["sinais"][:12]:
    print(s["tipo"], "|", s["nome"], "|", s["valor"], "|", s["detalhe"][:300])
