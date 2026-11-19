import re, requests
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
B="https://www.camarajf.mg.gov.br/transparencia/"
for pg in ["extratoDeContratos.php","index.php"]:
    r=requests.get(B+pg,headers=UA,timeout=60); r.encoding="utf-8"; h=r.text
    print("=====",pg)
    for m in re.finditer(r'(?is)<(form|select|button|input|a)[^>]*(onclick|action|name|id|href)=[^>]*>', h):
        s=m.group(0)
        if re.search(r"relat|gera|emit|contrat|termo|cess|loca|ct=|cod",s,re.I): print("  ",re.sub(r"\s+"," ",s)[:260])
    for s in re.findall(r"(?s)<script[^>]*>(.*?)</script>",h):
        if re.search(r"relat|contrat|gera",s,re.I): print("--SCRIPT--",re.sub(r"\s+"," ",s)[:1500])
    for t in re.findall(r"(?i)termo[^<]{0,80}",h)[:20]: print("  TXT",t)
