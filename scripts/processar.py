"""Transforma os dados brutos em arquivos prontos para o site.

Regras de classificação (as mesmas para todos os vereadores) ficam em REGRAS,
e o texto delas é publicado no próprio site.
"""
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BRUTO = RAIZ / "data" / "bruto"
CACHE = RAIZ / "data" / "cache"
SAIDA = RAIZ / "site" / "dados"

GRUPOS = {
    "pedidos": "Pedidos de melhoria nos bairros",
    "cobrancas": "Perguntas e cobranças",
    "homenagens": "Homenagens",
    "leis": "Propostas de lei",
    "outros": "Outros",
}

REGRAS = [
    "Pedidos de melhoria nos bairros: requerimentos e indicações que pedem um serviço ou uma obra "
    "(iluminação, capina, buraco, poda, sinalização etc.). Em Juiz de Fora esses pedidos são feitos como requerimento.",
    "Perguntas e cobranças: pedidos de informação, representações e requerimentos que pedem informações, "
    "esclarecimentos, convocação de autoridades ou audiência pública.",
    "Homenagens: votos de congratulação, aplauso ou pesar, moções de homenagem, título de cidadão, "
    "nome de rua ou praça, datas comemorativas, medalhas e sessões solenes.",
    "Propostas de lei: projetos de lei, de lei complementar, de emenda à Lei Orgânica, de resolução e de "
    "decreto legislativo que não sejam homenagem nem declaração de utilidade pública.",
    "Outros: declarações de utilidade pública, moções que não são homenagem (apoio, repúdio, apelo) e "
    "pedidos de procedimento interno (urgência, retirada, licença, desarquivamento).",
    "A classificação é feita automaticamente pelas palavras do texto oficial (ementa). Pode haver erro "
    "pontual; cada proposta tem link para o documento oficial.",
]

RE_HOMENAGEM = re.compile(
    r"congratula|aplauso|louvor|pesar|parab[eé]n|homenag|felicita|men[cç][aã]o honrosa|"
    r"cidad[aã]o honor|t[ií]tulo de cidad|cidadania honor|denomina|logradouro|"
    r"dia municipal|semana municipal|m[eê]s municipal|calend[aá]rio|comenda|medalha|"
    r"diploma|sess[aã]o solene|reuni[aã]o solene|voto de reconhecimento|condol[eê]ncia|falecimento",
    re.I)
RE_UTILIDADE = re.compile(r"utilidade p[uú]blica", re.I)
RE_COBRANCA = re.compile(
    r"informa[cç]|esclarec|convoca|convite|convida|audi[eê]ncia p[uú]blica|"
    r"comparecimento|presta[cç][aã]o de contas|explica[cç]", re.I)
RE_INTERNO = re.compile(
    r"urg[eê]ncia|retirada|desarquiv|licen[cç]a do vereador|licen[cç]a para|prorroga[cç][aã]o de prazo|"
    r"regime de urg|inclus[aã]o em pauta|adiamento|vista do processo|tramita[cç][aã]o conjunta", re.I)

TEMAS = [
    ("Iluminação", r"ilumina|l[aâ]mpada|luminária|poste|refletor|led\b"),
    ("Buraco e asfalto", r"buraco|asfalt|tapa.?buraco|pavimenta|recapeamento|calçamento|cal[cç]amento|bloquete|meio.?fio|sarjeta"),
    ("Capina e limpeza", r"capina|ro[cç]ada|limpeza|varri[cç][aã]o|entulho|terreno baldio|mato"),
    ("Lixo e coleta", r"\blixo|coleta|lixeira|ca[cç]amba|res[ií]duo|contêiner|conteiner"),
    ("Poda e árvores", r"poda|[aá]rvore|galho|supress[aã]o arb|plantio de mud"),
    ("Esgoto e drenagem", r"esgoto|bueiro|boca de lobo|drenagem|galeria pluvial|manilha|[aá]gua pluvial|alagamento|c[oó]rrego|canaliza"),
    ("Água", r"cesama|falta d.?[aá]gua|abastecimento de [aá]gua|vazamento|hidr[oô]metro|rede de [aá]gua"),
    ("Trânsito e sinalização", r"sinaliza|quebra.?mola|redutor de velocidade|lombada|faixa de pedestre|sem[aá]foro|placa|tr[aâ]nsito|estacionamento"),
    ("Ônibus e transporte", r"[oô]nibus|linha |abrigo|ponto de [oô]nibus|transporte coletivo|itiner[aá]rio"),
    ("Praças e lazer", r"pra[cç]a|parquinho|academia|quadra|campo de futebol|playground|brinquedo"),
    ("Saúde", r"\bubs\b|unidade b[aá]sica|posto de sa[uú]de|sa[uú]de"),
    ("Escolas e creches", r"escola|creche|\bcmei\b|educa[cç]"),
    ("Animais", r"animal|animais|cachorro|c[aã]es|gato|zoonose|castra[cç]"),
]
TEMAS = [(t, re.compile(rx, re.I)) for t, rx in TEMAS]

