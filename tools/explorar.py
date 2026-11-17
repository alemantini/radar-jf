"""Exploração 2: páginas de agenda e audiências da Câmara."""
import re, requests, html
H = {"User-Agent": "Mozilla/5.0 RadarJF"}
for u in ["https://www.camarajf.mg.gov.br/www/agenda-de-reunioes", "https://www.camarajf.mg.gov.br/www/audiencias-publicas",
          "https://www.camarajf.mg.gov.br/www/eventos-institucionais", "https://www.camarajf.mg.gov.br/sal/buscarreuniao.php"]:
    r = requests.get(u, headers=H, timeout=40)
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", r.text, flags=re.S)
    txt = html.unescape(re.sub(r"<[^>]+>", " ", t))
    txt = re.sub(r"\s+", " ", txt)
    i = max(0, txt.find("Agenda") if "agenda" in u else txt.find("Audi"))
    print("==", u, r.status_code, len(r.text))
    print(txt[i:i+2500])
    for f in re.findall(r'<form[^>]*>.*?</form>', r.text, flags=re.S)[:2]:
        print("FORM", re.sub(r"\s+", " ", f)[:1200])
    for l in sorted(set(re.findall(r'href="([^"]+)"', r.text))):
        if re.search(r"audien|agenda|reuni|\.ics|json|api|evento", l, re.I): print("   L", l)
