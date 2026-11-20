import subprocess, json, re, unicodedata, collections
subprocess.run(["bash","tools/versao_anterior.sh"],check=False)
def sa(s): return unicodedata.normalize("NFKD",s or "").encode("ascii","ignore").decode().lower()
EL=re.compile(r"locacao de imove|locacoes de imove")
HI=re.compile(r"(locacao|aluguel|alugueis) (de |do |dos |da )?(um |uma )?(imove|predio|sala|galpao|galpoes|casa|espaco fisico|loja|edificac|terreno)")
for ano in (2025,2026):
    B=json.load(open(f"/tmp/anterior/dados/prefeitura/empenhos_{ano}.json")); ix={c:i for i,c in enumerate(B["campos"])}
    E=B["empenhos"]; el=lambda e:B["elementos"][e[ix["elemento"]]]; cr=lambda e:B["credores"][e[ix["credor"]]]; sec=lambda e:B["secretarias"][e[ix["secretaria"]]]
    print("ELEMENTOS com loca:",sorted({el(e) for e in E if "loca" in sa(el(e))}))
    g=collections.defaultdict(lambda:{"emp":0,"pago":0,"n":set(),"h":collections.Counter(),"sec":collections.Counter()})
    for e in E:
        h=sa(str(e[ix["historico"]]))
        if EL.search(sa(el(e))) or HI.search(h):
            if "aluguel social" in h or "auxilio" in h: continue
            c=cr(e); k=(c[0],c[1])
            x=g[k]; x["emp"]+=e[ix["empenhado"]]; x["pago"]+=e[ix["pago"]]; x["n"].add(e[ix["numero"]]); x["h"][str(e[ix["historico"]])[:330]]+=1; x["sec"][sec(e)[:35]]+=1
    tot=sum(v["emp"] for v in g.values()); totp=sum(v["pago"] for v in g.values())
    print(f"\n######## {ano}: {len(g)} credores, emp {tot:,.0f} pago {totp:,.0f}")
    for (doc,nome),v in sorted(g.items(),key=lambda kv:-kv[1]["pago"]):
        pf=len(re.sub(r"\D","",doc))<=11
        print(f"== {'[PF]' if pf else nome[:45]} {'' if pf else doc} | emp {v['emp']:,.2f} pago {v['pago']:,.2f} | {len(v['n'])} emp | {v['sec'].most_common(2)}")
        for h,_ in v["h"].most_common(2): print("     ",h[:330])
    print("\n######## HPS",ano)
    for e in E:
        h=sa(str(e[ix["historico"]]))+" "+sa(cr(e)[1])
        if re.search(r"pronto socorro|\bhps\b",h) and re.search(r"loca|alug|imove|predio",h):
            c=cr(e); print(f"  {e[ix['data']]} {e[ix['numero']]} {sec(e)[:30]} | {c[1][:40]} {c[0]} | {el(e)[:35]} | emp {e[ix['empenhado']]:,.2f} pago {e[ix['pago']]:,.2f} | {str(e[ix['historico']])[:300]}")
