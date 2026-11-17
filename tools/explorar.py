"""Exploração: API do PNCP para a Prefeitura de Juiz de Fora (CNPJ 18338178000102)."""
import json, requests
CNPJ = "18338178000102"
H = {"User-Agent": "RadarJF/1.0 (transparencia)"}
def get(u, **p):
    r = requests.get(u, params=p, headers=H, timeout=90)
    print("GET", r.url, r.status_code, len(r.content))
    try:
        return r.json()
    except Exception:
        print(r.text[:300]); return None
d = get("https://pncp.gov.br/api/consulta/v1/contratos", dataInicial="20260101", dataFinal="20261116", cnpjOrgao=CNPJ, pagina=1, tamanhoPagina=10)
if d:
    print("chaves", list(d.keys()) if isinstance(d, dict) else type(d))
    itens = d.get("data", []) if isinstance(d, dict) else d
    print("total", d.get("totalRegistros"), d.get("totalPaginas"))
    if itens: print(json.dumps(itens[0], ensure_ascii=False)[:2500])
c = get("https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao", dataInicial="20260101", dataFinal="20261116", codigoModalidadeContratacao=6, cnpj=CNPJ, pagina=1, tamanhoPagina=10)
if c:
    print("total compras pregão", c.get("totalRegistros"))
    it = c.get("data", [])
    if it:
        x = it[0]; print(json.dumps(x, ensure_ascii=False)[:2000])
        ano, seq = x.get("anoCompra"), x.get("sequencialCompra")
        its = get(f"https://pncp.gov.br/api/pncp/v1/orgaos/{CNPJ}/compras/{ano}/{seq}/itens", pagina=1, tamanhoPagina=5)
        print(json.dumps(its, ensure_ascii=False)[:1500])
        if its:
            n = its[0].get("numeroItem")
            res = get(f"https://pncp.gov.br/api/pncp/v1/orgaos/{CNPJ}/compras/{ano}/{seq}/itens/{n}/resultados")
            print(json.dumps(res, ensure_ascii=False)[:1500])
if d and d.get("data"):
    k = d["data"][0]
    t = get(f"https://pncp.gov.br/api/pncp/v1/orgaos/{CNPJ}/contratos/{k.get('anoContrato')}/{k.get('sequencialContrato')}/termos")
    print(json.dumps(t, ensure_ascii=False)[:1500])
for mod in (8, 9):
    x = get("https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao", dataInicial="20260101", dataFinal="20261116", codigoModalidadeContratacao=mod, cnpj=CNPJ, pagina=1, tamanhoPagina=10)
    if x: print("modalidade", mod, "total", x.get("totalRegistros"))
