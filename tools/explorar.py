"""Exploração das fontes públicas (só imprime amostras no log)."""
import csv, io, json, re, zipfile, requests
UA = {"User-Agent": "RadarJF/1.0 (robo de transparencia; https://github.com/alemantini/radar-jf)"}
S = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"

print("=== anexos")
r = requests.get(f"{S}/anexos-relatorios", headers=UA, timeout=120)
for x in r.json().get("items", []):
    if x.get("esfera") in ("M", "U", None) and x.get("demonstrativo") in ("RREO", "RGF"):
        print("  ", x)

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
