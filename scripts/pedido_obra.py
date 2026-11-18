"""Pedido x obra: os pedidos dos vereadores para cada rua e os gastos de obra da Prefeitura na mesma rua.

Junta duas fontes oficiais que o Radar já tem:
  - site/dados/propostas.json: pedidos (indicações e requerimentos) dos vereadores, com a rua
    encontrada no texto (gerado por processar.py a partir do sistema da Câmara);
  - site/dados/prefeitura/empenhos_AAAA.json: gastos da Prefeitura (Portal da Transparência),
    onde o texto do empenho às vezes cita a rua da obra ou do serviço.

O que a página pode dizer: "achamos um gasto de obra da Prefeitura que cita esta rua".
O que ela NÃO pode dizer: que o pedido não foi atendido quando não achamos nada. Muita obra é
feita por contratos grandes que não citam a rua no empenho (tapa-buraco, capina, iluminação),
e o arquivo da Prefeitura só traz os anos publicados. Por isso a página fala em "gasto encontrado".

Saída: site/dados/pedido_obra.json
"""
import datetime as dt
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "site" / "dados"
SAIDA = DADOS / "pedido_obra.json"

OBRA_ELEMENTO = re.compile(r"obras e instalac|servicos de engenharia|manutencao e conservacao de (bens imoveis|vias)")
OBRA_TEXTO = re.compile(r"\bobras?\b|paviment|asfalt|recapeament|drenagem|contencao|calcament|meio.fio|sarjeta|iluminacao publica|"
                        r"reforma|tapa.buraco|operacao tapa|capina|rede pluvial|galeria|bueiro|boca de lobo|muro de arrimo|"
                        r"encosta|escada(ria)?|passeio|calcada|ponte|pontilhao|canaliza|corrego|terraplan")
RUA_TEXTO = re.compile(
    r"\b(rua|r\.|avenida|av\.|travessa|tv\.|praca|estrada|alameda|rodovia|beco|largo|ladeira|viela)\s+"
    r"((?:[a-z]{1,4}\.|[a-z0-9º°ª'\-]+)(?:\s(?:[a-z]{1,4}\.|[a-z0-9º°ª'\-]+)){0,6}?)"
    r"(?=\s*(?:,|;|\.(?:\s|$)|\(|$|\s-\s|\s+n[º°o]?\.?\s*\d|\s+\d|\s+(?:no|na|nos|nas|bairro|esquina|entre|proxim|em frente|"
    r"ate|e rua|e avenida|e travessa|altura|trecho|localizad|situad|sentido|regiao|loteamento|vila|conforme|para|com|referente)\b))")
BAIRRO_TEXTO = re.compile(r"\bbairros?\s+([a-z0-9º°ª'\-]+(?:\s[a-z0-9º°ª'\-]+){0,3}?)(?=\s*(?:,|;|\.|\(|$|\s-\s|\s+(?:em|na|no|e|regiao|zona|juiz|conforme|para|com)\b))")
TIPOS = {"r.": "rua", "av.": "avenida", "tv.": "travessa"}
ABREV = {"dr": "doutor", "dra": "doutora", "prof": "professor", "profa": "professora", "cel": "coronel", "gal": "general",
         "sta": "santa", "sto": "santo", "pe": "padre", "eng": "engenheiro", "des": "desembargador", "mal": "marechal",
         "presidente": "presidente", "pres": "presidente", "av": "avenida", "sen": "senador", "dep": "deputado", "ten": "tenente", "cap": "capitao", "maj": "major"}
VAZIAS = {"de", "da", "do", "das", "dos", "e"}


