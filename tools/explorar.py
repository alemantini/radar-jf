import subprocess, json, re, unicodedata
subprocess.run(["bash","tools/versao_anterior.sh"],check=False)
def sa(s): return unicodedata.normalize("NFKD",s or "").encode("ascii","ignore").decode().lower()
for ano in (2025,2026):
    B=json.load(open(f"/tmp/anterior/dados/prefeitura/empenhos_{ano}.json")); ix={c:i for i,c in enumerate(B["campos"])}
    for e in B["empenhos"]:
        c=sa(B["credores"][e[ix["credor"]]][1]); h=sa(str(e[ix["historico"]]))
        if "previd" in c and re.search(r"atraso|multa|juros|atualizacao|a menor|3180",h) and "parcelamento" not in h:
            print(f"@{ano}|{e[ix['numero']]}|{e[ix['data']]}|{B['secretarias'][e[ix['secretaria']]]}|emp {e[ix['empenhado']]}|pago {e[ix['pago']]}|{e[ix['historico']]}")
