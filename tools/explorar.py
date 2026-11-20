import requests, io, re
from pypdf import PdfReader
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
B="https://www.camarajf.mg.gov.br/"
L=requests.get(B+"transparencia/geraIntervalo.php",params={"ct":25},headers=UA,timeout=60).json()
print("N",len(L),[x["value"] for x in L[:26]])
for x in L[:24]:
    r=requests.get(B+"relatorio.php",params={"cod_relatorio":x["cod"]},headers=UA,timeout=90)
    if r.content[:4]!=b"%PDF": print("==",x["value"],"nao pdf"); continue
    t="\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(r.content)).pages)
    print("=====",x["value"],x["cod"],len(t))
    print(t[:2500])
