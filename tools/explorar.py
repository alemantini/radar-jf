import requests, io, re
from pypdf import PdfReader
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
B="https://www.camarajf.mg.gov.br/relatorio.php"
alvos=[(23395,"set/2025",["77","79"]),(23396,"out/2025",["91"]),(23403,"dez/2025",["104"]),(23359,"mai/2026",["31/2026"]),(23566,"jun/2026",["31/2026"])]
for cod,nome,nums in alvos:
    r=requests.get(B,params={"cod_relatorio":cod},headers=UA,timeout=90)
    t="\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(r.content)).pages)
    plano=re.sub(r"\s+"," ",t)
    print("=====",nome,"cod",cod,"| titulo:",plano[:90])
    for n in nums:
        for m in re.finditer(r"(?<![\d/])"+re.escape(n)+r"(?![\d])",plano):
            print("  >>",n,":",plano[max(0,m.start()-700):m.end()+250]); print()
