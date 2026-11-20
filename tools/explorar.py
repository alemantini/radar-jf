import subprocess, json, re, unicodedata, os, glob
subprocess.run(["bash","tools/versao_anterior.sh"],check=False)
def sa(s): return unicodedata.normalize("NFKD",str(s or "")).encode("ascii","ignore").decode().lower()
for ano in (2025,2026):
    B=json.load(open(f"/tmp/anterior/dados/prefeitura/empenhos_{ano}.json")); ix={c:i for i,c in enumerate(B["campos"])}
    for e in B["empenhos"]:
        h=sa(e[ix["historico"]]); c=B["credores"][e[ix["credor"]]]
        if re.search(r"vigil|seguranca patrimonial|monitoramento",h+" "+sa(c[1])) and re.search(r"hps|pronto socorro|regional|terreno|novo hosp|lote|area",h):
            print(f"@{ano}|{e[ix['numero']]}|{e[ix['data']]}|{B['secretarias'][e[ix['secretaria']]]}|{c[1]} {c[0]}|emp {e[ix['empenhado']]}|pago {e[ix['pago']]}|{e[ix['historico']]}")
print("### arquivos")
for f in glob.glob("/tmp/anterior/dados/prefeitura/**/*.json",recursive=True):
    if "empenhos_" in f: continue
    t=open(f,encoding="utf-8",errors="ignore").read()
    for m in re.finditer(r"(?i)vigil[^\"]{0,400}",t):
        s=sa(m.group(0))
        if re.search(r"hps|pronto|regional|terreno|hospital",s): print("%",os.path.basename(f),"|",t[max(0,m.start()-300):m.end()][:900].replace("\n"," "))
