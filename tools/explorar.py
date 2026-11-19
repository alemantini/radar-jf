import re, requests, json
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
B="https://www.camarajf.mg.gov.br/transparencia/"
D=requests.get(B+"exportardata.php",params={"tpr":"CONT","tpo":"JSON","dti":"01/01/2010","dtf":"31/12/2026"},headers=UA,timeout=120).json()
KW=re.compile(r"loca[cç][aã]o d[oe] im[oó]vel|im[oó]vel (situado|sito)|marechal deodoro|andar|vagas? (para|de) estacionamento|torre de transmiss|loca[cç][aã]o de (espa[cç]o|sala|galp|garag|dep[oó]sito|pr[eé]dio)|aluguel de (im|sala|espa)|cess[aã]o de uso|n[aã]o.residencial",re.I)
base={}
for x in D:
    if KW.search(x["objeto"] or ""):
        print("|".join([x["tipo"],x["numContrato"],x["contratado"],x["docContratado"],x["valor"],x["data"],x["dataInicioVigencia"],x["dataFinalVigencia"],str(x["anexo"]),re.sub(r"\s+"," ",x["objeto"])[:400]]))
# cessão
r=requests.get(B,headers=UA,timeout=60); r.encoding="utf-8"
for u in set(re.findall(r'href="([^"]*termocess[^"]*)"',r.text)): print("CESSAO",u)
for pg in ["vereadores.php","index.php","outros.php","patrimonio.php"]:
    try:
        x=requests.get(B+pg,headers=UA,timeout=60); x.encoding="utf-8"
        for u,t in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',x.text,re.S):
            if re.search(r"cess|termo|loca|imov",u+t,re.I): print("LNK",pg,re.sub(r"<[^>]+>|\s+"," ",t).strip()[:60],"|",u)
    except Exception as e: print("err",pg,e)
