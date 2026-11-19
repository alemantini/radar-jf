import re, requests, io
from pypdf import PdfReader
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
R="https://www.camarajf.mg.gov.br/relatorio.php"
for cod in [21406,21636,22454,22521,23015,23328,23384,23839,23902]:
    x=requests.get(R,params={"cod_relatorio":cod},headers=UA,timeout=120)
    if x.content[:4]!=b"%PDF": print("== ",cod,"nao pdf",x.content[:200]); continue
    t="\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(x.content)).pages)
    print("=====",cod,len(t)); print(t[:300].replace("\n"," | "))
    for m in re.finditer(r"(?i)(seguro social|INSS|loca[cç][aã]o|marechal|aluguel)",t):
        a=max(0,m.start()-500); print("  ...",t[a:m.start()+700].replace("\n"," | ")); print("  ---")
