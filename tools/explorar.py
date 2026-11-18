import requests, json, collections, re, unicodedata
def sa(s): return "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn").lower()
API="https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo"
for ano,per in ((2026,5),(2026,4)):
    it=requests.get(API,params={"an_exercicio":ano,"nr_periodo":per,"co_tipo_demonstrativo":"RREO","no_anexo":"RREO-Anexo 02","id_ente":3136702},timeout=120).json().get("items",[])
    print(ano,per,len(it))
    if not it: continue
    print("COLUNAS", collections.Counter(x["coluna"] for x in it).most_common(20))
    for x in it:
        if sa(x["coluna"]).startswith("dotacao") and x.get("cod_conta","")[:0]=="" :
            print("  ",x.get("cod_conta"),"|",x["conta"],"|",x["coluna"],"|",x["valor"])
    break
it=requests.get(API,params={"an_exercicio":2026,"nr_periodo":4,"co_tipo_demonstrativo":"RREO","no_anexo":"RREO-Anexo 01","id_ente":3136702},timeout=120).json().get("items",[])
for x in it:
    if re.match(r"despesas (correntes|de capital)|total das despesas|despesas \(exceto", sa(x["conta"])) and "dotacao" in sa(x["coluna"]):
        print(" A1",x["conta"],"|",x["coluna"],"|",x["valor"])
# e_atos_vis acessível?
try:
    r=requests.get("https://www.pjf.mg.gov.br/e_atos/e_atos_vis.php?id=148005",timeout=60,headers={"User-Agent":"RadarJF/1.0"})
    print("ATO", r.status_code, len(r.content)); t=re.sub(r"<[^>]+>"," ",r.content.decode("utf-8","replace")); t=re.sub(r"\s+"," ",t); print(t[:3000])
except Exception as e: print("ATO erro", e)
