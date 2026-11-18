"""Exploração 6: diárias da Câmara (xlsx) e atas (PDF) para presença e votações."""
import io, re, requests
from openpyxl import load_workbook
from pypdf import PdfReader
H = {"User-Agent": "Mozilla/5.0 RadarJF"}
B = "https://www.camarajf.mg.gov.br/"
s = requests.get(B + "transparencia/viagens.php", headers=H, timeout=60)
print("viagens.php", s.status_code, sorted(set(re.findall(r"cod_relatorio=(\d+)[^'\"]*", s.text)))[:20])
print([l for l in re.findall(r"geraIntervalo\([^)]*\)", s.text)][:6])
for js in re.findall(r'<script[^>]*src="([^"]+)"', s.text):
    if "jquery" in js or "bootstrap" in js: continue
    try:
        j = requests.get(requests.compat.urljoin(B + "transparencia/", js), headers=H, timeout=30).text
        for m in re.findall(r"function geraIntervalo[\s\S]{0,1800}", j): print("JS", js, m)
    except Exception as e: print("js erro", e)
for m in re.findall(r"function geraIntervalo[\s\S]{0,1800}", s.text): print("INLINE", m)
for cod in (23703, 23704):
    r = requests.get(B + f"transparencia/relatorio.php?cod_relatorio={cod}&tp=xls", headers=H, timeout=60)
    print("\nXLS", cod, r.status_code, r.headers.get("content-type"), len(r.content))
    try:
        wb = load_workbook(io.BytesIO(r.content), read_only=True)
        for ws in wb.worksheets:
            print(" aba", ws.title)
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i < 14 or i % 40 == 0: print("  ", row)
            print("  linhas", i)
    except Exception as e: print(" erro", e)
for cod in (5571, 5566, 5567):
    r = requests.get(B + f"sal/ata.php?cod={cod}", headers=H, timeout=90)
    print("\nATA", cod, r.status_code, len(r.content))
    try:
        t = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(r.content)).pages)
        t1 = re.sub(r"\s+", " ", t)
        print(" inicio:", t1[:1500])
        for k in ("presen", "ausen", "votação nominal", "votaram", "SIM", "aprovad", "rejeitad", "manteve o veto", "veto"):
            for m in list(re.finditer(k, t1))[:3]:
                print(f" [{k}]", t1[max(0, m.start() - 250):m.start() + 350])
    except Exception as e: print(" erro", e)
