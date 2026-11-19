import subprocess, json
subprocess.run(["bash","tools/versao_anterior.sh"],check=False)
B=json.load(open("/tmp/anterior/dados/prefeitura/empenhos_2026.json")); ix={c:i for i,c in enumerate(B["campos"])}
alvo={"2026NE02644":"Marja","2026NE00052":"4 Estacoes","2026NE01415":"Fgf","2026NE00168":"Milk","2026NE00038":"Amazonia"}
for n,cr in alvo.items():
    rows=[e for e in B["empenhos"] if e[ix["numero"]]==n and cr.lower() in B["credores"][e[ix["credor"]]][1].lower()]
    print("=====",n,cr,len(rows),"secretarias",{B["secretarias"][e[ix["secretaria"]]] for e in rows})
    for e in rows: print(f"   {e[ix['data']]} el={B['elementos'][e[ix['elemento']]][:40]} emp={e[ix['empenhado']]} pago={e[ix['pago']]} | {str(e[ix['historico']])[:500]}")
    # mesmo credor, outros empenhos no ano
    outros=[e for e in B["empenhos"] if cr.lower() in B["credores"][e[ix["credor"]]][1].lower() and e[ix["numero"]]!=n]
    print("   outros empenhos do credor no ano:",len({e[ix['numero']] for e in outros}),"total emp",round(sum(e[ix['empenhado']] for e in outros)))
