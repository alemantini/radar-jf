"""Emendas de vereadores que pagaram festas, shows, torneios e outros eventos (2025 e 2026).

Fonte: Diário Oficial do Município (Atos do Governo, https://www.pjf.mg.gov.br/e_atos/e_atos.php),
cruzado com o Monitor de Emendas da Prefeitura para saber de quem é cada emenda.

A apuração foi feita à mão em 26/11/2026 (o site da Prefeitura bloqueia o robô), lendo todos os
1.078 atos de 2025 e 2026 que citam "emenda parlamentar", "emenda individual" ou "EPI".
Entram as emendas cujo ato (ou o objeto da emenda no Monitor) fala em evento, festa, festival,
show, torneio, campeonato, copa, corrida, carnaval, folia, feira, mostra e parecidos.
Fica fora o que é só compra de material, obra ou custeio sem evento.
O dado bruto revisado está em data/manual/emendas_eventos_bruto.jsonl.

Saída: data/prefeitura/emendas_eventos.json (copiado para o site pelo workflow).
"""
import json
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BRUTO = RAIZ / "data" / "manual" / "emendas_eventos_bruto.jsonl"
SAIDA = RAIZ / "data" / "prefeitura" / "emendas_eventos.json"

CATEGORIAS = {
    "musica": "Música e shows",
    "gastronomia": "Gastronomia e cerveja",
    "esporte": "Esporte",
    "agro": "Agropecuária e torneio leiteiro",
    "religioso": "Religioso",
    "carnaval": "Carnaval, blocos e folia",
    "diversidade": "Orgulho LGBTQIA+ e Miss Gay",
    "artes": "Cinema, teatro e cultura",
    "turismo": "Turismo e negócios",
    "outros": "Outros eventos",
}


def main():
    itens = []
    for linha in BRUTO.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        a, ep, prop, valor, data, atos, benef, evento, cat, misto = json.loads(linha)
        assert cat in CATEGORIAS, cat
        itens.append({"ano": a, "ep": ep, "p": prop, "v": round(float(valor), 2), "d": data,
                      "atos": atos, "benef": benef, "ev": evento, "cat": cat, "misto": bool(misto)})
    chaves = [(i["ano"], i["ep"]) for i in itens]
    assert len(chaves) == len(set(chaves)), "emenda repetida"

    por_cat = defaultdict(lambda: {"n": 0, "v": 0.0})
    por_ano = defaultdict(lambda: {"n": 0, "v": 0.0})
    for i in itens:
        por_cat[i["cat"]]["n"] += 1
        por_cat[i["cat"]]["v"] += i["v"]
        por_ano[i["ano"]]["n"] += 1
        por_ano[i["ano"]]["v"] += i["v"]

    saida = {
        "apurado_em": "26/11/2026",
        "periodo": "atos publicados de 01/01/2025 a 26/11/2026",
        "fonte": "Diário Oficial do Município (Atos do Governo) e Monitor de Emendas da Prefeitura",
        "fonte_url": "https://www.pjf.mg.gov.br/e_atos/e_atos.php",
        "atos_lidos": 1078,
        "categorias": CATEGORIAS,
        "total": {"n": len(itens), "v": round(sum(i["v"] for i in itens), 2)},
        "por_ano": {str(k): {"n": x["n"], "v": round(x["v"], 2)} for k, x in sorted(por_ano.items())},
        "por_categoria": {k: {"n": x["n"], "v": round(x["v"], 2)} for k, x in por_cat.items()},
        "itens": sorted(itens, key=lambda i: i["d"], reverse=True),
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(itens)} emendas, R$ {saida['total']['v']:,.2f}")


if __name__ == "__main__":
    main()
