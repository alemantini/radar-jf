import re, requests, io, json
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
B="https://www.camarajf.mg.gov.br/"
L=requests.get(B+"transparencia/geraIntervalo.php?ct=15",headers=UA,timeout=60).json()
print("N meses",len(L)); print([x["value"] for x in L])
from pypdf import PdfReader
for c in [L[0]["cod"]]:
    for tp in ["pdf","xls","txt"]:
        x=requests.get(f"{B}relatorio.php?cod_relatorio={c}&tp={tp}",headers=UA,timeout=90)
        ct=x.headers.get("content-type"); print("--",tp,x.status_code,ct,len(x.content),x.headers.get("content-disposition"))
        if x.content[:4]==b"%PDF":
            p=PdfReader(io.BytesIO(x.content)); print("pags",len(p.pages))
            for pg in p.pages[:3]: print((pg.extract_text() or "")[:3000])
        else: print(x.content[:2000])
c=requests.get(B+"transparencia/geraIntervalo.php?ct=25",headers=UA,timeout=60).json()[0]["cod"]
x=requests.get(f"{B}relatorio.php?cod_relatorio={c}",headers=UA,timeout=90)
print("== DIARIAS",x.status_code,len(x.content))
if x.content[:4]==b"%PDF":
    p=PdfReader(io.BytesIO(x.content)); print("pags",len(p.pages)); print((p.pages[0].extract_text() or "")[:2500])
