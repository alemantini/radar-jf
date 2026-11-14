"""Impostômetro: quanto a Prefeitura de Juiz de Fora arrecada.

Fonte oficial: Siconfi (Tesouro Nacional), Relatório Resumido da Execução Orçamentária (RREO),
Anexo 3 (Receita Corrente Líquida), que a Prefeitura envia a cada bimestre. Ele traz, mês a mês,
os últimos 12 meses de IPTU, ISS, ITBI, outros impostos e taxas, transferências e receitas correntes.

Saída: site/dados/prefeitura/receitas.json
"""
import datetime as dt
import json
import sys
import time
from pathlib import Path

import requests

API = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo"
IBGE_JF = 3136702
UA = "RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"
SAIDA = Path(__file__).resolve().parent.parent / "site" / "dados" / "prefeitura" / "receitas.json"

# contas que entram no painel (texto como aparece no RREO)
CONTAS = {
    "IPTU": "IPTU",
    "ISS": "ISS",
    "ITBI": "ITBI",
    "Outros Impostos, Taxas e Contribuições de Melhoria": "Outros impostos e taxas",
    "Impostos, Taxas e Contribuições de Melhoria": "Impostos e taxas municipais",
    "RECEITAS CORRENTES (I)": "Receitas correntes (total)",
    "Transferências Correntes": "Transferências (União e Estado)",
    "Cota-Parte do FPM": "FPM (União)",
    "Cota-Parte do ICMS": "ICMS (Estado)",
    "Cota-Parte do IPVA": "IPVA (Estado)",
}


def consultar(ano, bim):
    params = {"an_exercicio": ano, "nr_periodo": bim, "co_tipo_demonstrativo": "RREO",
              "no_anexo": "RREO-Anexo 03", "id_ente": IBGE_JF}
    for i in range(3):
        try:
            r = requests.get(API, params=params, headers={"User-Agent": UA}, timeout=120)
            if r.status_code == 200:
                return r.json().get("items", [])
            print(f"  HTTP {r.status_code} ({ano}, bimestre {bim})", file=sys.stderr)
        except (requests.RequestException, ValueError) as e:
            print(f"  erro {e}", file=sys.stderr)
        time.sleep(10 * (i + 1))
    return []


def mes_da_coluna(coluna, mes_ref, ano_ref):
    """'<MR-3>' com mês de referência agosto/2026 -> (2026, 5)."""
    c = coluna.strip().upper().replace(" ", "")
    if c == "<MR>":
        k = 0
    elif c.startswith("<MR-") and c.endswith(">") and c[4:-1].isdigit():
        k = -int(c[4:-1])
    else:
        return None
    m = mes_ref + k
    ano = ano_ref
    while m <= 0:
        m += 12
        ano -= 1
    return ano, m


def main():
    hoje = dt.date.today()
    itens, ano_ref, bim_ref = [], None, None
    for ano in (hoje.year, hoje.year - 1):
        for bim in range(6, 0, -1):
            if ano == hoje.year and bim * 2 > hoje.month:
                continue
            itens = consultar(ano, bim)
            time.sleep(1)
            if itens:
                ano_ref, bim_ref = ano, bim
                break
        if itens:
            break
    if not itens:
        print("Siconfi: nenhum RREO encontrado")
        sys.exit(1)
    mes_ref = bim_ref * 2
    print(f"Siconfi: RREO {ano_ref}, bimestre {bim_ref} (dados até {mes_ref:02d}/{ano_ref}), {len(itens)} linhas")

    contas = {}
    populacao = None
    for it in itens:
        populacao = populacao or it.get("populacao")
        nome = (it.get("conta") or "").strip()
        if nome not in CONTAS:
            continue
        c = contas.setdefault(nome, {"nome": CONTAS[nome], "meses": {}, "total_12m": None, "previsao": None})
        col = (it.get("coluna") or "").strip()
        valor = float(it.get("valor") or 0)
        am = mes_da_coluna(col, mes_ref, ano_ref)
        if am:
            c["meses"].setdefault(f"{am[0]}-{am[1]:02d}", valor)
        elif col.upper().startswith("TOTAL") and c["total_12m"] is None:
            c["total_12m"] = valor
        elif col.upper().startswith("PREVIS") and c["previsao"] is None:
            c["previsao"] = valor

    if "IPTU" not in contas or "ISS" not in contas or len(contas["ISS"]["meses"]) < 6:
        print("Siconfi: resposta sem as contas esperadas; não publica")
        sys.exit(1)

    saida = {
        "fonte": "Siconfi, Tesouro Nacional: Relatório Resumido da Execução Orçamentária (RREO), Anexo 3",
        "fonte_url": f"{API}?an_exercicio={ano_ref}&nr_periodo={bim_ref}&co_tipo_demonstrativo=RREO&no_anexo=RREO-Anexo%2003&id_ente={IBGE_JF}",
        "consulta_publica": "https://siconfi.tesouro.gov.br/siconfi/pages/public/consulta_finbra/finbra_list.jsf",
        "ano_ref": ano_ref,
        "bimestre": bim_ref,
        "ultimo_mes": f"{ano_ref}-{mes_ref:02d}",
        "populacao": populacao,
        "coletado_em": dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M"),
        "contas": {k: {**v, "meses": dict(sorted(v["meses"].items()))} for k, v in contas.items()},
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(saida, ensure_ascii=False, indent=1))
    imp = contas.get("Impostos, Taxas e Contribuições de Melhoria", {})
    print(f"OK: impostos e taxas 12 meses R$ {((imp.get('total_12m') or 0) / 1e6):.1f} mi; população {populacao}")


if __name__ == "__main__":
    main()
