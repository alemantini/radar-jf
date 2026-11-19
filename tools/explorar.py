import re, requests, io
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
def txt(h):
    h=re.sub(r"(?s)<script.*?</script>|<style.*?</style>","",h)
    h=re.sub(r"<(br|/tr|/p|/li|/h\d|/div)[^>]*>","\n",h); h=re.sub(r"<td[^>]*>"," | ",h)
    t=re.sub(r"<[^>]+>","",h); t=re.sub(r"[ \t]+"," ",t); return re.sub(r"\n\s*\n+","\n",t)
for u in ["https://www.camarajf.mg.gov.br/transparencia/combustiveis.php","https://www.camarajf.mg.gov.br/transparencia/viagens.php"]:
    r=requests.get(u,headers=UA,timeout=40); r.encoding="utf-8"; t=txt(r.text)
    i=t.find("Despesas com Combust") if "combust" in u else t.find("Viagens")
    print("=====",u); print(t[max(0,i-200):i+5000])
    for h,a in re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>',r.text,re.S):
        if re.search(r"pdf|xls|csv|ods|relatorio|anexo",h,re.I): print("  LINK",re.sub("<[^>]+>","",a).strip()[:60],"|",h)
from pypdf import PdfReader
for u in ["https://www.camarajf.mg.gov.br/transparencia/termocessao/2025/locacao.pdf"]:
    r=requests.get(u,headers=UA,timeout=60); print("=====",u,r.status_code,len(r.content))
    try:
        p=PdfReader(io.BytesIO(r.content)); print("paginas",len(p.pages))
        for pg in p.pages[:6]: print((pg.extract_text() or "")[:2500])
    except Exception as e: print("ERRO",e)
