"""Exploração 5: testa os temas de fiscalização e procura fontes de diárias, atas e plano de governo."""
import json, re, subprocess, sys, html, requests
from pathlib import Path
H = {"User-Agent": "Mozilla/5.0 RadarJF"}
P = Path("site/dados/prefeitura"); P.mkdir(parents=True, exist_ok=True)
for a in (2025, 2026):
    r = requests.get(f"https://jflandia.com.br/dados/prefeitura/empenhos_{a}.json", timeout=120)
    (P / f"empenhos_{a}.json").write_bytes(r.content)
subprocess.run([sys.executable, "scripts/prefeitura_fiscalize.py"], check=True)
F = json.loads((P / "fiscalize.json").read_text())
for k, t in F["temas"].items():
    print("\n=====", k, t["anos"], "subtemas:", t["subtemas"][:5])
    print("  forn:", [(f[1][:30], round(f[3] / 1e3)) for f in t["fornecedores"][:12]])
    for i in t["itens"][:14]:
        print("   ", i[0], i[3][:28], round(i[5]), "|", i[9], "|", i[7][:110])
print("escolas:", len(F["temas"]["escolas"]["lista"]), F["temas"]["escolas"]["lista"][:6])
O = json.loads((P / "obras.json").read_text())
par = [o for o in O["obras"] if o[9]]
print("\nOBRAS", len(O["obras"]), "paradas", len(par))
for o in par[:15]:
    print("   ", o[1], o[3][:28], round(o[5]), "|", o[7][:120])

def tx(u, **k):
    try:
        r = requests.get(u, headers=H, timeout=60, **k)
        r.encoding = r.apparent_encoding or "utf-8"
        return r.status_code, r.text
    except Exception as e:
        return 0, str(e)

print("\n===== CÂMARA transparência (diárias)")
s, t = tx("https://www.camarajf.mg.gov.br/transparencia/")
print(s, len(t))
for l in sorted(set(re.findall(r'href="([^"]+)"', t))):
    if re.search(r"diar|viag|passag|publicid|contrat|despes", l, re.I): print("  L", l)
print("\n===== CÂMARA atas")
s, t = tx("https://www.camarajf.mg.gov.br/sal/buscaratas.php")
print(s, re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))[:800])
for f in re.findall(r"<form[^>]*>", t): print("  FORM", f)
for f in re.findall(r'<(?:select|input)[^>]*name="([^"]+)"', t): print("  CAMPO", f)
print("\n===== TSE plano de governo (JF 47333)")
for u in ["https://divulgacandcontas.tse.jus.br/divulga/rest/v1/candidatura/listar/2024/47333/2045202024/11/candidatos"]:
    s, t = tx(u)
    print(s, t[:1500])
