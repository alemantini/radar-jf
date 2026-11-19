import re, requests, json, io
from pypdf import PdfReader
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
B="https://www.camarajf.mg.gov.br/transparencia/"
for cnpj in ["29979036009105","29.979.036/0091-05","29979036009016"]:
  for ano in ["2024","2025","2026"]:
    for cod in (22,21):
        try:
            r=requests.get(B+"geraPesquisa.php",params={"codTpRel":cod,"credor":"","nempenho":"","cpf":"","cnpj":cnpj,"dia":"","mes":"","ano":ano,"anoPesquisa":ano},headers=UA,timeout=90)
            print("Q",cnpj,ano,cod,r.status_code,r.text[:500])
            data=r.json()
        except Exception as e: print("ERR",e); continue
        if isinstance(data,list) and data:
            c=data[0].get("cod") or data[0].get("cod_relatorio") or data[0].get("value")
            print("  primeiro",data[0])
