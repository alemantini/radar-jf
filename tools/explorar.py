"""Sonda 2: estrutura dos anexos da Lei 15.039/2024 (planta de valores do IPTU)."""
import io, re, requests
from pypdf import PdfReader
H = {"User-Agent": "Mozilla/5.0 (RadarJF)"}
b = requests.get("https://www.camarajf.mg.gov.br/sal/anexo.php?t=nj&cod=301", headers=H, timeout=120).content
r = PdfReader(io.BytesIO(b))
for i, p in enumerate(r.pages):
    t = p.extract_text() or ""
    tit = re.findall(r"ANEXO [IVX]+[^\n]*\n(?:[^\n]*\n){0,4}", t)
    print(f"--- pagina {i+1}: {len(t)} chars; bairro={t.lower().count('bairro')}; titulos={[re.sub(chr(10),' / ',x)[:220] for x in tit]}")
    if i in (12, 16, 20, 24) or "Bairro" in t or "BAIRRO" in t:
        print(t[:1800])
for p in r.pages[-6:]:
    print("=== FIM ===", (p.extract_text() or "")[:1500])
