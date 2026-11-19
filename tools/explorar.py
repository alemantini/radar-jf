import re, requests, json
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
B="https://www.camarajf.mg.gov.br/transparencia/"
D=None
for dti,dtf in [("01/01/2010","19/11/2026"),("2010-01-01","2026-11-19")]:
    r=requests.get(B+"exportardata.php",params={"tpr":"CONT","tpo":"JSON","dti":dti,"dtf":dtf},headers=UA,timeout=120)
    print("TRY",dti,r.status_code,len(r.content),r.text[:300])
    try:
        D=r.json()
        if D: break
    except Exception as e: print("nojson",e)
if D:
    print("N",len(D)); print("CHAVES",list(D[0].keys())); print(json.dumps(D[0],ensure_ascii=False)[:800])
    KW=re.compile(r"loca[cç][aã]o de im|alug|im[oó]vel|loca[cç][aã]o.*(sala|pr[eé]dio|galp|garag|espa[cç]o)|cess",re.I)
    for x in D:
        s=json.dumps(x,ensure_ascii=False)
        if KW.search(s): print("ALUG",s[:900])
