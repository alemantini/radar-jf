"""Exploração 2: campos do PNCP (contratos, termos, resultados)."""
import json, requests, time
CNPJ = "18338178000102"
H = {"User-Agent": "RadarJF/1.0 (transparencia)"}
def get(u, **p):
    for t in range(3):
        try:
            r = requests.get(u, params=p, headers=H, timeout=90)
            if r.status_code == 204: return None
            if r.status_code == 200: return r.json()
            print("status", r.status_code, u); time.sleep(3)
        except Exception as e:
            print("erro", e); time.sleep(3)
d = get("https://pncp.gov.br/api/consulta/v1/contratos", dataInicial="20250101", dataFinal="20251231", cnpjOrgao=CNPJ, pagina=1, tamanhoPagina=50)
print("total contratos 2025-26:", d["totalRegistros"])
print("CHAVES contrato:", sorted(d["data"][0].keys()))
k = d["data"][0]; print({x: k.get(x) for x in k if "valor" in x.lower() or "data" in x.lower() or "tipo" in x.lower()})
tipos = {}
for k in d["data"]:
    tipos[k["tipoContrato"]["nome"]] = tipos.get(k["tipoContrato"]["nome"], 0) + 1
print("tipos na pag 1:", tipos)
achou = 0
for k in d["data"]:
    t = get(f"https://pncp.gov.br/api/pncp/v1/orgaos/{CNPJ}/contratos/{k['anoContrato']}/{k['sequencialContrato']}/termos")
    if t:
        print("TERMO de", k["anoContrato"], k["sequencialContrato"], json.dumps(t[0], ensure_ascii=False)[:1500]); achou += 1
        if achou >= 2: break
c = get("https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao", dataInicial="20250101", dataFinal="20251231", codigoModalidadeContratacao=6, cnpj=CNPJ, pagina=1, tamanhoPagina=50)
print("pregões 2025:", c["totalRegistros"])
for x in c["data"]:
    if x.get("valorTotalHomologado"):
        print("COMPRA", x["anoCompra"], x["sequencialCompra"], x["objetoCompra"][:120], x["valorTotalEstimado"], x["valorTotalHomologado"])
        its = get(f"https://pncp.gov.br/api/pncp/v1/orgaos/{CNPJ}/compras/{x['anoCompra']}/{x['sequencialCompra']}/itens", pagina=1, tamanhoPagina=3)
        for it in its or []:
            res = get(f"https://pncp.gov.br/api/pncp/v1/orgaos/{CNPJ}/compras/{x['anoCompra']}/{x['sequencialCompra']}/itens/{it['numeroItem']}/resultados")
            print("ITEM", it["descricao"][:80], it["valorUnitarioEstimado"], it.get("catalogoCodigoItem"), "->", json.dumps(res, ensure_ascii=False)[:900] if res else None)
        break
