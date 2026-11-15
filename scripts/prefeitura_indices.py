"""Placar fiscal da Prefeitura e comparação com outras cidades mineiras.

Fonte oficial: Siconfi (Tesouro Nacional), que a própria Prefeitura alimenta.
  RGF Anexo 1: despesa com pessoal em relação à receita (limite da Lei de Responsabilidade Fiscal).
  RREO Anexo 14: mínimos constitucionais de educação (25%), saúde (15%) e Fundeb (70%).
  RREO Anexo 2: despesa por função (saúde, educação...), para comparar cidades.
  RREO Anexo 3: receita corrente líquida, IPTU e ISS dos últimos 12 meses.

Saída: site/dados/prefeitura/indices.json
"""
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path

import requests

API = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
UA = {"User-Agent": "RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
JF = 3136702
SAIDA = Path(__file__).resolve().parent.parent / "site" / "dados" / "prefeitura" / "indices.json"

# cidades mineiras de porte parecido (mais de 200 mil habitantes), além de JF
COMPARAR = [3106200, 3170206, 3118601, 3136702, 3143302, 3106705, 3170107, 3154606,
            3127701, 3122306, 3167202, 3131307]
FUNCOES = ["Saúde", "Educação", "Assistência Social", "Segurança Pública", "Urbanismo",
           "Transporte", "Saneamento", "Cultura", "Desporto e Lazer", "Legislativa", "Administração"]


def api(rel, **p):
    for i in range(4):
        try:
            r = requests.get(f"{API}/{rel}", params=p, headers=UA, timeout=180)
            if r.status_code == 200:
                return r.json().get("items", [])
            print(f"  HTTP {r.status_code} {rel} {p}", file=sys.stderr)
        except (requests.RequestException, ValueError) as e:
            print(f"  erro {e}", file=sys.stderr)
        time.sleep(8 * (i + 1))
    return None


def ultimo(rel, anexo, ente, periodos, **extra):
    """Procura o relatório mais recente publicado: devolve (ano, periodo, itens)."""
    hoje = dt.date.today()
    for ano in (hoje.year, hoje.year - 1, hoje.year - 2):
        for per in periodos:
            it = api(rel, an_exercicio=ano, nr_periodo=per, co_tipo_demonstrativo=rel.upper(),
                     no_anexo=anexo, id_ente=ente, **extra)
            if it:
                return ano, per, it
    return None, None, []


def val(itens, conta_re, coluna_re):
    for x in itens:
        if re.search(conta_re, x.get("conta", ""), re.I) and re.search(coluna_re, x.get("coluna", ""), re.I):
            try:
                return float(x["valor"])
            except (TypeError, ValueError):
                pass
    return None


def pessoal():
    ano, q, it = ultimo("rgf", "RGF-Anexo 01", JF, (3, 2, 1), in_periodicidade="Q", co_esfera="M", co_poder="E")
    if not it:
        return None
    return {
        "ano": ano, "quadrimestre": q,
        "rcl": val(it, r"^RECEITA CORRENTE L[IÍ]QUIDA - RCL", r"^Valor$"),
        "despesa": val(it, r"^DESPESA TOTAL COM PESSOAL - DTP \(VI\)", r"^Valor$"),
        "pct": val(it, r"^DESPESA TOTAL COM PESSOAL - DTP \(VI\)", r"% sobre"),
        "limite": val(it, r"^LIMITE M[ÁA]XIMO", r"% sobre"),
        "prudencial": val(it, r"^LIMITE PRUDENCIAL", r"% sobre"),
        "alerta": val(it, r"^LIMITE DE ALERTA", r"% sobre"),
    }


def minimos():
    ano, bim, it = ultimo("rreo", "RREO-Anexo 14", JF, (6, 5, 4, 3, 2, 1))
    if not it:
        return None
    return {
        "ano": ano, "bimestre": bim,
        "educacao": {"aplicado": val(it, r"Manuten[çc][ãa]o e Desenvolvimento do Ensino", r"% Aplicado"),
                     "minimo": val(it, r"Manuten[çc][ãa]o e Desenvolvimento do Ensino", r"% M[íi]nimo")},
        "saude": {"aplicado": val(it, r"Sa[úu]de", r"% Aplicado"),
                  "minimo": val(it, r"Sa[úu]de", r"% M[íi]nimo")},
        "fundeb": {"aplicado": val(it, r"70% do FUNDEB", r"% Aplicado"),
                   "minimo": val(it, r"70% do FUNDEB", r"% M[íi]nimo")},
    }


def balanco():
    """RREO Anexo 1: receita prevista x arrecadada e despesas x receitas correntes no ano (art. 167-A)."""
    ano, bim, it = ultimo("rreo", "RREO-Anexo 01", JF, (6, 5, 4, 3, 2, 1))
    if not it:
        return None
    print("  colunas anexo 1:", sorted({x.get("coluna") for x in it})[:30])
    def v(conta, col):
        for x in it:
            if re.match(conta, x.get("conta", "").strip(), re.I) and re.search(col, x.get("coluna", ""), re.I):
                try:
                    return float(x["valor"])
                except (TypeError, ValueError):
                    pass
        return None
    rc_prev = v(r"^RECEITAS CORRENTES", r"PREVIS[ÃA]O ATUALIZADA")
    rc_real = v(r"^RECEITAS CORRENTES", r"^At[ée] o Bimestre|REALIZADAS.*AT[ÉE] O BIMESTRE|^Até o Bimestre \(c\)")
    dc_liq = v(r"^DESPESAS CORRENTES", r"LIQUIDADAS AT[ÉE] O BIMESTRE")
    dc_emp = v(r"^DESPESAS CORRENTES", r"EMPENHADAS AT[ÉE] O BIMESTRE")
    rt_prev = v(r"^RECEITAS \(EXCETO INTRA|^TOTAL DAS RECEITAS|^SUBTOTAL DAS RECEITAS", r"PREVIS[ÃA]O ATUALIZADA")
    rt_real = v(r"^RECEITAS \(EXCETO INTRA|^TOTAL DAS RECEITAS|^SUBTOTAL DAS RECEITAS", r"^At[ée] o Bimestre|AT[ÉE] O BIMESTRE")
    return {"ano": ano, "bimestre": bim, "rc_previsto_ano": rc_prev, "rc_realizado": rc_real,
            "dc_liquidado": dc_liq, "dc_empenhado": dc_emp, "receita_prevista_ano": rt_prev, "receita_realizada": rt_real}


def por_funcao(itens):
    """Despesa liquidada no ano por função (orçamento fiscal e seguridade, sem as intraorçamentárias)."""
    out = {}
    rotulos = sorted({x.get("rotulo", "") for x in itens})
    principal = [r for r in rotulos if "intra" not in r.lower()] or rotulos
    for x in itens:
        if x.get("rotulo", "") not in principal[:1]:
            continue
        if not x.get("coluna", "").upper().startswith("DESPESAS LIQUIDADAS AT"):
            continue
        c = x.get("conta", "").strip()
        if c in FUNCOES and c not in out:
            out[c] = float(x["valor"] or 0)
    return out


def main():
    entes = {e["cod_ibge"]: e for e in (api("entes") or [])}
    if not entes:
        print("Índices: Siconfi não respondeu")
        sys.exit(1)

    res = {"fonte": "Siconfi, Tesouro Nacional (dados enviados pelas prefeituras)",
           "fonte_url": "https://siconfi.tesouro.gov.br/",
           "coletado_em": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
           "pessoal": pessoal(), "minimos": minimos(), "balanco": balanco(), "cidades": []}
    print("Pessoal:", res["pessoal"])
    print("Mínimos:", res["minimos"])
    print("Balanço:", res["balanco"])

    # ano fechado mais recente com o 6º bimestre de JF publicado
    ano_cmp = None
    for a in (dt.date.today().year - 1, dt.date.today().year - 2):
        if api("rreo", an_exercicio=a, nr_periodo=6, co_tipo_demonstrativo="RREO", no_anexo="RREO-Anexo 02", id_ente=JF):
            ano_cmp = a
            break
    res["ano_comparacao"] = ano_cmp
    if ano_cmp:
        for cod in COMPARAR:
            e = entes.get(cod, {})
            pop = e.get("populacao")
            f = por_funcao(api("rreo", an_exercicio=ano_cmp, nr_periodo=6, co_tipo_demonstrativo="RREO",
                               no_anexo="RREO-Anexo 02", id_ente=cod) or [])
            r3 = api("rreo", an_exercicio=ano_cmp, nr_periodo=6, co_tipo_demonstrativo="RREO",
                     no_anexo="RREO-Anexo 03", id_ente=cod) or []
            tot = lambda conta: val(r3, conta, r"^TOTAL")
            cid = {"cod": cod, "nome": e.get("ente"), "pop": pop, "funcoes": f,
                   "rcl": tot(r"^RECEITA CORRENTE L[IÍ]QUIDA"),
                   "iptu": tot(r"^IPTU$"), "iss": tot(r"^ISS$"),
                   "impostos": tot(r"^Impostos, Taxas e Contribui[çc][õo]es de Melhoria$")}
            print(" ", cid["nome"], pop, len(f), "funções", cid["rcl"])
            if f and pop:
                res["cidades"].append(cid)

    ok = res["pessoal"] or res["minimos"] or len(res["cidades"]) >= 5
    if not ok:
        print("Índices: nada utilizável")
        sys.exit(1)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Índices gravados: {len(res['cidades'])} cidades")


if __name__ == "__main__":
    main()