RE_RUA = re.compile(
    r"\b(Rua|R\.|Avenida|Av\.|Travessa|Tv\.|Pra[cç]a|Estrada|Alameda|Rodovia|Beco|Largo|Viela|Ladeira|Servid[aã]o)"
    r"\s+((?:[A-ZÀ-Ýa-zà-ÿ0-9º°ª'\.\-]+\s?){1,7}?)"
    r"(?=\s*(?:,|;|\.\s|\.$|\(|$|\s+n[º°o]?\.?\s*\d|\s+\d|\s+-\s|\s+(?:esquina|pr[oó]xim|em frente|entre|altura|nas?\b|nos?\b|at[eé]|com\b|e\s+(?:Rua|Avenida|Travessa)|Bairro|bairro|loteamento|Loteamento|Vila\b)))")
RE_BAIRRO = re.compile(
    r"\b[Bb]airros?\s+((?:[A-ZÀ-Ýa-zà-ÿ0-9º°ª'\-]+\s?){1,5}?)"
    r"(?=\s*(?:,|;|\.\s|\.$|\(|$|\s+-\s|\s+(?:em\b|na\b|no\b|nas\b|nos\b|e\s+[Bb]airro|regi[aã]o|zona|pr[oó]xim|Juiz)))")

# Salário (subsídio) dos vereadores, fixado pelo Projeto de Lei 133/2024 (substitutivo aprovado em 28/06/2024)
SUBSIDIO = {
    "vereadores": 23,
    "por_ano": {"2025": 18595.70, "2026": 19757.94, "2027": 20992.81, "2028": 22304.86},
    "decimo_terceiro": True,
    "fonte": "https://www.camarajf.mg.gov.br/sal/mostrapfs.php?n=140483",
    "fonte_nome": "Projeto de Lei 133/2024 (substitutivo aprovado em 28/06/2024)",
}

PREPOSICOES = {"de", "da", "do", "das", "dos", "e"}


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def chave(s):
    return re.sub(r"[^a-z0-9]", "", sem_acento(s.lower()))


def titulo(s):
    pal = s.strip(" .-").split()
    return " ".join(p.lower() if p.lower() in PREPOSICOES and i else p[:1].upper() + p[1:] for i, p in enumerate(pal))


def classificar(p):
    t, e = p["tipo"], p["ementa"]
    if t in ("PLEI", "PLEIC", "PELOR", "PRES", "PDL"):
        if RE_UTILIDADE.search(e):
            return "outros"
        if RE_HOMENAGEM.search(e):
            return "homenagens"
        return "leis"
    if t == "MOC":
        return "homenagens" if RE_HOMENAGEM.search(e) else "outros"
    if t in ("PEDIF", "REP"):
        return "cobrancas"
    # REQ / IND
    if RE_HOMENAGEM.search(e):
        return "homenagens"
    if RE_INTERNO.search(e):
        return "outros"
    if RE_COBRANCA.search(e):
        return "cobrancas"
    return "pedidos"


def achar_tema(e):
    # o tema é o que aparece primeiro no texto (o assunto principal costuma vir no começo)
    melhor = None
    for nome, rx in TEMAS:
        m = rx.search(e)
        if m and (melhor is None or m.start() < melhor[0]):
            melhor = (m.start(), nome)
    return melhor[1] if melhor else "Outros pedidos"


def achar_rua(e):
    m = RE_RUA.search(e)
    if not m:
        return ""
    tipo = m.group(1)
    tipo = {"R.": "Rua", "Av.": "Avenida", "Tv.": "Travessa"}.get(tipo, tipo)
    nome = m.group(2).strip(" .-")
    if len(nome) < 3:
        return ""
    return titulo(f"{tipo} {nome}")


def achar_bairro(e):
    m = RE_BAIRRO.search(e)
    if not m:
        return ""
    b = m.group(1).strip(" .-")
    return titulo(b) if len(b) >= 3 else ""


RE_NAO_VEREADOR = re.compile(r"sem efeito|executivo|prefeit|mesa diretora|comiss[aã]o|iniciativa popular|popular|c[aâ]mara", re.I)


def casar_autores(texto, vereadores):
    """Devolve lista de ids de vereador (ou nomes 'x:Nome' para quem não está na lista atual)."""
    pedacos = [p.strip() for p in re.split(r",|;| e (?=[A-ZÀ-Ý])", texto) if p.strip()]
    res = []
    for p in pedacos:
        cp = chave(p)
        alvo = None
        for v in vereadores:
            for k in v["_chaves"]:
                if k and (k == cp or (len(k) >= 5 and (k in cp or cp in k))):
                    alvo = v["id"]
                    break
            if alvo:
                break
        if alvo is None:
            if RE_NAO_VEREADOR.search(p) or not cp:
                continue
            alvo = "x:" + p
        if alvo not in res:
            res.append(alvo)
    return res


