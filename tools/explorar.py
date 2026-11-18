"""Sonda: anexos da planta de valores do IPTU (Lei 15.039/2024 e a lei de 2025 para 2026)."""
import io, re, requests
from pypdf import PdfReader
H = {"User-Agent": "Mozilla/5.0 (RadarJF)"}
def norma(n):
    t = requests.get(f"https://www.camarajf.mg.gov.br/sal/norma.php?njn={n}&njc=&njt=LEI", headers=H, timeout=60).text
    return t
for n in ("15039", "15068"):
    t = norma(n)
    em = re.search(r"Ementa:.*?\n(.*?)\n", re.sub(r"<[^>]+>", "\n", t), re.S)
    anexos = re.findall(r'href="([^"]*anexo\.php[^"]*)"[^>]*>([^<]*)', t)
    print("LEI", n, anexos, re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))[200:700])
    for href, nome in anexos[:2]:
        url = requests.compat.urljoin("https://www.camarajf.mg.gov.br/sal/", href)
        b = requests.get(url, headers=H, timeout=120).content
        r = PdfReader(io.BytesIO(b))
        print("PDF", nome, len(b), "paginas", len(r.pages))
        txt = "\n".join((p.extract_text() or "") for p in r.pages)
        cods = re.findall(r"\b([A-Z]{2}\d{3})\b", txt)
        print("codigos", len(cods), len(set(cods)))
        print(txt[:3000])
        print("..... MEIO .....")
        i = len(txt) // 2
        print(txt[i:i + 2500])
        for kw in ("ANEXO", "Anexo"):
            for m in re.finditer(kw + r"[^\n]{0,120}", txt):
                print("  >>", m.group(0)[:130])
# lei de 2025 para 2026 (Mensagem 4718/2025)
t = requests.get("https://www.camarajf.mg.gov.br/sal/buscanormas.php?palavra=%C1REAS+IS%D3TIMAS", headers=H, timeout=60).text
print("BUSCA", re.findall(r"norma\.php\?njn=(\d+)[^\"]*njt=(\w+)", t)[:20])
