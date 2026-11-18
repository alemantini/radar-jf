"""Três assuntos quentes da Prefeitura, em páginas próprias:

  chuvas.json      o dinheiro da calamidade das chuvas e das obras de encostas e drenagem
  emprestimos.json empréstimos: o que foi autorizado, o que entrou e quanto custa (juros e amortização)
  hospitais.json   quanto a Prefeitura comprometeu e pagou a cada hospital

Fontes (todas oficiais e já usadas pelo Radar):
  - site/dados/prefeitura/empenhos_AAAA.json, gerado por prefeitura_despesas.py
    (arquivos de despesas do Portal da Transparência da PJF);
  - data/cache/atos/ (Diário Oficial, "Atos do Governo"), gerado por prefeitura_atos.py;
  - Siconfi (Tesouro Nacional): RREO Anexo 01 e RGF Anexos 02 e 04.

Cuidado com a leitura: "empenhado" é o valor reservado no orçamento para a despesa; "pago" é o que
já saiu do caixa. A diferença inclui serviços que ainda vão ser prestados e não significa atraso
por si só. Pagamentos a pessoas físicas entram só somados, sem nome.
"""
import datetime as dt
import glob
import json
import re
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "site" / "dados" / "prefeitura"
ATOS = RAIZ / "data" / "cache" / "atos"
LINK_ATO = "https://www.pjf.mg.gov.br/e_atos/e_atos_vis.php?id="
SICONFI = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/"
IBGE_JF = 3136702
UA = "RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"
FONTE_DESPESAS = "https://www.pjf.mg.gov.br/transparencia/dados_abertos/arquivos.php"


