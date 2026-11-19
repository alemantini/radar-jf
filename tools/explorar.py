import re, requests
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
r=requests.get("https://www.camarajf.mg.gov.br/transparencia/js/funcoes.js?v=1",headers=UA,timeout=40); r.encoding="utf-8"; js=r.text
print("LEN",len(js))
for nome in ["geraIntervalo","gerarRelatorioPeriodoSeparado","jumpto"]:
    i=js.find("function "+nome)
    print("=====",nome,i); print(js[i:i+3500] if i>=0 else "")
for m in set(re.findall(r"[\w/.\-]+\.php[^'\"]*",js)): print("PHP",m)
