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
NUM = r"(?<![\d,])(?<!\d\.)(\d{1,3}(?:\.\d{3})+|\d+)"
# preços aparecem como 12.000,00 ou 3.105.076.68 (tudo com ponto) ou 15.71
PRECO = r"R\$ ?(\d{1,3}(?:\.\d{3})+\.\d{2}(?!\d)|\d{1,3}(?:\.\d{3})*,\d{2}|\d+\.\d{2}(?!\d)|\d+,\d{2})"
P0 = re.compile(NUM + r" ?" + UNID + r" ?(?:A|DE|X) ?" + PRECO)
P1 = re.compile(NUM + r" ?" + UNID + r".{0,60}?(?:CUSTO|PRECO|VALOR|VR)\.? ?UNI\w*\.? ?(?:DE)? ?" + PRECO)
P2 = re.compile(r"QUANTIDADE ?:? ?" + NUM + r".{0,160}?(?:UNITARIO|CADA).{0,20}?" + PRECO)
P3 = re.compile(NUM + r" ?" + UNID + r".{0,40}?SENDO " + PRECO + r" O VALOR DE CAD")


def sa(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper()


def preco(s):
    if "," in s:
        return float(s.replace(".", "").replace(",", "."))
    inteiro, dec = s.rsplit(".", 1)
    return float(inteiro.replace(".", "") + "." + dec)


def qtd(s):
    return int(s.replace(".", ""))


def conta(hist):
    t = re.sub(r"\s+", " ", sa(hist)).replace("-", "")
    achados = []
    if re.search(r"MENSAL|POR MES|/MES|AO MES", t) and not re.search(r"\d ?MESES", t):
        return None
    for P in (P0, P3, P1, P2):
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
        grupos = {}
        for e in B["empenhos"]:
            k = (e[ix["numero"]], e[ix["secretaria"]], e[ix["credor"]])
            g = grupos.setdefault(k, {"emp": 0.0, "pago": 0.0, "data": e[ix["data"]], "frag": {}})
            g["emp"] += e[ix["empenhado"]]
            g["pago"] += e[ix["pago"]]
            h = str(e[ix["historico"]] or "").strip()
            if h:
                g["frag"].setdefault(h, None)
            g["data"] = min(g["data"], e[ix["data"]])
        for (numero, sec_i, cred_i), g in grupos.items():
            emp = g["emp"]
            frags = list(g["frag"])
            if emp <= 0 or not frags:
                continue
            itens = [(h, conta(h)) for h in frags]
            com = [(h, c) for h, c in itens if c]
            if not com:
                continue
            calc = sum(c[0] * c[1] for _, c in com)
            todos = len(com) == len(frags)
            r = emp / calc if calc else 0
            # se todos os pedaços têm conta, compara nos dois sentidos; se faltam pedaços,
            # só marca quando os itens descritos sozinhos já passam muito do valor reservado
            marca = (todos and (r >= RAZAO or r <= 1 / RAZAO)) or (not todos and r <= 1 / RAZAO)
            if not (marca and abs(emp - calc) >= DIF_MIN):
                continue
            cr = B["credores"][cred_i] if isinstance(cred_i, int) else cred_i
            doc, nome = (cr[0], cr[1]) if isinstance(cr, list) else ("", str(cr))
            pf = len(re.sub(r"\D", "", doc)) <= 11 or bool(re.search(r"\d{11}", nome or ""))
            sec = B["secretarias"][sec_i] if isinstance(sec_i, int) else sec_i
            casos.append({
                "ano": ano, "data": g["data"], "numero": numero, "secretaria": sec,
                "credor": "Pessoa física (nome não publicado)" if pf else nome, "doc": "" if pf else doc,
                "empenhado": round(emp, 2), "pago": round(g["pago"], 2), "conta": round(calc, 2), "razao": round(r, 3),
                "completo": todos, "n_itens": len(frags),
                "itens": [{"texto": h[:300], "qtd": c[0] if c else None, "preco": c[1] if c else None} for h, c in itens][:12],
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