def sa(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn").lower()


def chave_rua(tipo, nome):
    tipo = TIPOS.get(tipo, tipo)
    pal = [ABREV.get(p.strip(".'"), p.strip(".'")) for p in sa(nome).replace("-", " ").split()]
    pal = [p for p in pal if p and p not in VAZIAS]
    if not pal or len("".join(pal)) < 4:
        return None
    return tipo + ":" + " ".join(pal)


def chave_bairro(b):
    pal = [p for p in re.sub(r"[^a-z0-9 ]", " ", sa(b)).split() if p not in VAZIAS]
    return " ".join(pal)


def ruas_no_texto(texto):
    t = re.sub(r"\s+", " ", sa(texto))
    achadas = []
    for m in RUA_TEXTO.finditer(t):
        k = chave_rua(m.group(1), m.group(2))
        if k:
            achadas.append(k)
    b = BAIRRO_TEXTO.search(t)
    return achadas, chave_bairro(b.group(1)) if b else ""


def ler(rel):
    try:
        return json.loads((DADOS / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def main():
    props = ler("propostas.json") or []
    pedidos = defaultdict(list)
    for p in props:
        if p.get("g") != "pedidos" or not p.get("r"):
            continue
        tipo, _, nome = p["r"].partition(" ")
        k = chave_rua(sa(tipo), nome)
        if k:
            pedidos[k].append(p)
    print(f"Pedido x obra: {sum(len(v) for v in pedidos.values())} pedidos com rua, {len(pedidos)} ruas")

    gastos = defaultdict(list)
    anos = []
    for f in sorted((DADOS / "prefeitura").glob("empenhos_*.json")):
        B = json.loads(f.read_text(encoding="utf-8"))
        anos.append(B.get("ano"))
        S, E, C = B["secretarias"], B["elementos"], B["credores"]
        for x in B["empenhos"]:
            if x[2] < 0 or not x[6]:
                continue
            h = sa(x[6])
            if not (OBRA_ELEMENTO.search(sa(E[x[3]])) or OBRA_TEXTO.search(h)):
                continue
            ruas, bairro = ruas_no_texto(x[6])
            for k in set(ruas):
                if k in pedidos:
                    gastos[k].append({"d": x[0], "sec": S[x[1]], "cnpj": C[x[2]][0], "cred": C[x[2]][1],
                                      "e": x[4], "p": x[5], "h": x[6], "num": x[7] if len(x) > 7 else "", "_b": bairro})

    ruas = []
    for k, ps in pedidos.items():
        bairros_ped = Counter(chave_bairro(p["b"]) for p in ps if p.get("b"))
        nome_b = Counter(p["b"] for p in ps if p.get("b"))
        gs = []
        for g in gastos.get(k, []):
            # mesma rua em bairros diferentes: só junta quando os bairros não se contradizem
            if g["_b"] and bairros_ped and g["_b"] not in bairros_ped:
                continue
            gs.append({kk: v for kk, v in g.items() if kk != "_b"})
        # soma por empenho (anulações aparecem como linhas negativas do mesmo empenho)
        por_emp = {}
        for g in gs:
            c = por_emp.setdefault((g["cnpj"], g["num"] or g["d"] + g["h"]), {**g, "e": 0.0, "p": 0.0})
            c["e"] += g["e"]; c["p"] += g["p"]
        gs = sorted((g for g in por_emp.values() if g["e"] > 0.5), key=lambda g: g["d"])
        datas = sorted(p["d"] for p in ps if p.get("d"))
        autores = Counter(a for p in ps for a in p.get("au", []))
        ruas.append({
            "r": Counter(p["r"] for p in ps).most_common(1)[0][0],
            "b": nome_b.most_common(1)[0][0] if nome_b else "",
            "q": len(ps),
            "temas": [t for t, _ in Counter(p.get("tm") for p in ps if p.get("tm")).most_common(3)],
            "au": [a for a, _ in autores.most_common(6)],
            "d1": datas[0] if datas else "", "d2": datas[-1] if datas else "",
            "ped": [{"i": p["i"], "t": p["t"], "n": p["n"], "a": p["a"], "d": p.get("d", ""), "e": p["e"][:220]}
                    for p in sorted(ps, key=lambda p: p.get("d") or "", reverse=True)[:8]],
            "g": [{**g, "e": round(g["e"], 2), "p": round(g["p"], 2), "h": g["h"][:260]} for g in gs[-10:]],
            "ge": round(sum(g["e"] for g in gs), 2),
            "gp": round(sum(g["p"] for g in gs), 2),
            "ng": len(gs),
            "depois": sum(1 for g in gs if datas and g["d"] >= datas[0]),
        })
    com = [r for r in ruas if r["ng"]]
    sem = sorted((r for r in ruas if not r["ng"] and r["q"] >= 3), key=lambda r: -r["q"])[:60]
    saida = {
        "atualizado": dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M"),
        "anos_gastos": [a for a in anos if a],
        "ruas_com_pedido": len(ruas), "pedidos_com_rua": sum(r["q"] for r in ruas),
        "ruas_com_gasto": len(com),
        "com_gasto": sorted(com, key=lambda r: (-r["q"], -r["ge"])),
        "sem_gasto": [{k: v for k, v in r.items() if k not in ("g",)} for r in sem],
        "fonte_ped": "https://www.camarajf.mg.gov.br/sal/",
        "fonte_gastos": "https://www.pjf.mg.gov.br/transparencia/dados_abertos/arquivos.php",
    }
    SAIDA.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Pedido x obra: {len(com)} ruas com pedido e com gasto de obra encontrado; {len(sem)} ruas muito pedidas sem gasto encontrado")


if __name__ == "__main__":
    main()
