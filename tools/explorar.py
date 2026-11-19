import subprocess, json, re, unicodedata
subprocess.run(["bash","tools/versao_anterior.sh"],check=False)
def sa(s): return unicodedata.normalize("NFKD",s or "").encode("ascii","ignore").decode().upper()
for ano in (2025,2026):
    B=json.load(open(f"/tmp/anterior/dados/prefeitura/empenhos_{ano}.json")); ix={c:i for i,c in enumerate(B["campos"])}
    E=B["empenhos"]; cr=lambda e: B["credores"][e[ix["credor"]]]; sec=lambda e: B["secretarias"][e[ix["secretaria"]]]
    def dump(titulo, filtro):
        nums={(e[ix["numero"]],e[ix["secretaria"]],e[ix["credor"]]) for e in E if filtro(e)}
        print(f"\n##### {ano} {titulo}: {len(nums)} empenhos")
        te=tp=0
        for k in sorted(nums):
            rows=[e for e in E if (e[ix["numero"]],e[ix["secretaria"]],e[ix["credor"]])==k]
            emp=sum(e[ix["empenhado"]] for e in rows); pg=sum(e[ix["pago"]] for e in rows); te+=emp; tp+=pg
            print(f"  == {k[0]} | {sec(rows[0])[:30]} | {cr(rows[0])[1][:40]} {cr(rows[0])[0]} | emp {emp:,.2f} pago {pg:,.2f} | linhas {len(rows)}")
            for e in rows: print(f"       {e[ix['data']]} {B['elementos'][e[ix['elemento']]][:30]} emp={e[ix['empenhado']]} pago={e[ix['pago']]} | {str(e[ix['historico']])[:260]}")
        print(f"  TOTAL emp {te:,.2f} pago {tp:,.2f}")
    dump("BONES", lambda e: re.search(r"\bBONE", sa(str(e[ix["historico"]]))) and "TRANSPORTE" in sa(sec(e)))
    dump("KIT LANCHE DEMLURB", lambda e: re.search(r"KITS? ?LANCHE", sa(str(e[ix["historico"]]))) and "LIMPEZA" in sa(sec(e)))
    dump("ZE GOTINHA", lambda e: "GOTINHA" in sa(str(e[ix["historico"]])))
    dump("DRONES ANDRONES", lambda e: "ANDRONES" in sa(cr(e)[1]))
