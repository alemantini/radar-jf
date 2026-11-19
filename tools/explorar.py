import requests, io
from pypdf import PdfReader
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
B="https://www.camarajf.mg.gov.br/"
L=requests.get(B+"transparencia/geraIntervalo.php?ct=15",headers=UA,timeout=60).json()
print([ (x["cod"],x["value"]) for x in L[:26]])
for x in [L[0]]+[y for y in L if "2025" in y["value"] and ("Janeiro" in y["value"] or "Mar" in y["value"])]:
    r=requests.get(B+"relatorio.php",params={"cod_relatorio":x["cod"]},headers=UA,timeout=90)
    t="\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(r.content)).pages)
    print("=====",x["value"]); print(repr(t[:1400])); print(t[1400:4000])
