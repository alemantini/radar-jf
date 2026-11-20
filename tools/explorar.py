import subprocess, json, re, collections
subprocess.run(["bash","tools/versao_anterior.sh"],check=False)
ALVO=["Cotresa","Esdeva","S3 Empreend","Asa Gestao","Piramide","Farias","Mitra","Big Ben","Universal","Pattaya","Ribeiro & Arrabal","Hgd","Bbx","Savi","Moinho","Cap Partic","J Oliveira"]
for ano in (2025,2026):
    B=json.load(open(f"/tmp/anterior/dados/prefeitura/empenhos_{ano}.json")); ix={c:i for i,c in enumerate(B["campos"])}
    E=B["empenhos"]; cr=lambda e:B["credores"][e[ix["credor"]]]
    for a in ALVO:
        rows=[e for e in E if a.lower() in cr(e)[1].lower()]
        if not rows: continue
        hs=collections.OrderedDict()
        for e in rows: hs.setdefault(str(e[ix["historico"]]),(e[ix["numero"]],B["elementos"][e[ix["elemento"]]],B["secretarias"][e[ix["secretaria"]]]))
        print(f"##### {ano} {a}: {len(rows)} linhas, emp {sum(e[ix['empenhado']] for e in rows):,.2f} pago {sum(e[ix['pago']] for e in rows):,.2f}")
        for h,(n,el,sec) in list(hs.items())[:5]: print(f"   {n} | {el[:35]} | {sec[:30]} | {h[:700]}")
