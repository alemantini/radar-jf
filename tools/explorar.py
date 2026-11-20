import requests, re
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
B="https://www.camarajf.mg.gov.br/transparencia/"
h=requests.get(B+"extratoDeContratos.php",headers=UA,timeout=60).text
for s in re.findall(r"(?s)<script[^>]*>(.*?)</script>",h):
    if "mostraAnexo" in s: i=s.find("mostraAnexo"); print("JS",re.sub(r"\s+"," ",s[max(0,i-900):i+300]))
D=requests.get(B+"exportardata.php",params={"tpr":"CONT","tpo":"JSON","dti":"01/01/2010","dtf":"31/12/2026"},headers=UA,timeout=120).json()
for x in D:
    if x["anexo"] and re.search(r"seguro social|Jamaica|JF SISTEMA|JF Sistema",x["contratado"],re.I):
        for t in (x["tipo"], "C", "A", "T", "CONTRATO", "TERMO ADITIVO"):
            r=requests.get(B+"mostraAnexo.php",params={"t":t,"cod":x["anexo"]},headers=UA,timeout=60)
            print("ANEXO",x["numContrato"],x["tipo"],x["anexo"],"t=",t,r.status_code,r.headers.get("content-type"),len(r.content),r.content[:8])
            if r.content[:4]==b"%PDF": break
