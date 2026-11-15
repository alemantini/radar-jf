"""Procura Juiz de Fora em decisões do TCE-MG sobre alertas da LRF."""
import re, subprocess, requests
UA = {"User-Agent": "Mozilla/5.0 (RadarJF)"}
for n in ["4768266", "4425975", "4252191"]:
    r = requests.get(f"https://tcnotas.tce.mg.gov.br/TCJuris/Nota/BuscarArquivo/{n}", headers=UA, timeout=120)
    open("/tmp/d.pdf", "wb").write(r.content)
    t = subprocess.run(["pdftotext", "-layout", "/tmp/d.pdf", "-"], capture_output=True, text=True).stdout
    print("=====", n, r.status_code, len(t))
    m = re.search(r"(Processo|PROCESSO)[^\n]{0,80}", t); print(m.group(0) if m else "")
    for d in re.findall(r"[^\n]*(?:Sess[ãa]o|sess[ãa]o)[^\n]{0,60}20\d\d[^\n]*", t)[:2]: print("  ", d.strip())
    for d in re.findall(r"[^\n]*Data[- ]?[Bb]ase[^\n]*", t)[:3]: print("  ", d.strip())
    for m in re.finditer(r"JUIZ DE FORA|Juiz de Fora", t):
        print("  >>", t[max(0, m.start()-300):m.end()+200].replace("\n", " | "))
