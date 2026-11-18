"""Planta Genérica de Valores de Terreno do IPTU de Juiz de Fora (áreas isótimas).

Lê o anexo oficial da Lei nº 15.039/2024 no sistema da Câmara Municipal e grava
data/prefeitura/iptu_areas.json com, para cada área isótima: valor do m² para IPTU
(Anexo I) e para ITBI (Anexo IX), grupo de redução (Anexos V a VIII: A, B, C, D) e,
para as áreas criadas em 2025, a descrição oficial (Anexo IV).
Os valores de 2026 são estes corrigidos pelo IPCA (Lei nº 14.544/2022, art. 11),
mesma correção para todas as áreas; a ordem do ranking não muda.
"""
import io
import json
import re
from datetime import date
from pathlib import Path

import requests
from pypdf import PdfReader

URL = "https://www.camarajf.mg.gov.br/sal/anexo.php?t=nj&cod=301"
NORMA = "https://www.camarajf.mg.gov.br/sal/norma.php?njn=15039&njc=&njt=LEI"
SAIDA = Path(__file__).resolve().parent.parent / "data" / "prefeitura" / "iptu_areas.json"
COD = r"[A-Z]{2}\d{3}"


def num(t):
    return float(t.replace(".", "").replace(",", "."))


def main():
    b = requests.get(URL, headers={"User-Agent": "Mozilla/5.0 (RadarJF)"}, timeout=120).content
    txt = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(b)).pages)
    partes = re.split(r"\n\s*ANEXO ([IVX]+)\s*\n", "\n" + txt)
    sec = {partes[i]: partes[i + 1] for i in range(1, len(partes) - 1, 2)}
    par = lambda t: {c: num(v) for c, v in re.findall(rf"\b({COD}) ([\d\.]+,\d{{2}})\b", t)}
    iptu, itbi = par(sec.get("I", "")), par(sec.get("IX", ""))
    grupo = {}
    for rom, g in (("V", "A"), ("VI", "B"), ("VII", "C"), ("VIII", "D")):
        for c in re.findall(rf"\b({COD})\b", sec.get(rom, "")):
            grupo.setdefault(c, g)
    criadas = {}
    for linha in sec.get("IV", "").splitlines():
        m = re.match(rf"\s*({COD}) ({COD}) (.+)", linha)
        if m:
            criadas[m.group(1)] = {"origem": m.group(2), "descricao": m.group(3).strip()}
    areas = [{"cod": c, "iptu": v, "itbi": itbi.get(c), "grupo": grupo.get(c, ""), **({"descricao": criadas[c]["descricao"]} if c in criadas else {})}
             for c, v in iptu.items()]
    areas.sort(key=lambda a: -a["iptu"])
    out = {"ano_valores": 2025, "lei": "Lei nº 15.039, de 19 de dezembro de 2024", "fonte": NORMA, "anexo": URL,
           "baixado_em": date.today().isoformat(), "areas": areas,
           "grupos": {g: sum(1 for a in areas if a["grupo"] == g) for g in "ABCD"}}
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(areas)} áreas; ITBI {len(itbi)}; grupos {out['grupos']}; criadas {len(criadas)}")
    print("mais caras:", [(a['cod'], a['iptu']) for a in areas[:10]])
    print("mais baratas:", [(a['cod'], a['iptu']) for a in areas[-10:]])
    print("criadas:", list(criadas.items())[:5])


if __name__ == "__main__":
    main()
