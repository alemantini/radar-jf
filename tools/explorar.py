import re, requests
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
for u in ["https://www.camarajf.mg.gov.br/transparencia/combustiveis.php","https://www.camarajf.mg.gov.br/transparencia/viagens.php"]:
    r=requests.get(u,headers=UA,timeout=40); r.encoding="utf-8"; h=r.text
    print("=====",u)
    i=h.find("Conheça"); seg=h[i:i+9000]
    print(re.sub(r"\n\s*\n+","\n",seg))
    for m in re.finditer(r"(?s)<script[^>]*>(.*?)</script>",h):
        s=m.group(1)
        if re.search(r"relat|ajax|emitir|combust|diaria|\.php",s,re.I): print("--SCRIPT--\n",s[:3000])
    for s in re.findall(r'<script[^>]+src="([^"]+)"',h): print("SRC",s)
