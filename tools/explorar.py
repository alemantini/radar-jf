import re, requests, io, json
from pypdf import PdfReader
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
B="https://www.camarajf.mg.gov.br/transparencia/"
r=requests.get(B,headers=UA,timeout=60); r.encoding="utf-8"; h=r.text
print("CNPJ",set(re.findall(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}",h)))
links=re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>',h,re.S)
KW=re.compile(r"loca|alug|im[oó]v|contrat|cess|patrim",re.I)
alvo=[]
for u,t in links:
    t=re.sub(r"<[^>]+>|\s+"," ",t).strip()
    if KW.search(t+u): print("LINK",t[:80],"|",u); alvo.append(requests.compat.urljoin(B,u))
for u in dict.fromkeys(alvo):
    if not u.startswith("https://www.camarajf"): continue
    try: x=requests.get(u,headers=UA,timeout=60)
    except Exception as e: print("ERR",u,e); continue
    print("=====",u,x.status_code,x.headers.get("content-type"),len(x.content))
    if x.content[:4]==b"%PDF":
        p=PdfReader(io.BytesIO(x.content)); print("pags",len(p.pages)," texto:",(p.pages[0].extract_text() or "")[:800])
    else:
        x.encoding="utf-8"; t=re.sub(r"(?s)<script.*?</script>|<style.*?</style>","",x.text)
        t=re.sub(r"<[^>]+>"," ",t); t=re.sub(r"\s+"," ",t)
        i=max(0,t.lower().find("loca")-300); print(t[i:i+1500])
        for u2,t2 in re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>',x.text,re.S):
            t2=re.sub(r"<[^>]+>|\s+"," ",t2).strip()
            if re.search(r"\.pdf|loca|alug|im[oó]v|contrato\.php|cod=",u2+t2,re.I): print("   ->",t2[:70],"|",u2)
