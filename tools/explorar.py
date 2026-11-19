import subprocess, json
subprocess.run(["bash","tools/versao_anterior.sh"],check=False)
for ano,nums in [(2026,["2026NE00052","2026NE00601","2026NE03112"]),(2025,["2025NE00634","2025NE00019"])]:
    B=json.load(open(f"/tmp/anterior/dados/prefeitura/empenhos_{ano}.json")); ix={c:i for i,c in enumerate(B["campos"])}
    for n in nums:
        rows=[e for e in B["empenhos"] if e[ix["numero"]]==n]
        print("=====",n,len(rows))
        for e in rows: print("  ",e[ix["data"]],B["secretarias"][e[ix["secretaria"]]][:25] if isinstance(e[ix["secretaria"]],int) else e[ix["secretaria"]],"|",(B["credores"][e[ix["credor"]]][1] if isinstance(e[ix["credor"]],int) else e[ix["credor"]])[:30],"| emp",e[ix["empenhado"]],"pago",e[ix["pago"]],"| el",e[ix["elemento"]],"|",str(e[ix["historico"]])[:300])
