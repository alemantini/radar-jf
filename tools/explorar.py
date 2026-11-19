import re, requests
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
B="https://www.camarajf.mg.gov.br/transparencia/"
h=requests.get(B+"despesas.php",headers=UA,timeout=60); h.encoding="utf-8"
for s in re.findall(r"(?s)<script[^>]*>(.*?)</script>",h.text):
    if "gerarRelatorioDataPrev" in s: print("SCRIPT",re.sub(r"[ \t]+"," ",s)[:6000])
for m in re.findall(r'(?s)<div[^>]*id="divCredor".{0,1200}',h.text)[:1]: print("DIVCRED",re.sub(r"\s+"," ",m))
r=requests.get(B+"geraIntervalo.php",params={"ct":22},headers=UA,timeout=60); print("INT22",r.text[:600])
