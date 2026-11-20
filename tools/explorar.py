import subprocess, json
subprocess.run(["bash","tools/versao_anterior.sh"],check=False)
t=open("/tmp/anterior/dados/prefeitura/atos_2026.json",encoding="utf-8").read()
d=json.loads(t); print("KEYS",list(d.keys()) if isinstance(d,dict) else type(d))
import re
for m in re.finditer(r"147915|105/2026|novo hospital de pronto socorro",t,re.I):
    print("@",t[max(0,m.start()-200):m.end()+2500].replace("\\n"," "))
    break
for m in re.finditer(r"(?i)seguranca eletronica ativa|seguran.a eletr.nica ativa",t):
    print("#",t[max(0,m.start()-600):m.end()+2500])
