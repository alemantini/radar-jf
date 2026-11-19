import subprocess, json, shutil, os
subprocess.run(["bash","tools/versao_anterior.sh"],check=False)
os.makedirs("site/dados/prefeitura",exist_ok=True)
for f in os.listdir("/tmp/anterior/dados/prefeitura"):
    if f.startswith("empenhos_"): shutil.copy("/tmp/anterior/dados/prefeitura/"+f,"site/dados/prefeitura/")
subprocess.run(["python","scripts/prefeitura_numeros.py"],check=True)
d=json.load(open("site/dados/prefeitura/numeros.json"))
for c in d["casos"][:60]:
    print(f"{c['data']} {c['numero']} emp {c['empenhado']:,.0f} conta {c['conta']:,.0f} ({c['qtd']} x {c['preco']}) r={c['razao']} pago {c['pago']:,.0f} | {c['secretaria'][:25]} | {c['credor'][:35]}\n     {c['historico'][:420]}")
