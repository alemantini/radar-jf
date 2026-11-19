import re, requests, io
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
B="https://www.camarajf.mg.gov.br/transparencia/"
def g(u):
    r=requests.get(u,headers=UA,timeout=60); return r
def txt(h):
    h=re.sub(r"(?s)<script.*?</script>|<style.*?</style>","",h)
    h=re.sub(r"<(br|/tr|/p|/li|/h\d|/div)[^>]*>","\n",h); h=re.sub(r"<t[dh][^>]*>"," | ",h)
    t=re.sub(r"<[^>]+>","",h); t=re.sub(r"[ \t]+"," ",t); return re.sub(r"\n\s*\n+","\n",t)
for ct in (15,25,5):
    r=g(B+f"geraIntervalo.php?ct={ct}"); r.encoding="utf-8"
    print("===== ct",ct,r.status_code); print(r.text[:2500])
    cods=re.findall(r"value=['\"]?(\d{4,6})",r.text)
    print("COD",cods[:40])
    for c in cods[:2]:
        for u in [f"{B}exportar.php?cod={c}&tp=html", f"https://www.camarajf.mg.gov.br/relatorio.php?cod_relatorio={c}&tp=xls"]:
            x=g(u); print("--",u,x.status_code,x.headers.get("content-type"),len(x.content))
            if "html" in (x.headers.get("content-type") or "") or u.endswith("html"):
                x.encoding=x.apparent_encoding; print(txt(x.text)[:3500])
            else: print(x.content[:1500])
from pypdf import PdfReader
x=g(B+"termocessao/2025/pardal.pdf"); print("== termo",x.status_code,len(x.content))
try:
    p=PdfReader(io.BytesIO(x.content)); print(len(p.pages)); print((p.pages[0].extract_text() or "")[:1500])
except Exception as e: print(e)
