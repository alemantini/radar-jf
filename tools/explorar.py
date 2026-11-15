"""Exploração das fontes públicas (só imprime amostras no log)."""
import csv, io, json, re, zipfile, requests
UA = {"User-Agent": "RadarJF/1.0 (robo de transparencia; https://github.com/alemantini/radar-jf)"}
S = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"

print("=== anexos RREO JF 2025 bim 6")
for n in ["06", "07", "08", "09", "10", "11", "12", "13", "14"]:
    try:
        r = requests.get(f"{S}/rreo", params=dict(an_exercicio=2025, nr_periodo=6, co_tipo_demonstrativo="RREO", no_anexo=f"RREO-Anexo {n}", id_ente=3136702), headers=UA, timeout=180)
        it = r.json().get("items", [])
        print("Anexo", n, len(it))
        for x in it:
            if re.search(r"percentual|m[íi]nimo|25%|15%", x.get("conta", "") + " " + x.get("coluna", ""), re.I):
                print("   ", x["conta"][:120], "|", x["coluna"][:60], "|", x["valor"])
    except Exception as e:
        print("Anexo", n, "erro", e)

print("=== Câmara remuneração")
r = requests.get("https://www.camarajf.mg.gov.br/transparencia/remuneracaoServidores.php", headers=UA, timeout=60)
t = r.text
print(r.status_code, len(t))
for m in re.finditer(r"<(form|select|input|option|a)\b[^>]*>", t, re.I):
    print("  ", m.group(0)[:200])
print(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))[:3000])

def zipinfo(f, alvo=None, filtro=None, n=3):
    url = "https://cdn.tse.jus.br/estatistica/sead/odsele/" + f
    b = requests.get(url, headers=UA, timeout=600).content
    z = zipfile.ZipFile(io.BytesIO(b))
    print("##", f, [i.filename for i in z.infolist()][:40])
    if alvo:
        nome = next((i.filename for i in z.infolist() if alvo in i.filename), None)
        if nome:
            with z.open(nome) as fh:
                rd = csv.reader(io.TextIOWrapper(fh, encoding="latin-1"), delimiter=";")
                cab = next(rd); print("cabeçalho:", cab)
                k = 0
                for row in rd:
                    d = dict(zip(cab, row))
                    if filtro(d):
                        print("  ", {c: d[c] for c in cab if d[c] not in ("", "#NULO", "#NULO#", "-1", "-3")})
                        k += 1
                        if k >= n: break

jf = lambda d: d.get("NM_UE", d.get("NM_MUNICIPIO", "")) == "JUIZ DE FORA" and d.get("DS_CARGO", "VEREADOR").upper() == "VEREADOR"
zipinfo("consulta_cand/consulta_cand_2024.zip", "_MG.csv", jf)
zipinfo("bem_candidato/bem_candidato_2024.zip", "_MG.csv", lambda d: d.get("NM_UE") == "JUIZ DE FORA")
zipinfo("votacao_candidato_munzona/votacao_candidato_munzona_2024.zip", "_MG.csv", jf, 2)
