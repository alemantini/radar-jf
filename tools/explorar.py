import subprocess, json, re, unicodedata, requests, collections
subprocess.run(["bash","tools/versao_anterior.sh"],check=False)
def sa(s): return unicodedata.normalize("NFKD",s or "").encode("ascii","ignore").decode().lower()
print("############ A) JFPREV multas e juros")
for ano in (2025,2026):
    B=json.load(open(f"/tmp/anterior/dados/prefeitura/empenhos_{ano}.json")); ix={c:i for i,c in enumerate(B["campos"])}
    E=B["empenhos"]; cr=lambda e:B["credores"][e[ix["credor"]]]; el=lambda e:B["elementos"][e[ix["elemento"]]]; sec=lambda e:B["secretarias"][e[ix["secretaria"]]]
    te=tp=0
    for e in E:
        h=sa(str(e[ix["historico"]])); c=sa(cr(e)[1]); x=sa(el(e))
        if re.search(r"multa|juros|encargo|atualizacao monetaria|correcao monetaria|atraso",h+" "+x) and re.search(r"jfprev|previdencia|instituto de prev|ipjf|previd",h+" "+c):
            te+=e[ix["empenhado"]]; tp+=e[ix["pago"]]
            print(f"  {ano} {e[ix['data']]} {e[ix['numero']]} | {sec(e)[:30]} | {cr(e)[1][:35]} {cr(e)[0]} | {el(e)[:40]} | emp {e[ix['empenhado']]:,.2f} pago {e[ix['pago']]:,.2f} | {str(e[ix['historico']])[:330]}")
    print(f"  TOTAL {ano}: emp {te:,.2f} pago {tp:,.2f}")
print("############ B) Siconfi RREO Anexo 01 (despesas por categoria)")
S="https://apidatalake.tesouro.gov.br/ords/siconfi/tt/"
def get(rec,p):
    out=[]; off=0
    while True:
        r=requests.get(S+rec,params=dict(p,id_ente=3136702),timeout=120).json(); it=r.get("items",[]); out+=it
        if not r.get("hasMore"): break
        off+=len(it); p=dict(p,offset=off)
    return out
for ano,per in [(2024,6),(2025,6),(2026,5),(2026,4)]:
    it=get("rreo",{"an_exercicio":ano,"nr_periodo":per,"co_tipo_demonstrativo":"RREO","no_anexo":"RREO-Anexo 01"})
    print("== RREO",ano,"bim",per,"itens",len(it))
    for x in it:
        if re.search(r"investimento|inversoes",sa(x["conta"])) and x["coluna"] and not re.search(r"intra",sa(x["conta"])):
            print("   ",x["conta"][:45],"|",x["coluna"][:60],"|",x["valor"])
    if it: break_ok=True
print("############ C) Restos a pagar (RREO Anexo 07) 2025 bim 6 / 2026 bim 5")
for ano,per in [(2025,6),(2026,5),(2026,4)]:
    it=get("rreo",{"an_exercicio":ano,"nr_periodo":per,"co_tipo_demonstrativo":"RREO","no_anexo":"RREO-Anexo 07"})
    print("== RP",ano,per,len(it))
    for x in it:
        if re.search(r"^total|total \(iii\)|total geral|^despesas correntes$|investimentos",sa(x["conta"])):
            print("   ",x["conta"][:50],"|",x["coluna"][:70],"|",x["valor"])
