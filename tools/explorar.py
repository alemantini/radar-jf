"""Exploração: gestão fiscal da Fazenda (TCE-MG Diário Oficial de Contas + Siconfi)."""
import io
import re
import time

import requests
from pypdf import PdfReader

UA = {"User-Agent": "RadarJF/1.0 (robo de transparencia; https://github.com/alemantini/radar-jf)"}
DIARIOS = ["2023_05_19", "2025_02_17", "2025_06_06", "2026_01_23", "2026_01_30", "2026_02_12", "2026_05_04"]
TERMOS = re.compile(r"finotti", re.I)


def limpa(t):
    return re.sub(r"\s+", " ", t)


print("=== TCE-MG: Diário Oficial de Contas ===")
for d in DIARIOS:
    url = f"https://doc.tce.mg.gov.br/Home/ViewDiario/{d}_Diario.pdf"
    try:
        r = requests.get(url, headers=UA, timeout=120)
        print("DIARIO", d, r.status_code, len(r.content))
        pdf = PdfReader(io.BytesIO(r.content))
        for i, pg in enumerate(pdf.pages):
            txt = limpa(pg.extract_text() or "")
            for m in TERMOS.finditer(txt):
                a = max(0, m.start() - 1800)
                print(f"HIT {d} p{i+1}: ...{txt[a:m.end()+900]}...")
                print("-----")
    except Exception as e:
        print("ERRO", d, e)
    time.sleep(2)

print("=== Siconfi: RREO Anexo 01 (6º bimestre) ===")
API = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
CHAVE = re.compile(r"^(RECEITAS \(EXCETO INTRA|TOTAL DAS RECEITAS|SUBTOTAL DAS RECEITAS|DESPESAS \(EXCETO INTRA|TOTAL DAS DESPESAS|SUBTOTAL DAS DESPESAS|D[ÉE]FICIT|SUPER[ÁA]VIT|RECEITAS CORRENTES|DESPESAS CORRENTES|Impostos)", re.I)
for ano in range(2020, 2026):
    try:
        j = requests.get(f"{API}/rreo", params={"an_exercicio": ano, "nr_periodo": 6, "co_tipo_demonstrativo": "RREO",
                         "no_anexo": "RREO-Anexo 01", "id_ente": 3136702}, headers=UA, timeout=90).json()
        for it in j.get("items", []):
            if CHAVE.search(it["conta"] or ""):
                print("RREO", ano, "|", it["conta"], "|", it["coluna"], "|", it["valor"])
    except Exception as e:
        print("ERRO RREO", ano, e)
    time.sleep(1)

print("=== Siconfi: RGF Anexo 01 (pessoal, Executivo, 3º quadrimestre) ===")
for ano in range(2020, 2027):
    for per in ([3] if ano < 2026 else [1, 2]):
        try:
            j = requests.get(f"{API}/rgf", params={"an_exercicio": ano, "in_periodicidade": "Q", "nr_periodo": per,
                             "co_tipo_demonstrativo": "RGF", "no_anexo": "RGF-Anexo 01", "co_poder": "E",
                             "id_ente": 3136702}, headers=UA, timeout=90).json()
            for it in j.get("items", []):
                c = it["conta"] or ""
                if re.search(r"DESPESA TOTAL COM PESSOAL|RECEITA CORRENTE L[ÍI]QUIDA|LIMITE (M[ÁA]XIMO|PRUDENCIAL|DE ALERTA)", c, re.I):
                    print("RGF", ano, f"Q{per}", "|", c, "|", it["coluna"], "|", it["valor"])
        except Exception as e:
            print("ERRO RGF", ano, per, e)
        time.sleep(1)
print("FIM")
