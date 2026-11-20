import subprocess, json, re, unicodedata, os, glob
subprocess.run(["bash","tools/versao_anterior.sh"],check=False)
def sa(s): return unicodedata.normalize("NFKD",str(s or "")).encode("ascii","ignore").decode().lower()
B=json.load(open("/tmp/anterior/dados/prefeitura/empenhos_2026.json")); ix={c:i for i,c in enumerate(B["campos"])}
for e in B["empenhos"]:
    h=sa(e[ix["historico"]]); c=B["credores"][e[ix["credor"]]]
    if (re.search(r"vigilan|alarme|monitoramento eletr|cftv|seguranca eletr|burnier|sao dimas",h) or re.search(r"vigilan|seguranca",sa(c[1]))) and e[ix["data"]]>="2026-08-01":
        print(f"@{e[ix['numero']]}|{e[ix['data']]}|{B['secretarias'][e[ix['secretaria']]][:30]}|{c[1][:40]} {c[0]}|emp {e[ix['empenhado']]}|pago {e[ix['pago']]}|{str(e[ix['historico']])[:300]}")
print("### arquivos", [os.path.relpath(f,"/tmp/anterior/dados") for f in glob.glob("/tmp/anterior/dados/**/*.json",recursive=True)][:80])
for f in glob.glob("/tmp/anterior/dados/**/*.json",recursive=True):
    if "empenhos_" in f: continue
    t=open(f,encoding="utf-8",errors="ignore").read(); st=sa(t)
    for m in re.finditer(r"vigilancia|burnier|hospital regional",st):
        w=st[max(0,m.start()-250):m.end()+350]
        if re.search(r"dispensa|contrat|hps|regional|burnier",w): print("%",os.path.basename(f),"|",w.replace("\n"," "))
