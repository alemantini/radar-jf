"""Exploração 4: blocos das audiências públicas e a Ordem do Dia."""
import re, requests, html
H = {"User-Agent": "Mozilla/5.0 RadarJF"}
r = requests.get("https://www.camarajf.mg.gov.br/www/audiencias-publicas", headers=H, timeout=40)
r.encoding = r.apparent_encoding or "utf-8"
t = r.text
for m in list(re.finditer(r"Tema da Audi", t))[:3]:
    print("BLOCO:", t[m.start()-900:m.start()+900].replace("\n", " "))
    print("-----")
print("n temas:", len(re.findall(r"Tema da Audi", t)))
txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "\n", re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S))))
k = txt.find("Audiências Públicas - ")
print("TEXTO:", txt[k:k+3500])
r2 = requests.get("https://www.camarajf.mg.gov.br/www/ordem-do-dia", headers=H, timeout=40)
print("ORDEM", r2.status_code)
for l in sorted(set(re.findall(r'href="([^"]+)"', r.text + r2.text))):
    if re.search(r"ordem|pauta|reuniao|reunioes-ordinarias|itinerante", l, re.I): print("  L", l)
