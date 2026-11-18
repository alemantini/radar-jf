"""Créditos adicionais: o dinheiro que muda de lugar no orçamento da Prefeitura durante o ano.

A prefeita pode, por decreto, colocar mais dinheiro numa área do orçamento (crédito suplementar,
dentro do limite que a Lei Orçamentária já autoriza, ou crédito extraordinário, em calamidade).
O dinheiro sai de outra área (cancelamento de dotação), do saldo do ano anterior (superávit
financeiro), de arrecadação acima do previsto (excesso de arrecadação) ou de empréstimos.

Fontes:
  - data/cache/atos/ (lista dos atos do Diário Oficial, de prefeitura_atos.py), para achar os decretos;
  - texto completo de cada decreto em https://www.pjf.mg.gov.br/e_atos/e_atos_vis.php?id=N
    (lido uma vez e guardado em data/cache/creditos.json);
  - Siconfi (Tesouro Nacional), RREO Anexo 02: orçamento inicial x atualizado por área (função).

Saída: site/dados/prefeitura/creditos.json
"""
import argparse
import datetime as dt
import html
import json
import re
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
ATOS = RAIZ / "data" / "cache" / "atos"
CACHE = RAIZ / "data" / "cache" / "creditos.json"
SAIDA = RAIZ / "site" / "dados" / "prefeitura" / "creditos.json"
LINK = "https://www.pjf.mg.gov.br/e_atos/e_atos_vis.php?id="
SICONFI = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo"
UA = "RadarJF/1.0 (robo de transparencia, coleta lenta; codigo aberto em https://github.com/alemantini/radar-jf)"
PAUSA = 1.0

FUNCOES = ["Legislativa", "Judiciária", "Essencial à Justiça", "Administração", "Defesa Nacional", "Segurança Pública",
           "Relações Exteriores", "Assistência Social", "Previdência Social", "Saúde", "Trabalho", "Educação", "Cultura",
           "Direitos da Cidadania", "Urbanismo", "Habitação", "Saneamento", "Gestão Ambiental", "Ciência e Tecnologia",
           "Agricultura", "Organização Agrária", "Indústria", "Comércio e Serviços", "Comunicações", "Energia",
           "Transporte", "Desporto e Lazer", "Encargos Especiais"]


