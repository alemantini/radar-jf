import json, re, unicodedata, subprocess, collections
subprocess.run(["bash","tools/versao_anterior.sh"],check=False)
import collections as _c
def sa(s): return unicodedata.normalize("NFKD",s or "").encode("ascii","ignore").decode().lower()
TEMAS={
 "festas e shows":r"\bshows?\b|cantor|banda musical|apresentacao artistica|palco|sonorizacao|trio eletrico|carnaval|reveillon|\bnatal\b(?! ?(jardim|bairro))|papai noel|decoracao natalina|iluminacao natalina|fogos",
 "buffet e comida":r"buffet|coquetel|coffee|lanche|salgad|bolo|doces|churrasc|refeic|marmit|almoco|jantar|restaurante|cafe da manha|kit lanche",
 "flores e homenagens":r"coroa de flores|arranjos? (de )?flor|\bflores\b(?! ?(\d|- b|276))(?!ta)|trofeu|medalha|placa de homenagem|festividades e homenagens|condecor",
 "brindes":r"brinde|camiseta|\bbones?\b|squeeze|chaveiro|caneca|uniforme de gala|sacola personalizada|kit (escolar|personalizado)",
 "viagens":r"passagens? aerea|hospedagem|hotel|diarias? de viagem|translado|agencia de viagem|pacote turistico",
 "publicidade":r"publicidade|propaganda|campanha publicitaria|influenciador|impulsionamento|outdoor",
 "eventos":r"\bevento|cerimonial|locacao de tenda|tendas|estrutura para evento|banheiro quimico|gerador de energia para evento",
 "bebidas":r"cerveja|vinho|refrigerante|agua mineral|bebida",
 "multas e juros":r"multa|juros|encargos por atraso|correcao monetaria|atraso no pagamento",
 "indenizacoes e acordos":r"indeniza|acordo judicial|sentenca|precatorio|rpv|dano moral",
 "animais":r"\bracao\b|\bracoes\b|veterinari|canil|castracao",
 "curiosos":r"grama sintetica|perfume|cosmetic|chocolate|ovos de pascoa|panetone|cesta de natal|picole|sorvete|pipoca|algodao doce|brinquedo|pula pula|cama elastica|fantasia|maquiagem|piscina|jet ski|drone|estatua|escultura",
}
for ano in (2025,2026):
    try: B=json.load(open(f"/tmp/anterior/dados/prefeitura/empenhos_{ano}.json"))
    except Exception as e: print("sem",ano,e); continue
    C=B["campos"]; ix={c:i for i,c in enumerate(C)}
    print("=== ANO",ano,"n",len(B["empenhos"]),"campos",C,"cred ex",B["credores"][:3],"sec ex",B["secretarias"][:3])
    print("numeros exemplo",[e[ix["numero"]] for e in B["empenhos"][:8]], "vazios",sum(1 for e in B["empenhos"] if not e[ix["numero"]]))
    cnt=_c.Counter((e[ix["numero"]],e[ix["secretaria"]]) for e in B["empenhos"]); print("repetidos",sum(1 for v in cnt.values() if v>1), cnt.most_common(3))
    agg={}
    for e in B["empenhos"]:
        k=(e[ix["numero"]],e[ix["secretaria"]],e[ix["credor"]],str(e[ix["historico"]])[:60])
        a=agg.get(k)
        if a is None: agg[k]=list(e)
        else:
            a[ix["empenhado"]]+=e[ix["empenhado"]]; a[ix["pago"]]+=e[ix["pago"]]
    def nm(lst,i):
        try: return lst[i] if isinstance(i,int) else i
        except: return i
    for t,rx in TEMAS.items():
        R=re.compile(rx)
        hits=[a for a in agg.values() if R.search(sa(str(a[ix["historico"]])))]
        tot=sum(a[ix["empenhado"]] for a in hits)
        print(f"\n## {t} ({ano}): {len(hits)} empenhos, R$ {tot:,.0f}")
        for a in sorted(hits,key=lambda a:-a[ix["empenhado"]])[:9]:
            cr=nm(B["credores"],a[ix["credor"]]); cr=(cr[1] if len(str(cr[0]))>11 else "pessoa fisica") if isinstance(cr,list) else cr
            print(f"  {a[ix['data']]} R$ {a[ix['empenhado']]:,.0f} pago {a[ix['pago']]:,.0f} | {str(nm(B['secretarias'],a[ix['secretaria']]))[:28]} | {str(cr)[:40]} | {str(a[ix['historico']])[:230]}")