def main():
    props = json.loads((BRUTO / "proposicoes.json").read_text())
    vereadores = json.loads((BRUTO / "vereadores.json").read_text())
    datas = json.loads((CACHE / "datas.json").read_text()) if (CACHE / "datas.json").exists() else {}
    coletado = (BRUTO / "coletado_em.txt").read_text().strip() if (BRUTO / "coletado_em.txt").exists() else ""

    for v in vereadores:
        ks = {chave(v["apelido"]), chave(v["nome"])}
        for parte in re.split(r"\s+-\s+", v["apelido"]):
            ks.add(chave(parte))
        v["_chaves"] = [k for k in ks if len(k) >= 3]

    externos = {}
    saida = []
    for p in props:
        autores = casar_autores(p["autor"], vereadores)
        ids = []
        for a in autores:
            if isinstance(a, str):
                if a not in externos:
                    externos[a] = 1000 + len(externos)
                ids.append(externos[a])
            else:
                ids.append(a)
        grupo = classificar(p)
        e = p["ementa"]
        item = {
            "i": p["id"],
            "t": p["tipo"],
            "n": p["numero"],
            "a": p["ano"],
            "d": datas.get(str(p["id"]), ""),
            "g": grupo,
            "au": ids,
            "e": e,
            "s": p["situacao"],
        }
        if grupo in ("pedidos", "cobrancas"):
            rua, bairro = achar_rua(e), achar_bairro(e)
            if rua:
                item["r"] = rua
            if bairro:
                item["b"] = bairro
            if grupo == "pedidos":
                item["tm"] = achar_tema(e)
        saida.append(item)

    # vereadores fora da lista atual (suplentes que saíram, ex-vereadores da legislatura)
    lista = [{k: v for k, v in x.items() if not k.startswith("_")} for x in vereadores]
    for nome, vid in externos.items():
        lista.append({"id": vid, "nome": nome[2:], "apelido": nome[2:], "partido": "",
                      "email_gabinete": "", "telefone_gabinete": "", "ficha": "",
                      "fora_da_lista": True})

    cont = defaultdict(Counter)
    for it in saida:
        for a in it["au"]:
            cont[a][it["g"]] += 1
            cont[a]["total"] += 1
            if len(it["au"]) > 1:
                cont[a]["coautoria"] += 1
    for v in lista:
        v["contagem"] = dict(cont.get(v["id"], {}))
    # quem está fora da lista atual e não tem nenhuma proposta não aparece
    lista = [v for v in lista if not v.get("fora_da_lista") or v["contagem"]]
    lista.sort(key=lambda v: chave(v["apelido"]))

    # problemas que não somem: mesma rua + mesmo tipo de pedido, 2 vezes ou mais
    grupos_rua = defaultdict(list)
    for it in saida:
        if it["g"] == "pedidos" and it.get("r"):
            grupos_rua[(chave(it["r"]), it["tm"])].append(it)
    repetidos = []
    for (_, tema), itens in grupos_rua.items():
        if len(itens) < 2:
            continue
        itens.sort(key=lambda x: (x["d"] or "9999", x["a"], int(re.sub(r"\D", "", x["n"]) or 0)))
        bairros = Counter(x.get("b", "") for x in itens if x.get("b"))
        repetidos.append({
            "r": Counter(x["r"] for x in itens).most_common(1)[0][0],
            "b": bairros.most_common(1)[0][0] if bairros else "",
            "tm": tema,
            "q": len(itens),
            "ids": [x["i"] for x in itens],
            "nv": len({a for x in itens for a in x["au"]}),
            "d1": min((x["d"] for x in itens if x["d"]), default=""),
            "d2": max((x["d"] for x in itens if x["d"]), default=""),
        })
    repetidos.sort(key=lambda x: -x["q"])

    # bairros mais citados (juntando grafias diferentes do mesmo nome)
    por_chave = defaultdict(Counter)
    for it in saida:
        if it.get("b"):
            por_chave[chave(it["b"])][it["b"]] += 1
    bairros_top = sorted(((c.most_common(1)[0][0], sum(c.values())) for c in por_chave.values()), key=lambda x: -x[1])[:15]

    sem_data = sum(1 for it in saida if not it["d"])
    tot = Counter(it["g"] for it in saida)
    resumo = {
        "atualizado": coletado,
        "grupos": GRUPOS,
        "regras": REGRAS,
        "totais": dict(tot),
        "total": len(saida),
        "sem_data": sem_data,
        "anos": sorted({it["a"] for it in saida}),
        "vereadores": lista,
        "temas": Counter(it["tm"] for it in saida if it.get("tm")).most_common(12),
        "bairros": [[b, n] for b, n in bairros_top],
        "recentes": [it for it in sorted((x for x in saida if x["d"]), key=lambda x: (x["d"], x["i"]), reverse=True)[:6]],
        "subsidio": SUBSIDIO,
    }
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, separators=(",", ":")))
    (SAIDA / "propostas.json").write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")))
    (SAIDA / "repetidos.json").write_text(json.dumps(repetidos, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(saida)} propostas, {len(lista)} vereadores, {len(repetidos)} grupos de pedidos repetidos, {sem_data} sem data")
    print("por grupo:", dict(tot))
    com_rua = sum(1 for it in saida if it.get("r"))
    com_bairro = sum(1 for it in saida if it.get("b"))
    print(f"com rua: {com_rua}, com bairro: {com_bairro}, pedidos: {tot['pedidos']}")


if __name__ == "__main__":
    main()
