import subprocess, json
subprocess.run(["bash","tools/versao_anterior.sh"],check=False)
B=json.load(open("/tmp/anterior/dados/prefeitura/empenhos_2026.json")); ix={c:i for i,c in enumerate(B["campos"])}
for a in ["Cotresa","Piramide"]:
    rows=[e for e in B["empenhos"] if a.lower() in B["credores"][e[ix["credor"]]][1].lower()]
    print("#####",a)
    for e in rows: print(f"  {e[ix['data']]} {e[ix['numero']]} {B['elementos'][e[ix['elemento']]][:30]} emp={e[ix['empenhado']]} pago={e[ix['pago']]} | {str(e[ix['historico']])[:150]}")
