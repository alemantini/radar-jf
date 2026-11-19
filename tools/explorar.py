import requests
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
B="https://www.camarajf.mg.gov.br/transparencia/"
tests=[("Jamaica","",""),("","","03922282000172"),("Instituto Nacional","",""),("INSS","",""),("Seguro Social","",""),("","","03.922.282/0001-72")]
for credor,cpf,cnpj in tests:
    for ano in ("2025","2026"):
        for cod in (22,21):
            r=requests.get(B+"geraPesquisa.php",params={"codTpRel":cod,"credor":credor,"nempenho":"","cpf":cpf,"cnpj":cnpj,"dia":"","mes":"","ano":ano,"anoPesquisa":ano},headers=UA,timeout=90)
            print("Q",repr(credor),cnpj,ano,cod,r.status_code,len(r.text),r.text[:400])
