"""Exploração: emendas 'Executada' com valor pago zero ou vazio na planilha oficial."""
import csv, io, sys, collections, requests
sys.path.insert(0, "scripts")
from prefeitura_emendas import url_planilha
r = requests.get(url_planilha(), timeout=180)
linhas = list(csv.DictReader(io.StringIO(r.content.decode("utf-8", "replace"))))
print("colunas:", list(linhas[0].keys()))
c = collections.Counter(); ex = []
for x in linhas:
    if "munic" not in (x.get("Origem dos recursos") or "").lower():
        continue
    s = (x.get("Situação administrativa") or "").strip(); v = (x.get("Valor Pago") or "").strip()
    k = "vazio" if not v else ("zero" if v.replace("R$", "").strip() in ("0", "0,00", "0.00") else "valor")
    c[(s, k)] += 1
    if s.lower().startswith("execut") and k != "valor" and len(ex) < 5:
        ex.append({kk: vv for kk, vv in x.items() if vv and len(vv) < 80})
for k, v in sorted(c.items()):
    print(v, k)
for e in ex:
    print(e)
