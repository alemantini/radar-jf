import requests, io, re, subprocess, sys, json
subprocess.run([sys.executable,"-m","pip","install","-q","pdfplumber"])
import pdfplumber
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
B="https://www.camarajf.mg.gov.br/"
for cod,nome in [(23395,"set25"),(23403,"dez25"),(22995,"mar26")]:
    r=requests.get(B+"relatorio.php",params={"cod_relatorio":cod},headers=UA,timeout=90)
    print("=====",nome)
    with pdfplumber.open(io.BytesIO(r.content)) as pdf:
        pg=pdf.pages[0]
        print("lines",len(pg.lines),"rects",len(pg.rects),"pages",len(pdf.pages))
        for st in [{}, {"vertical_strategy":"text","horizontal_strategy":"lines"}, {"vertical_strategy":"lines","horizontal_strategy":"text"}]:
            tbs=pg.extract_tables(st)
            print("  STRAT",st,"tabelas",len(tbs),[len(t) for t in tbs])
            for tb in tbs[:1]:
                for row in tb[:5]: print("    ROW",json.dumps([re.sub(r"\s+"," ",c or "")[:90] for c in row],ensure_ascii=False))
        print("TEXT",pg.extract_text()[:1500].replace("\n"," | "))
