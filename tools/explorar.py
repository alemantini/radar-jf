import subprocess, sys, json, shutil, os, collections
subprocess.run([sys.executable,"-m","pip","install","-q","pdfplumber"])
subprocess.run(["bash","tools/versao_anterior.sh"],check=False)
os.makedirs("site/dados",exist_ok=True); shutil.copy("/tmp/anterior/dados/resumo.json","site/dados/")
subprocess.run([sys.executable,"scripts/camara_diarias.py"],check=True)
D=json.load(open("site/dados/diarias.json")); R=json.load(open("site/dados/resumo.json")); N={v["id"]:v["apelido"] for v in R["vereadores"]}
V=D["viagens"]
tot=collections.Counter(); val=collections.Counter()
for v in V:
    if not v["cancelado"] and v["valor"]: tot[v["m"][:4]]+=1; val[v["m"][:4]]+=v["valor"]
print("TOT",dict(tot),{k:round(x,2) for k,x in val.items()})
print("SEM VALOR",[ (v["m"],v["n"],v["diarias"][:30]) for v in V if v["valor"] is None and not v["cancelado"]])
for k,p in sorted(D["por_vereador"].items(),key=lambda kv:-kv[1]["valor"]): print("VER",N.get(int(k)),p["viagens"],p["valor"],p["destinos"])
for v in V:
    if v["vereadores"]: print("V",v["m"],v["n"],v["valor"],v["cancelado"],v["destino"],"|",v["cargo"],"|",[c["id"] for c in v["vereadores"]],[c["nome"] for c in v["vereadores"]],"|",v["motivo"][:170])
cargos=collections.Counter(v["cargo"] for v in V); print("CARGOS",cargos.most_common(15))
dest=collections.Counter(v["destino"] for v in V if not v["cancelado"]); print("DEST",dest.most_common(15))
