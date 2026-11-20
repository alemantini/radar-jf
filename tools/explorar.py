import subprocess, json, re, unicodedata, collections
subprocess.run(["bash","tools/versao_anterior.sh"],check=False)
def sa(s): return unicodedata.normalize("NFKD",s or "").encode("ascii","ignore").decode().lower()
for ano in (2025,2026):
    B=json.load(open(f"/tmp/anterior/dados/prefeitura/empenhos_{ano}.json")); ix={c:i for i,c in enumerate(B["campos"])}
    print("CAMPOS",B["campos"])
    E=B["empenhos"]; cr=lambda e:B["credores"][e[ix["credor"]]]; el=lambda e:B["elementos"][e[ix["elemento"]]]
    rows=[e for e in E if re.search(r"jfprev|juiz de fora previd|instituto de previd",sa(cr(e)[1])+" "+sa(str(e[ix["historico"]])))]
    tot=collections.defaultdict(lambda:[0,0,0])
    for e in rows:
        h=sa(str(e[ix["historico"]]))
        cat=("MULTA" if "multa" in h and "parcel" not in h else "JUROS" if "juro" in h and "parcel" not in h else "PARCEL" if "parcel" in h else "OUTRO")
        print(f"#{ano}|{cat}|"+"|".join(str(v)[:400] for v in e[:ix['historico']]+e[ix['historico']+1:])+f"|{cr(e)[1][:30]}|{el(e)[:35]}|H:{str(e[ix['historico']])[:260]}")
        if cat!="OUTRO":
            t=tot[cat]; t[0]+=e[ix["empenhado"]]; t[1]+=e[ix["pago"]]; t[2]+=1
    for k,v in tot.items(): print(f"TOTAL {ano} {k}: emp {v[0]:,.2f} pago {v[1]:,.2f} linhas {v[2]}")
