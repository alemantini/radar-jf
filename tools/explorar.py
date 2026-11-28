"""Teste: quais sites do TCE-MG respondem a partir do GitHub (servidor nos EUA)."""
import requests
UA = {"User-Agent": "Mozilla/5.0 (RadarJF; https://github.com/alemantini/radar-jf)"}
for u in ["https://www.tce.mg.gov.br/", "https://doc.tce.mg.gov.br/", "https://dadosabertos.tce.mg.gov.br/",
          "https://fiscalizandocomtce.tce.mg.gov.br/", "https://transparencia.tce.mg.gov.br/", "https://www.tce.mg.gov.br/Processo/",
          "https://tcjuris.tce.mg.gov.br/", "https://www.tce.mg.gov.br/lupademinas/", "https://www.mg.gov.br/", "https://www.almg.gov.br/"]:
    try:
        r = requests.get(u, headers=UA, timeout=25)
        print("TESTE", r.status_code, len(r.content), u, "|", r.text[:150].replace("\n", " "))
    except Exception as e:
        print("TESTE ERRO", u, type(e).__name__, str(e)[:120])
