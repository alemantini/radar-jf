"""Exploração das fontes públicas (só imprime amostras no log)."""
import json, re, requests
UA = {"User-Agent": "RadarJF/1.0 (robo de transparencia; https://github.com/alemantini/radar-jf)"}
S = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"

def get(url, **p):
    try:
        r = requests.get(url, params=p, headers=UA, timeout=120)
        print(f"-- {r.status_code} {r.url[:160]}")
        return r
    except Exception as e:
        print("-- erro", url, e)

def siconfi(rel, **p):
    r = get(f"{S}/{rel}", **p)
    try:
        return r.json().get("items", [])
    except Exception:
        return []

print("=== RGF anexo 1 JF 2025 Q3 / 2026 Q2")
for ano, per in [(2025, 3), (2026, 2), (2026, 1)]:
    it = siconfi("rgf", an_exercicio=ano, in_periodicidade="Q", nr_periodo=per, co_tipo_demonstrativo="RGF",
                 no_anexo="RGF-Anexo 01", co_esfera="M", co_poder="E", id_ente=3136702)
    print(ano, per, len(it))
    for x in it:
        if re.search(r"DESPESA TOTAL COM PESSOAL|RECEITA CORRENTE L|LIMITE", x.get("conta", ""), re.I):
            print("  ", x.get("conta")[:90], "|", x.get("coluna"), "|", x.get("valor"))
    if it:
        break

for anexo in ["RREO-Anexo 08", "RREO-Anexo 12"]:
    print("===", anexo)
    for ano, bim in [(2026, 4), (2026, 3), (2025, 6)]:
        it = siconfi("rreo", an_exercicio=ano, nr_periodo=bim, co_tipo_demonstrativo="RREO", no_anexo=anexo, id_ente=3136702)
        print(ano, bim, len(it))
        for x in it:
            if re.search(r"PERCENTUAL|M[ÍI]NIMO|APLICA", x.get("conta", ""), re.I):
                print("  ", x.get("conta")[:110], "|", x.get("coluna"), "|", x.get("valor"))
        if it:
            break

print("=== RREO anexo 2 (função) JF 2025 bim 6, amostra")
it = siconfi("rreo", an_exercicio=2025, nr_periodo=6, co_tipo_demonstrativo="RREO", no_anexo="RREO-Anexo 02", id_ente=3136702)
cols = sorted({x.get("coluna") for x in it})
print("colunas:", cols)
for x in it:
    if x.get("coluna", "").upper().startswith("DESPESAS LIQUIDADAS AT") and re.match(r"^(Saúde|Educação|Segurança|Urbanismo|Saneamento|Assistência|Transporte|Administração|Legislativa)", x.get("conta", "")):
        print("  ", x.get("conta"), "|", x.get("coluna"), "|", x.get("valor"))
print("chaves:", list(it[0].keys()) if it else None)

print("=== entes MG maiores")
it = siconfi("entes")
mg = sorted([e for e in it if e.get("uf") == "MG" and e.get("esfera") == "M"], key=lambda e: -(e.get("populacao") or 0))[:12]
for e in mg:
    print("  ", e.get("cod_ibge"), e.get("ente"), e.get("populacao"))

print("=== TSE")
for f in ["consulta_cand/consulta_cand_2024.zip", "bem_candidato/bem_candidato_2024.zip", "bem_candidato/bem_candidato_2020.zip",
          "votacao_candidato_munzona/votacao_candidato_munzona_2024.zip",
          "prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2024.zip", "consulta_cand/consulta_cand_2020.zip"]:
    try:
        r = requests.head("https://cdn.tse.jus.br/estatistica/sead/odsele/" + f, headers=UA, timeout=60, allow_redirects=True)
        print("  ", r.status_code, f, r.headers.get("content-length"))
    except Exception as e:
        print("  erro", f, e)

print("=== Câmara transparência")
for u in ["https://www.camarajf.mg.gov.br/transparencia/", "https://www.camarajf.mg.gov.br/www/transparencia"]:
    r = get(u)
    if r is not None and r.ok:
        for m in re.finditer(r'href="([^"]+)"[^>]*>([^<]{2,80})<', r.text):
            if re.search(r"servid|folha|pessoal|di[áa]ria|gabinete|despes|remunera|lota", m.group(0), re.I):
                print("  ", m.group(2).strip(), "->", m.group(1))
