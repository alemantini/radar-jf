import re, requests, json
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
B="https://www.camarajf.mg.gov.br/transparencia/"
D=requests.get(B+"exportardata.php",params={"tpr":"CONT","tpo":"JSON","dti":"01/01/2010","dtf":"31/12/2026"},headers=UA,timeout=120).json()
print("== INSS / Marechal")
for x in D:
    if x["docContratado"].startswith("29979036") or re.search(r"seguro social|INSS|marechal",x["contratado"]+x["objeto"],re.I):
        print("  ",x["tipo"],x["numContrato"],x["valor"],x["dataInicioVigencia"],"->",x["dataFinalVigencia"],x["dataPublicacao"],re.sub(r"\s+"," ",x["objeto"])[:200])
print("== tudo 2025-2026 (tipo|num|contratado|valor|vig|objeto)")
for x in D:
    if re.search(r"/202[56]$",x["data"] or ""):
        print("  ",x["tipo"],"|",x["numContrato"],"|",x["contratado"][:35],"|",x["valor"],"|",x["dataInicioVigencia"],"->",x["dataFinalVigencia"],"|",re.sub(r"\s+"," ",x["objeto"])[:110])
h=requests.get(B+"despesas.php",headers=UA,timeout=60); h.encoding="utf-8"
for s in re.findall(r"(?s)<script[^>]*>(.*?)</script>",h.text):
    if re.search(r"exportar|relat|gera|ajax",s,re.I): print("--DESP SCRIPT--",re.sub(r"\s+"," ",s)[:1800])
for m in re.findall(r'onclick=[^>]{0,200}',h.text): 
    if re.search(r"gera|desp|emit",m,re.I): print("ONCLICK",m[:200])
