"""Exploração: onde a Câmara publica agenda de reuniões e audiências."""
import re, requests
H = {"User-Agent": "Mozilla/5.0 RadarJF"}
for u in ["https://www.camarajf.mg.gov.br/", "https://www.camarajf.mg.gov.br/sal/", "https://www.camarajf.mg.gov.br/agenda.php",
          "https://www.camarajf.mg.gov.br/sal/reunioes.php", "https://www.camarajf.mg.gov.br/sal/pauta.php", "https://www.camarajf.mg.gov.br/sal/atas.php"]:
    try:
        r = requests.get(u, headers=H, timeout=40)
        print("==", u, r.status_code, len(r.text))
        links = sorted(set(re.findall(r'href="([^"]+)"', r.text)))
        for l in links:
            if re.search(r"agenda|pauta|audien|reuni|ata|sess|evento|calend|comiss|ordem", l, re.I):
                print("   ", l)
    except Exception as e:
        print("erro", u, e)
r = requests.get("https://www.camarajf.mg.gov.br/sal/ata.php?cod=5449", headers=H, timeout=40)
print("ata", r.status_code, r.text[:300].replace("\n", " "))
