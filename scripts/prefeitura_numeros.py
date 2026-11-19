"""Números que não batem: empenhos em que a descrição traz quantidade e preço unitário
e a conta (quantidade x preço) fica muito longe do valor empenhado.

Entrada: site/dados/prefeitura/empenhos_AAAA.json (gerado por prefeitura_despesas.py)
Saída: site/dados/prefeitura/numeros.json

Cuidados: a descrição às vezes cita só um item de um empenho com vários itens, ou tem erro de
digitação. Por isso a página trata cada caso como pergunta, nunca como prova, e só mostra
diferenças grandes (em proporção e em reais). Pessoas físicas não têm o nome publicado.
"""
import datetime as dt
import json
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "site" / "dados" / "prefeitura"
SAIDA = PASTA / "numeros.json"
ANOS = range(2025, dt.date.today().year + 1)
DIF_MIN = 20000      # diferença mínima em reais
RAZAO = 3            # o valor empenhado é 3 vezes maior ou menor que a conta

UNID = r"(?:UNIDADES?|UNID\.?|UNDS?\.?|UN\b|SERVICOS?|PACOTES?|DIARIAS?|KITS?|REFEICOES|CAIXAS?|LITROS?|QUANTIDADES?|LOCACOES|LOCACOERS|CABINES|VAGAS|PECAS|FARDOS|MESES|HORAS|EXEMPLARES|CESTAS|PARES)"
NUM = r"(\d{1,3}(?:\.\d{3})+|\d+)"
PRECO = r"R\$ ?(\d{1,3}(?:\.\d{3})*,\d{2}|\d+\.\d{2}|\d+,\d{2})"
P1 = re.compile(NUM + r" ?" + UNID + r".{0,140}?(?:CUSTO|PRECO|VALOR)? ?(?:UNI-?TARIO)? ?(?:DE|A|SENDO)? ?" + PRECO)
P2 = re.compile(r"QUANTIDADE ?:? ?" + NUM + r".{0,160}?(?:UNITARIO|CADA).{0,20}?" + PRECO)
P3 = re.compile(NUM + r" ?" + UNID + r".{0,40}?SENDO " + PRECO + r" O VALOR DE CAD")


def sa(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper()


def preco(s):
    if re.fullmatch(r"\d+\.\d{2}", s):
        return float(s)
    return float(s.replace(".", "").replace(",", "."))


def qtd(s):
    return int(s.replace(".", ""))


def conta(hist):
    t = re.sub(r"\s+", " ", sa(hist)).replace("-", "")
    achados = []
    for P in (P3, P1, P2):
        for m in P.finditer(t):
            q, p = qtd(m.group(1)), preco(m.group(2))
            if q > 0 and p > 0:
                achados.append((q, p, m.group(0)))
        if achados:
            break
    # só descrições com UMA conta: se aparecem vários itens, o empenho pode somar outros
    precos = re.findall(PRECO, t)
    if len(achados) != 1 or len(set(precos)) > 1:
        return None
    return achados[0]


def main():
    casos = []
    for ano in ANOS:
        f = PASTA / f"empenhos_{ano}.json"
        if not f.exists():
            continue
        B = json.loads(f.read_text())
        ix = {c: i for i, c in enumerate(B["campos"])}
        agg = {}
        for e in B["empenhos"]:
            k = (e[ix["numero"]], e[ix["secretaria"]], e[ix["credor"]], str(e[ix["historico"]])[:60])
            a = agg.get(k)
            if a is None:
                agg[k] = list(e)
            else:
                a[ix["empenhado"]] += e[ix["empenhado"]]
                a[ix["pago"]] += e[ix["pago"]]
        for a in agg.values():
            emp = a[ix["empenhado"]]
            if emp <= 0:
                continue
            c = conta(str(a[ix["historico"]]))
            if not c:
                continue
            q, p, trecho = c
            calc = q * p
            if calc <= 0:
                continue
            r = emp / calc
            if (r >= RAZAO or r <= 1 / RAZAO) and abs(emp - calc) >= DIF_MIN:
                cr = B["credores"][a[ix["credor"]]] if isinstance(a[ix["credor"]], int) else a[ix["credor"]]
                doc, nome = (cr[0], cr[1]) if isinstance(cr, list) else ("", str(cr))
                pf = len(re.sub(r"\D", "", doc)) <= 11 or re.search(r"\d{11}", nome or "")
                sec = B["secretarias"][a[ix["secretaria"]]] if isinstance(a[ix["secretaria"]], int) else a[ix["secretaria"]]
                casos.append({
                    "ano": ano, "data": a[ix["data"]], "numero": a[ix["numero"]], "secretaria": sec,
                    "credor": "Pessoa física (nome não publicado)" if pf else nome, "doc": "" if pf else doc,
                    "empenhado": round(emp, 2), "pago": round(a[ix["pago"]], 2),
                    "qtd": q, "preco": p, "conta": round(calc, 2), "razao": round(r, 2),
                    "trecho": trecho[:160], "historico": str(a[ix["historico"]])[:600],
                })
    casos.sort(key=lambda x: -abs(x["empenhado"] - x["conta"]))
    SAIDA.write_text(json.dumps({
        "atualizado": dt.date.today().isoformat(),
        "criterio": {"razao": RAZAO, "dif_min": DIF_MIN},
        "casos": casos,
    }, ensure_ascii=False, separators=(",", ":")))
    print(f"numeros.json: {len(casos)} casos")


if __name__ == "__main__":
    main()