def sa(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn").lower()


def num(s):
    return float(s.replace(".", "").replace(",", "."))


def bonito(s):
    s = re.sub(r"\s+", " ", s).strip(" -–")
    pequenas = {"de", "da", "do", "das", "dos", "e", "a", "o", "para", "com", "em"}
    siglas = {"jf", "ctr", "sus", "amac", "emcasa", "demlurb", "funalfa", "procon", "settra", "cesama", "jfprev", "pjf", "ug"}
    out = []
    for i, w in enumerate(s.lower().split()):
        out.append(w.upper() if w.strip("()-/") in siglas else w if (i and w in pequenas) else w[:1].upper() + w[1:])
    return " ".join(out)


# ---------------- leitura de um decreto ----------------
def texto_do_ato(sessao, ato_id):
    r = sessao.get(LINK + str(ato_id), headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    t = r.content.decode("utf-8", "replace")
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t).replace("\xa0", " ")
    t = re.sub(r"\s+", " ", t)
    i = t.find("DECRETO")
    return t[i:] if i >= 0 else t


UG = re.compile(r"((?:[A-ZÀ-Ú][A-ZÀ-Ú0-9ºª/\-\.,()]*\s){1,16}?)R\$\s(.*?)Total da UG\s([\d\.]+,\d{2})")
LINHA = re.compile(r"(\d{2})\.\d{3}\.\d{4}\.\d{4}\s.*?\s([\d\.]+,\d{2})(?=\s|$)")


def blocos(trecho):
    """[(órgão, total, {função: valor})] de um trecho com 'NOME DO ÓRGÃO R$ ... Total da UG x'."""
    out = []
    for m in UG.finditer(trecho):
        nome = re.sub(r"^(?:Art\. \d+º?|.*?Orçamento (?:vigente )?(?:no |do )?Município:)\s*", "", m.group(1).strip())
        nome = re.sub(r"^.*?\b(?:dotação\(ões\)|seguinte\(s\))[^A-ZÀ-Ú]*", "", nome)
        por_funcao = defaultdict(float)
        for l in LINHA.finditer(m.group(2)):
            por_funcao[l.group(1)] += num(l.group(2))
        out.append([bonito(nome), num(m.group(3)), {k: round(v, 2) for k, v in por_funcao.items()}])
    return out


def interpretar(texto):
    t = texto
    m_valor = re.search(r"no valor de R\$\s?([\d\.]+,\d{2})", t)
    tipo = "extraordinario" if re.search(r"(?i)cr[eé]dito extraordin", t[:400]) else \
        "especial" if re.search(r"(?i)cr[eé]dito especial", t[:400]) else "suplementar"
    a1 = re.search(r"Art\. 1", t)
    a2 = re.search(r"Art\. 2", t)
    a3 = re.search(r"Art\. 3", t)
    destino = blocos(t[a1.start():a2.start()]) if a1 and a2 else []
    art2 = t[a2.start():a3.start() if a3 else a2.start() + 6000] if a2 else ""
    s2 = sa(art2)
    fontes = []
    origem = []
    if "cancelamento" in s2 or "anulacao" in s2:
        fontes.append("Cancelamento de outras dotações")
        origem = blocos(art2)
    if "superavit" in s2:
        fontes.append("Saldo do ano anterior (superávit financeiro)")
    if "excesso de arrecadacao" in s2:
        fontes.append("Arrecadação acima do previsto")
    if "operac" in s2 and "credito" in s2:
        fontes.append("Empréstimo (operação de crédito)")
    if not fontes and art2:
        fontes.append("Outra fonte")
    return {"tipo": tipo, "valor": num(m_valor.group(1)) if m_valor else None,
            "para": destino, "de": origem, "fontes": fontes}


# ---------------- coleta ----------------
def decretos_de_credito():
    atos = []
    for f in sorted(ATOS.glob("20*.json")):
        for a in json.loads(f.read_text(encoding="utf-8")).values():
            t = sa(a.get("texto"))
            if a.get("tipo") == "Decreto" and re.search(r"(abre|insere|abertura de) credito (suplementar|especial|extraordinario)", t):
                atos.append(a)
    return sorted(atos, key=lambda a: (a["data"], a["id"]))


def coletar(minutos, amostra=None):
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    lista = decretos_de_credito()
    faltam = [a for a in lista if str(a["id"]) not in cache]
    if amostra:
        faltam = faltam[-amostra:]
    print(f"Créditos: {len(lista)} decretos no Diário Oficial, {len(cache)} já lidos, {len(faltam)} a ler")
    sessao, ini, erros = requests.Session(), time.time(), 0
    for a in faltam:
        if (time.time() - ini) / 60 > minutos:
            print("Créditos: tempo desta rodada acabou; o resto fica para a próxima")
            break
        try:
            texto = texto_do_ato(sessao, a["id"])
        except Exception as e:
            erros += 1
            print("  erro", a["id"], e, file=sys.stderr)
            if erros >= 10:
                break
            time.sleep(10)
            continue
        erros = 0
        d = interpretar(texto)
        d.update({"id": a["id"], "data": a["data"], "num": (re.search(r"DECRETO N[º°o]\s*([\d\.]+)", texto) or [None, ""])[1]})
        if d["valor"] is None:
            d["valor"] = (lambda m: num(m.group(1)) if m else None)(re.search(r"R\$\s?([\d\.]+,\d{2})", a.get("texto") or ""))
        cache[str(a["id"])] = d
        time.sleep(PAUSA)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")
    return cache, lista


# ---------------- orçamento por área (Siconfi) ----------------
def orcamento_por_funcao(ano):
    for bim in range(6, 0, -1):
        try:
            r = requests.get(SICONFI, params={"an_exercicio": ano, "nr_periodo": bim, "co_tipo_demonstrativo": "RREO",
                                              "no_anexo": "RREO-Anexo 02", "id_ente": 3136702},
                             headers={"User-Agent": UA}, timeout=120)
            it = r.json().get("items", []) if r.status_code == 200 else []
        except (requests.RequestException, ValueError):
            it = []
        if it:
            break
        time.sleep(1)
    else:
        return None
    f = {}
    total = {}
    for x in it:
        conta, col = (x.get("conta") or "").strip(), sa(x.get("coluna"))
        if col.startswith("dotacao inicial"):
            k = "ini"
        elif col.startswith("dotacao atualizada"):
            k = "atu"
        else:
            continue
        if conta in FUNCOES:
            f.setdefault(conta, {})[k] = x.get("valor")  # a primeira ocorrência é a do orçamento fiscal
        elif conta.startswith("DESPESAS (EXCETO INTRA") and k not in total:
            total[k] = x.get("valor")
    areas = [{"area": n, "ini": v.get("ini") or 0, "atu": v.get("atu") or 0} for n, v in f.items() if (v.get("ini") or v.get("atu"))]
    areas.sort(key=lambda a: -abs(a["atu"] - a["ini"]))
    return {"ano": ano, "ate_mes": bim * 2, "total": total, "areas": areas}


# ---------------- resumo para o site ----------------
def gerar(cache, lista):
    anos = defaultdict(lambda: {"n": 0, "valor": 0.0, "por_tipo": defaultdict(lambda: [0, 0.0]), "fontes": defaultdict(float),
                                "ganhou": defaultdict(float), "perdeu": defaultdict(float), "meses": defaultdict(float)})
    decretos = []
    for a in lista:
        d = cache.get(str(a["id"]))
        if not d or not d.get("valor"):
            continue
        ano = a["data"][:4]
        A = anos[ano]
        A["n"] += 1
        A["valor"] += d["valor"]
        A["por_tipo"][d["tipo"]][0] += 1
        A["por_tipo"][d["tipo"]][1] += d["valor"]
        A["meses"][a["data"][5:7]] += d["valor"]
        for f in d["fontes"] or ["Não identificada"]:
            A["fontes"][f] += d["valor"] / max(1, len(d["fontes"]))
        for nome, v, _ in d["para"]:
            A["ganhou"][nome] += v
        for nome, v, _ in d["de"]:
            A["perdeu"][nome] += v
        decretos.append({"id": a["id"], "d": a["data"], "num": d.get("num"), "tipo": d["tipo"], "v": round(d["valor"], 2),
                         "para": [[n, round(v, 2)] for n, v, _ in d["para"]][:6], "de": [[n, round(v, 2)] for n, v, _ in d["de"]][:6],
                         "fontes": d["fontes"]})
    saida_anos = {}
    for ano, A in sorted(anos.items()):
        orgaos = set(A["ganhou"]) | set(A["perdeu"])
        saldo = sorted(({"orgao": o, "ganhou": round(A["ganhou"].get(o, 0), 2), "perdeu": round(A["perdeu"].get(o, 0), 2)} for o in orgaos),
                       key=lambda x: -(x["ganhou"] - x["perdeu"]))
        saida_anos[ano] = {"n": A["n"], "valor": round(A["valor"], 2),
                           "por_tipo": {k: [v[0], round(v[1], 2)] for k, v in A["por_tipo"].items()},
                           "fontes": sorted(([k, round(v, 2)] for k, v in A["fontes"].items()), key=lambda x: -x[1]),
                           "meses": [[m, round(v, 2)] for m, v in sorted(A["meses"].items())],
                           "orgaos": saldo}
    hoje = dt.date.today()
    orc = [o for o in (orcamento_por_funcao(hoje.year), orcamento_por_funcao(hoje.year - 1)) if o]
    lidos = sum(1 for a in lista if str(a["id"]) in cache)
    saida = {"atualizado": dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M"),
             "link_ato": LINK, "decretos_total": len(lista), "decretos_lidos": lidos,
             "anos": saida_anos, "orcamento": orc,
             "maiores": sorted(decretos, key=lambda x: -x["v"])[:60],
             "recentes": sorted(decretos, key=lambda x: x["d"], reverse=True)[:30]}
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for ano, A in saida_anos.items():
        print(f"Créditos {ano}: {A['n']} decretos, R$ {A['valor'] / 1e6:.1f} mi; fontes {A['fontes'][:3]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutos", type=float, default=12)
    ap.add_argument("--amostra", type=int)
    args = ap.parse_args()
    cache, lista = coletar(args.minutos, args.amostra)
    gerar(cache, lista)


if __name__ == "__main__":
    main()