def sa(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn").lower()


def r2(x):
    return round(x, 2)


# ---------------- dados de base ----------------
def carregar_empenhos():
    """Lista de empenhos de todos os anos publicados, já com nomes por extenso."""
    saida = []
    for f in sorted(DADOS.glob("empenhos_*.json")):
        B = json.loads(f.read_text(encoding="utf-8"))
        S, E, C = B["secretarias"], B["elementos"], B["credores"]
        campos = B["campos"]
        il = campos.index("liquidado") if "liquidado" in campos else None
        for x in B["empenhos"]:
            pj = x[2] >= 0
            saida.append({
                "d": x[0], "sec": S[x[1]], "cnpj": C[x[2]][0] if pj else "", "cred": C[x[2]][1] if pj else "",
                "pj": pj, "el": E[x[3]], "e": x[4], "p": x[5], "l": x[il] if il is not None and il < len(x) else None,
                "h": x[6] or "", "n": x[7] if len(x) > 7 else "",
            })
    return saida


def carregar_atos():
    atos = []
    for f in sorted(ATOS.glob("20*.json")):
        atos += list(json.loads(f.read_text(encoding="utf-8")).values())
    return atos


def valor_no_texto(t):
    m = re.search(r"R\$\s*([\d\.]+,\d{2})", t or "")
    return float(m.group(1).replace(".", "").replace(",", ".")) if m else None


def ato_curto(a):
    t = re.sub(r"\s+", " ", a.get("texto") or "").strip()
    corte = re.search(r"\. A PREFEITA DE JUIZ DE FORA|\. A Câmara Municipal de Juiz de Fora aprova", t)
    if corte:
        t = t[:corte.start() + 1]
    return {"id": a["id"], "d": a["data"], "tipo": a["tipo"], "x": t[:300], "v": valor_no_texto(t)}


# ---------------- chuvas ----------------
RESPOSTA = re.compile(r"calamidad|chuvas?\b|enchente|desabrig|desaloj|deslizament|ajuda humanitaria|"
                      r"17\.?693|17\.?59[38]|fumecap|acolhimento temporario|aluguel social|auxilio.moradia|"
                      r"(?:familias|pessoas|imoveis|moradores) atingid|atingid[oa]s pel")
ENCOSTAS = re.compile(r"encosta|macrodrenag|drenagem|corrego|contencao|contencoes|estabilizacao")
FUNDO_CALAMIDADE = re.compile(r"calamidade")
INICIO_CHUVAS = "2025-12-01"  # situação de emergência (dez/2025) e calamidade (fev/2026)


def forma_contratacao(h):
    t = sa(h)
    if re.search(r"emergencia|dispensa", t):
        return "Contratação emergencial ou dispensa"
    if re.search(r"inexigib|credenciament", t):
        return "Inexigibilidade ou credenciamento"
    if re.search(r"concorrencia|pregao|licitac|tomada de preco|ata de registro", t):
        return "Licitação"
    return "Não informado no histórico"


def gerar_chuvas(empenhos, atos):
    cats = {"Resposta à calamidade": defaultdict(float), "Obras de encostas e drenagem": defaultdict(float)}
    meses = defaultdict(lambda: {"e": 0.0, "p": 0.0})
    forn = defaultdict(lambda: {"e": 0.0, "p": 0.0, "n": 0, "cats": set(), "nome": ""})
    forma = defaultdict(lambda: {"e": 0.0, "n": 0})
    por_sec = defaultdict(lambda: {"e": 0.0, "p": 0.0, "n": 0})
    pf = {"e": 0.0, "p": 0.0, "n": 0}
    itens = {}
    for x in empenhos:
        if x["d"] < INICIO_CHUVAS:
            continue
        h = sa(x["h"] + " " + x["el"])
        if FUNDO_CALAMIDADE.search(sa(x["sec"])) or RESPOSTA.search(h):
            cat = "Resposta à calamidade"
        elif ENCOSTAS.search(h) and re.search(r"obras|desenvolvi|urbano", sa(x["sec"])):
            cat = "Obras de encostas e drenagem"
        else:
            continue
        c = cats[cat]
        c["e"] += x["e"]; c["p"] += x["p"]; c["n"] += 1
        m = meses[x["d"][:7]]
        m["e"] += x["e"]; m["p"] += x["p"]
        ps = por_sec[x["sec"]]
        ps["e"] += x["e"]; ps["p"] += x["p"]; ps["n"] += 1
        if not x["pj"]:
            pf["e"] += x["e"]; pf["p"] += x["p"]; pf["n"] += 1
            continue
        f = forn[x["cnpj"]]
        f["e"] += x["e"]; f["p"] += x["p"]; f["n"] += 1; f["cats"].add(cat); f["nome"] = x["cred"]
        fm = forma[forma_contratacao(x["h"])]
        fm["e"] += x["e"]; fm["n"] += 1
        # anulações aparecem como linhas negativas do mesmo empenho: soma por empenho
        chave = (x["cnpj"], x["n"] or (x["d"], x["h"]))
        it = itens.setdefault(chave, {"d": x["d"], "cred": x["cred"], "cnpj": x["cnpj"], "sec": x["sec"], "cat": cat,
                                      "e": 0.0, "p": 0.0, "h": x["h"], "num": x["n"]})
        it["e"] += x["e"]; it["p"] += x["p"]
        if x["e"] > 0 and (x["d"] < it["d"] or not it["h"]):
            it["d"], it["h"] = x["d"], x["h"] or it["h"]
    # atos: decretos de emergência e calamidade, comitê, isenções e créditos extraordinários
    marcos, creditos = [], []
    for a in atos:
        t = sa(a.get("texto"))
        if a["data"] < "2025-12-01":
            continue
        if "credito extraordinario" in t:
            creditos.append(ato_curto(a))
        elif a["tipo"] in ("Decreto", "Lei") and re.search(r"calamidade|situacao de emergencia|chuvas|enchentes|luto oficial", t):
            marcos.append(ato_curto(a))
    tot_cred = sum(c["v"] or 0 for c in creditos)
    saida = {
        "desde": INICIO_CHUVAS,
        "categorias": [{"nome": k, "e": r2(v["e"]), "p": r2(v["p"]), "n": int(v["n"])} for k, v in cats.items()],
        "meses": [{"m": k, "e": r2(v["e"]), "p": r2(v["p"])} for k, v in sorted(meses.items())],
        "fornecedores": sorted(({"cnpj": k, "nome": v["nome"], "e": r2(v["e"]), "p": r2(v["p"]), "n": v["n"],
                                 "cats": sorted(v["cats"])} for k, v in forn.items()), key=lambda f: -f["e"])[:40],
        "n_fornecedores": len(forn),
        "secretarias": sorted(({"nome": k, "e": r2(v["e"]), "p": r2(v["p"]), "n": v["n"]} for k, v in por_sec.items() if v["e"] > 0.5),
                              key=lambda f: -f["e"]),
        "forma": sorted(({"nome": k, "e": r2(v["e"]), "n": v["n"]} for k, v in forma.items()), key=lambda f: -f["e"]),
        "pessoas_fisicas": {k: r2(v) if k != "n" else v for k, v in pf.items()},
        "itens": sorted(({**i, "e": r2(i["e"]), "p": r2(i["p"])} for i in itens.values() if i["e"] > 0.5),
                        key=lambda i: -i["e"])[:80],
        "marcos": sorted(marcos, key=lambda a: a["d"]),
        "creditos_extraordinarios": {"total": r2(tot_cred), "n": len(creditos), "atos": sorted(creditos, key=lambda a: a["d"])},
    }
    tot = sum(c["e"] for c in saida["categorias"])
    print(f"Chuvas: R$ {tot / 1e6:.1f} mi empenhados em {sum(c['n'] for c in saida['categorias'])} empenhos, "
          f"{len(forn)} empresas, {len(marcos)} decretos, {len(creditos)} créditos extraordinários (R$ {tot_cred / 1e6:.1f} mi)")
    return saida


# ---------------- empréstimos ----------------
def siconfi(recurso, params):
    for i in range(3):
        try:
            r = requests.get(SICONFI + recurso, params={**params, "id_ente": IBGE_JF}, headers={"User-Agent": UA}, timeout=120)
            if r.status_code == 200:
                return r.json().get("items", [])
        except (requests.RequestException, ValueError) as e:
            print("  Siconfi:", e, file=sys.stderr)
        time.sleep(5 * (i + 1))
    return None


def ultimo_rreo(ano):
    for bim in range(6, 0, -1):
        it = siconfi("rreo", {"an_exercicio": ano, "nr_periodo": bim, "co_tipo_demonstrativo": "RREO", "no_anexo": "RREO-Anexo 01"})
        if it:
            return bim, it
        time.sleep(1)
    return None, []


def ultimo_rgf(ano, anexo):
    for q in (3, 2, 1):
        it = siconfi("rgf", {"an_exercicio": ano, "in_periodicidade": "Q", "nr_periodo": q, "co_tipo_demonstrativo": "RGF",
                             "no_anexo": anexo, "co_esfera": "M", "co_poder": "E"})
        if it:
            return q, it
        time.sleep(1)
    return None, []


def gerar_emprestimos(empenhos, atos):
    hoje = dt.date.today()
    anos = [hoje.year - 1, hoje.year]
    entradas = []
    for ano in anos:
        bim, it = ultimo_rreo(ano)
        linha = {}
        for x in it:
            if (x.get("conta") or "").strip().upper() == "OPERAÇÕES DE CRÉDITO":
                col = sa(x.get("coluna"))
                if col.startswith("previsao atualizada"):
                    linha["previsto"] = x.get("valor")
                elif col.startswith("previsao inicial"):
                    linha["previsto_inicial"] = x.get("valor")
                elif col.startswith("ate o bimestre"):
                    linha["recebido"] = x.get("valor")
        if linha:
            entradas.append({"ano": ano, "ate_mes": bim * 2, **linha})
    limite = {}
    q, it = ultimo_rgf(hoje.year, "RGF-Anexo 04")
    if not it:
        q, it = ultimo_rgf(hoje.year - 1, "RGF-Anexo 04")
        ano_rgf = hoje.year - 1
    else:
        ano_rgf = hoje.year
    for x in it or []:
        conta, col, v = sa(x.get("conta")), sa(x.get("coluna")), x.get("valor")
        if conta.startswith("total considerado") and "%" in col:
            limite["pct"] = v
        elif conta.startswith("total considerado"):
            limite["valor"] = v
        elif conta.startswith("limite geral") and "%" in col:
            limite["limite_pct"] = v
        elif conta.startswith("limite geral"):
            limite["limite_valor"] = v
        elif conta.startswith("receita corrente liquida - rcl"):
            limite["rcl"] = v
    if limite:
        limite.update({"ano": ano_rgf, "quadrimestre": q})
    divida = {}
    q2, it = ultimo_rgf(hoje.year, "RGF-Anexo 02")
    ano_dc = hoje.year
    if not it:
        q2, it = ultimo_rgf(hoje.year - 1, "RGF-Anexo 02")
        ano_dc = hoje.year - 1
    for x in it or []:
        conta, col, v = sa(x.get("conta")), sa(x.get("coluna")), x.get("valor")
        if not col.startswith("ate o") or v is None:
            continue
        chave = "dc" if conta.startswith("divida consolidada - dc") else "dcl" if conta.startswith("divida consolidada liquida (dcl)") else \
            "dcl_pct" if "% da dcl sobre a rcl" in conta else None
        if chave:
            divida[chave] = v  # a última coluna "Até o Nº quadrimestre" fica
    if divida:
        divida.update({"ano": ano_dc, "quadrimestre": q2})
    # o que a Prefeitura paga pelos empréstimos (empenhos de juros e de amortização)
    servico = defaultdict(lambda: defaultdict(lambda: {"e": 0.0, "p": 0.0}))
    for x in empenhos:
        el = sa(x["el"])
        tipo = "juros" if "juros" in el and "divida" in el else "amortizacao" if ("principal da divida" in el or "amortiza" in el) else None
        if not tipo:
            continue
        credor = x["cred"] or "Outros"
        s = servico[x["d"][:4]][(credor, tipo)]
        s["e"] += x["e"]; s["p"] += x["p"]
    servico_saida = {}
    for ano, d in servico.items():
        credores = defaultdict(lambda: {"juros_e": 0.0, "juros_p": 0.0, "amort_e": 0.0, "amort_p": 0.0})
        for (c, tipo), v in d.items():
            k = "juros" if tipo == "juros" else "amort"
            credores[c][k + "_e"] += v["e"]; credores[c][k + "_p"] += v["p"]
        servico_saida[ano] = sorted(({"credor": c, **{k: r2(v) for k, v in vals.items()}} for c, vals in credores.items()),
                                    key=lambda r: -(r["juros_e"] + r["amort_e"]))
    leis, contratos = [], []
    for a in atos:
        t = sa(a.get("texto"))
        if re.search(r"cofinanciamento|consignacao|consignado|cartao de credito", t):
            continue
        if a["tipo"] in ("Lei", "Decreto") and re.search(r"operac(ao|oes) de credito", t):
            leis.append(ato_curto(a))
        elif a["tipo"] == "Extrato de Contrato" and re.search(r"objeto: emprestimo|financiamento concedido|operacao de credito", t):
            contratos.append(ato_curto(a))
    saida = {"entradas": entradas, "limite": limite, "divida": divida, "servico": servico_saida,
             "leis": sorted(leis, key=lambda a: a["d"]), "contratos": sorted(contratos, key=lambda a: a["d"])}
    print(f"Empréstimos: {len(entradas)} anos no RREO, limite {limite.get('pct')}% da RCL, {len(leis)} leis/decretos, "
          f"{len(contratos)} contratos, serviço da dívida em {list(servico_saida)}")
    return saida


# ---------------- hospitais ----------------
HOSPITAL = re.compile(r"\bhospital\b|santa casa|maternidade|ascomcer|casa de saude|instituto oncologico|instituto de clinica|"
                      r"\bhps\b|pronto.socorro|fundacao instituto mineiro|hu.ufjf|ebserh")
NAO_HOSPITAL = re.compile(r"hospitalar|comercio|comercial|distribuid|medicamentos|farma|equipamentos|confec|sistemas?\b")


def gerar_hospitais(empenhos, atos):
    por = defaultdict(lambda: defaultdict(lambda: {"e": 0.0, "p": 0.0, "l": 0.0, "tem_l": False, "n": 0,
                                                    "meses": defaultdict(lambda: [0.0, 0.0])}))
    nomes = {}
    for x in empenhos:
        if not x["pj"]:
            continue
        nome = sa(x["cred"])
        if not HOSPITAL.search(nome) or NAO_HOSPITAL.search(nome) or "saude" not in sa(x["sec"]) and "assistencia a saude" not in sa(x["sec"]):
            continue
        nomes[x["cnpj"]] = x["cred"]
        H = por[x["d"][:4]][x["cnpj"]]
        H["e"] += x["e"]; H["p"] += x["p"]; H["n"] += 1
        if x["l"] is not None:
            H["l"] += x["l"]; H["tem_l"] = True
        mm = H["meses"][x["d"][5:7]]
        mm[0] += x["e"]; mm[1] += x["p"]
    anos = {}
    for ano, d in por.items():
        lista = []
        for cnpj, H in d.items():
            lista.append({"cnpj": cnpj, "nome": nomes[cnpj], "e": r2(H["e"]), "p": r2(H["p"]), "n": H["n"],
                          "l": r2(H["l"]) if H["tem_l"] else None,
                          "meses": [[m, r2(v[0]), r2(v[1])] for m, v in sorted(H["meses"].items())]})
        lista.sort(key=lambda h: -h["e"])
        anos[ano] = lista
    convenios = [ato_curto(a) for a in atos if a["tipo"] in ("Extrato de Convênio", "Extrato de Contrato", "Extrato de Termo de Acordo")
                 and HOSPITAL.search(sa(a.get("texto"))) and not NAO_HOSPITAL.search(sa(a.get("texto"))[:400]) and a["data"] >= "2025-07-01"]
    saida = {"anos": anos, "convenios": sorted(convenios, key=lambda a: a["d"], reverse=True)[:40]}
    for ano, l in sorted(anos.items()):
        print(f"Hospitais {ano}: {len(l)} hospitais, R$ {sum(h['e'] for h in l) / 1e6:.1f} mi empenhados, R$ {sum(h['p'] for h in l) / 1e6:.1f} mi pagos")
    return saida


def main():
    empenhos = carregar_empenhos()
    if not empenhos:
        print("Temas: sem empenhos da Prefeitura; nada a fazer")
        sys.exit(1)
    atos = carregar_atos()
    agora = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M")
    ultimo = max(x["d"] for x in empenhos if x["d"])
    base = {"atualizado": agora, "dados_ate": ultimo, "fonte_despesas": FONTE_DESPESAS, "link_ato": LINK_ATO}
    for nome, func in (("chuvas", gerar_chuvas), ("emprestimos", gerar_emprestimos), ("hospitais", gerar_hospitais)):
        dados = func(empenhos, atos)
        (DADOS / f"{nome}.json").write_text(json.dumps({**base, **dados}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("OK temas da Prefeitura")


if __name__ == "__main__":
    main()
