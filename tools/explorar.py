import requests, io, re, subprocess, sys, json
subprocess.run([sys.executable,"-m","pip","install","-q","pdfplumber"])
import pdfplumber
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
B="https://www.camarajf.mg.gov.br/"
L=requests.get(B+"transparencia/geraIntervalo.php",params={"ct":25},headers=UA,timeout=60).json()
for x in [L[1],L[4],L[13],L[20]]:
    r=requests.get(B+"relatorio.php",params={"cod_relatorio":x["cod"]},headers=UA,timeout=90)
    print("=====",x["value"])
    with pdfplumber.open(io.BytesIO(r.content)) as pdf:
        for i,pg in enumerate(pdf.pages[:3]):
            for tb in pg.extract_tables():
                for row in tb: print("ROW",i,json.dumps([re.sub(r"\s+"," ",c or "")[:160] for c in row],ensure_ascii=False))
