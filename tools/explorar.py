"""Exploração das fontes públicas (só imprime amostras no log)."""
import csv, io, re, zipfile, requests, shutil
UA = {"User-Agent": "RadarJF/1.0 (robo de transparencia; https://github.com/alemantini/radar-jf)"}

print("=== Câmara remuneração: setores e scripts")
B = "https://www.camarajf.mg.gov.br/transparencia/"
t = requests.get(B + "remuneracaoServidores.php", headers=UA, timeout=60).text
sel = re.search(r'<select id="codsetor".*?</select>', t, re.S)
if sel:
    for v, txt in re.findall(r'<option value="(\d*)"[^>]*>([^<]*)', sel.group(0)):
        print("  setor", v, txt.strip())
for m in re.finditer(r"[\w/.-]+\.php[^\"' ]*", t):
    print("  php:", m.group(0))
for m in re.finditer(r"<script[^>]*>(.*?)</script>", t, re.S):
    c = m.group(1)
    if "ajax" in c or ".php" in c or "codsetor" in c:
        print("  SCRIPT:", re.sub(r"\s+", " ", c)[:1500])

print("=== Prestação de contas 2024")
url = "https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2024.zip"
with requests.get(url, headers=UA, timeout=900, stream=True) as r:
    with open("/tmp/pc.zip", "wb") as f:
        shutil.copyfileobj(r.raw, f, 1 << 20)
z = zipfile.ZipFile("/tmp/pc.zip")
nomes = [i.filename for i in z.infolist() if "_MG" in i.filename or "BRASIL" in i.filename]
print(nomes)
for nome in nomes:
    if "_MG" not in nome:
        continue
    with z.open(nome) as fh:
        rd = csv.reader(io.TextIOWrapper(fh, encoding="latin-1"), delimiter=";")
        cab = next(rd); print("##", nome); print("cab:", cab)
        for row in rd:
            d = dict(zip(cab, row))
            if d.get("NM_UE") == "JUIZ DE FORA" and d.get("DS_CARGO", "").upper() == "VEREADOR":
                print("  ", {c: d[c] for c in cab if d[c] not in ("", "#NULO", "#NULO#", "-1", "-3")}); break
