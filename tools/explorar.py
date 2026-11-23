"""Exploração: custo da Câmara (função Legislativa) por habitante, JF x cidades comparáveis. Siconfi RREO Anexo 2, 6º bim."""
import json, re, time, requests
API = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
UA = {"User-Agent": "RadarJF/1.0 (robo de transparencia; https://github.com/alemantini/radar-jf)"}
def get(rel, **p):
    out, off = [], 0
    while True:
        r = requests.get(f"{API}/{rel}", params={**p, "offset": off}, headers=UA, timeout=90); r.raise_for_status(); j = r.json()
        out += j.get("items", [])
        if not j.get("hasMore"): return out
        off += len(j["items"]); time.sleep(0.5)
entes = get("entes")
mun = [e for e in entes if e.get("esfera") == "M"]
print("municipios", len(mun), "exemplo", mun[0])
jf = next(e for e in mun if e["ente"].startswith("Juiz de Fora"))
print("JF", jf)
pop_jf = jf["populacao"]
# comparáveis: MG acima de 200 mil + Brasil entre 400 e 800 mil (fora capitais)
mg = [e for e in mun if e["uf"] == "MG" and (e["populacao"] or 0) >= 200000]
br = [e for e in mun if 400000 <= (e["populacao"] or 0) <= 800000 and str(e.get("capital") or "0").strip() == "0"]
alvo = {e["cod_ibge"]: e for e in mg + br}
print("alvos", len(alvo))
res = []
for cod, e in sorted(alvo.items(), key=lambda x: -x[1]["populacao"]):
    for ano in (2025, 2024):
        try:
            it = get("rreo", an_exercicio=ano, nr_periodo=6, co_tipo_demonstrativo="RREO", no_anexo="RREO-Anexo 02", id_ente=cod)
        except Exception as ex:
            print("erro", e["ente"], ex); continue
        if ano == 2025 and cod == jf["cod_ibge"]:
            print("colunas", sorted(set(i["coluna"] for i in it)))
            print("contas", sorted(set(i["conta"] for i in it))[:60])
        leg = [i for i in it if re.fullmatch(r"\s*Legislativa\s*", i["conta"]) and re.search(r"LIQUIDADAS AT", i["coluna"], re.I)]
        tot = [i for i in it if re.search(r"DESPESAS \(EXCETO INTRA", i["conta"], re.I) and re.search(r"LIQUIDADAS AT", i["coluna"], re.I)]
        v = leg[0]["valor"] if leg else None
        t = tot[0]["valor"] if tot else None
        res.append({"cod": cod, "ente": e["ente"], "uf": e["uf"], "pop": e["populacao"], "ano": ano, "legislativa": v, "total": t,
                    "per_capita": round(v / e["populacao"], 2) if v and e["populacao"] else None})
        print(e["ente"], e["uf"], e["populacao"], v, t)
        time.sleep(0.4)
print("RESULTADO_JSON", json.dumps(res, ensure_ascii=False))
