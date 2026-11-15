"""Sinais de alerta nos gastos da Prefeitura de Juiz de Fora.

Junta dados públicos e aponta situações que merecem uma pergunta. Um sinal NÃO é prova de
irregularidade: muitas vezes há explicação legal (emergência real, único fornecedor, prestador
contratado por licitação antiga etc.). O site deixa isso claro em cada sinal.

Fontes:
  - Empenhos e pagamentos da Prefeitura (arquivos de despesas do Portal da Transparência, já
    publicados pelo Radar em site/dados/prefeitura/empenhos_AAAA.json).
  - Cadastro de CNPJ da Receita Federal (via minhareceita.org, que republica os dados abertos da Receita).
  - Doações de campanha de 2024 em Juiz de Fora (TSE), guardadas como códigos em data/doadores_jf_2024.json.
  - Cadastros de empresas punidas da CGU (CEIS e CNEP), quando o download estiver disponível.

Nenhum nome de pessoa física é gravado: sócios e doadores viram códigos (nome + 6 dígitos do meio do CPF).

Saída: site/dados/prefeitura/alertas.json
"""
import csv
import datetime as dt
import hashlib
import io
import json
import re
import sys
import time
import unicodedata
import zipfile
from collections import defaultdict
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "site" / "dados" / "prefeitura"
CACHE = RAIZ / "data" / "cache" / "cnpj.json"
SAIDA = DADOS / "alertas.json"
UA = {"User-Agent": "RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
ANOS = (2025, 2026)
# limites de dispensa por valor (Lei 14.133, art. 75, atualizados por decreto a cada ano)
LIMITE = {2025: {"obras": 125451.15, "outros": 62725.59}, 2026: {"obras": 130984.20, "outros": 65492.11}}
MIN_CNPJ = 50_000          # só consulta o cadastro de empresas que receberam pelo menos isso
TEMPO_CNPJ = 900           # segundos por execução para consultas novas de CNPJ
VALIDADE_CNPJ = 120        # dias até consultar de novo a mesma empresa

LICITADO = re.compile(r"PREG[AÃ]O|ATA DE REGISTRO|\bATA\b|CONCORR|TOMADA DE PRE|CONTRATO|ADES[AÃ]O|CREDENCIAMENTO|"
                      r"TERMO DE (COLABORA|FOMENTO|CONV)|CONV[EÊ]NIO|PARCERIA|INEXIG|REPASSE|EMERG|\bLEI\b|DEA\b|"
                      r"EXERC[IÍ]CIO ANTERIOR|PESSOAL|AMORTIZ|SUBSTITUI|ALUGUEL|LOCA[CÇ][AÃ]O DO IM|TARIFA|FATURA|"
                      r"ENERGIA|[AÁ]GUA|TELEFON|CORREIOS|INSS|PASEP|FGTS|JUROS|PRECAT|SENTEN|JUDICIAL|DI[AÁ]RIA")
ELEM_COMPRA = re.compile(r"material de consumo|outros serv.*terceiros.*jur|equipamentos e material permanente|obras e instala|"
                        r"tecnologia da informa|distribui|g[êe]neros de alimenta", re.I)
PUBLICA = re.compile(r"p[úu]blic|autarquia|munic[íi]pio|estado|uni[ãa]o|cons[óo]rcio p[úu]blico|economia mista|fundo", re.I)
DISPENSA = re.compile(r"DISPENSA|CONTRATA[CÇ][AÃ]O DIRETA|COMPRA DIRETA")


def chave(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def codigo_pessoa(nome, meio_cpf):
    return hashlib.sha256(f"{chave(nome)}|{meio_cpf}".encode()).hexdigest()[:20]


def conserta(t):
    """Textos do arquivo da Prefeitura às vezes vêm com acentos quebrados (Ã§ no lugar de ç)."""
    if t and ("Ã" in t or "Â" in t):
        try:
            return t.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return t
    return t or ""


def carregar_empenhos():
    linhas = []
    nomes = {}
    for ano in ANOS:
        f = DADOS / f"empenhos_{ano}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        sec, el, cred = d["secretarias"], d["elementos"], d["credores"]
        for c, n in cred:
            nomes[c] = n
        for data, u, ic, ie, e, p, hist, num in d["empenhos"]:
            if ic < 0:
                continue  # pessoa física: fora dos sinais
            linhas.append({"ano": ano, "data": data, "sec": sec[u], "cnpj": cred[ic][0], "el": el[ie],
                           "e": e or 0.0, "p": p or 0.0, "hist": conserta(hist).upper(), "num": num})
    return linhas, nomes


def brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------- cadastro de CNPJ ----------------
def consultar_cnpj(cnpjs):
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    hoje = dt.date.today()
    inicio = time.time()
    novos = 0
    for c in cnpjs:
        if len(c) != 14:
            continue
        x = cache.get(c)
        if x and (hoje - dt.date.fromisoformat(x["_em"])).days < VALIDADE_CNPJ:
            continue
        if time.time() - inicio > TEMPO_CNPJ:
            break
        try:
            r = requests.get(f"https://minhareceita.org/{c}", headers=UA, timeout=30)
        except requests.RequestException:
            time.sleep(5)
            continue
        if r.status_code == 429:
            time.sleep(30)
            continue
        if r.status_code != 200:
            if r.status_code == 404:
                cache[c] = {"_em": hoje.isoformat(), "nao_encontrado": True}
            time.sleep(1)
            continue
        d = r.json()
        socios = []
        for s in d.get("qsa") or []:
            doc = re.sub(r"\D", "", s.get("cnpj_cpf_do_socio") or "")
            if len(doc) == 6:  # CPF mascarado: ***123456**
                socios.append(codigo_pessoa(s.get("nome_socio", ""), doc))
        cache[c] = {"_em": hoje.isoformat(), "abertura": d.get("data_inicio_atividade"),
                    "situacao": d.get("descricao_situacao_cadastral"), "data_situacao": d.get("data_situacao_cadastral"),
                    "capital": d.get("capital_social"), "porte": d.get("porte"), "cnae": d.get("cnae_fiscal_descricao"),
                    "municipio": d.get("municipio"), "uf": d.get("uf"), "natureza": d.get("natureza_juridica"),
                    "socios": socios}
        novos += 1
        time.sleep(0.6)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    print(f"CNPJ: {novos} consultas novas, {len(cache)} no cadastro guardado")
    return cache


# ---------------- empresas punidas (CGU) ----------------
def punidas():
    out = {}
    for base in ("ceis", "cnep"):
        for atras in range(0, 10):
            dia = (dt.date.today() - dt.timedelta(days=atras)).strftime("%Y%m%d")
            try:
                r = requests.get(f"https://portaldatransparencia.gov.br/download-de-dados/{base}/{dia}", headers=UA, timeout=120)
            except requests.RequestException:
                continue
            if r.status_code != 200 or r.content[:2] != b"PK":
                continue
            z = zipfile.ZipFile(io.BytesIO(r.content))
            with z.open(z.infolist()[0]) as fh:
                rd = csv.DictReader(io.TextIOWrapper(fh, encoding="latin-1"), delimiter=";")
                for row in rd:
                    doc = re.sub(r"\D", "", row.get("CPF OU CNPJ DO SANCIONADO", "") or row.get("CNPJ OU CPF DO SANCIONADO", ""))
                    if len(doc) == 14:
                        out.setdefault(doc, []).append({
                            "cadastro": base.upper(),
                            "sancao": row.get("CATEGORIA DA SANÇÃO", "").strip(),
                            "orgao": row.get("ÓRGÃO SANCIONADOR", "").strip(),
                            "inicio": row.get("DATA INÍCIO SANÇÃO", "").strip(),
                            "fim": row.get("DATA FINAL SANÇÃO", "").strip()})
            print(f"{base.upper()}: arquivo de {dia}")
            break
        else:
            print(f"{base.upper()}: download indisponível")
    return out


def data_br(s):
    for f in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s, f).date()
        except (TypeError, ValueError):
            pass
    return None


# ---------------- sinais ----------------
def main():
    linhas, nomes = carregar_empenhos()
    if len(linhas) < 1000:
        print("Alertas: arquivos de empenhos ausentes ou incompletos")
        sys.exit(1)
    alertas = []

    def add(tipo, cnpj, titulo, detalhe, valor, sec=None, refs=None):
        alertas.append({"tipo": tipo, "cnpj": cnpj, "nome": nomes.get(cnpj, ""), "titulo": titulo,
                        "detalhe": detalhe, "valor": round(valor, 2), "secretaria": sec, "refs": refs or []})

    por_cred = defaultdict(lambda: {"p": 0.0, "e": 0.0, "primeiro": None})
    ultimo_emp = {}
    for x in linhas:
        c = por_cred[x["cnpj"]]
        c["p"] += x["p"]
        c["e"] += max(x["e"], 0)
        if x["data"] and (c["primeiro"] is None or x["data"] < c["primeiro"]):
            c["primeiro"] = x["data"]
        if x["data"] and x["data"] > ultimo_emp.get(x["cnpj"], ""):
            ultimo_emp[x["cnpj"]] = x["data"]

    # 1. possível fracionamento: vários empenhos pequenos, mesmo fornecedor, secretaria e tipo de despesa,
    #    sem citar licitação, que somados passam do limite de dispensa do ano
    grupos = defaultdict(list)
    for x in linhas:
        if x["e"] > 0 and ELEM_COMPRA.search(x["el"]) and not LICITADO.search(x["hist"]):
            grupos[(x["ano"], x["sec"], x["cnpj"], x["el"])].append(x)
    for (ano, sec, cnpj, el), xs in grupos.items():
        lim = LIMITE[ano]["obras" if re.search(r"obra|engenharia|instala", el, re.I) else "outros"]
        peq = [x for x in xs if x["e"] < lim]
        tot = sum(x["e"] for x in peq)
        if len(peq) >= 4 and tot > lim * 1.5:
            add("fracionamento", cnpj, "Possível fracionamento de compra",
                f"{len(peq)} empenhos em {ano}, todos abaixo do limite de dispensa ({brl(lim)}), somando {brl(tot)} "
                f"para o mesmo fornecedor, na mesma secretaria e no mesmo tipo de despesa ({el}), sem citar licitação no histórico.",
                tot, sec, [x["num"] for x in sorted(peq, key=lambda x: x["data"] or "")][:12])

    # 2. contratação direta frequente (dispensa, inexigibilidade, emergência citadas no histórico)
    diretas = defaultdict(lambda: {"n": 0, "e": 0.0, "emerg_meses": set(), "secs": set()})
    for x in linhas:
        h = x["hist"]
        if DISPENSA.search(h) or "INEXIG" in h or "EMERG" in h:
            d = diretas[x["cnpj"]]
            d["n"] += 1
            d["e"] += max(x["e"], 0)
            d["secs"].add(x["sec"])
            if "EMERG" in h and x["data"]:
                d["emerg_meses"].add(x["data"][:7])
    for cnpj, d in diretas.items():
        if d["e"] >= 500_000 and d["n"] >= 3:
            add("direta", cnpj, "Muita contratação sem licitação",
                f"{d['n']} empenhos que citam dispensa, inexigibilidade ou emergência, somando {brl(d['e'])} em {len(d['secs'])} secretaria(s).",
                d["e"])
        if len(d["emerg_meses"]) >= 4:
            add("emergencia", cnpj, "Emergência que se repete",
                f"Empenhos citando emergência em {len(d['emerg_meses'])} meses diferentes. Contratação emergencial deveria ser exceção e de curta duração.",
                d["e"])

    # cadastro de empresas
    alvo = [c for c, v in sorted(por_cred.items(), key=lambda kv: -kv[1]["p"]) if v["p"] >= MIN_CNPJ or v["e"] >= MIN_CNPJ]
    cad = consultar_cnpj(alvo)
    doadores = {}
    fd = RAIZ / "data" / "doadores_jf_2024.json"
    if fd.exists():
        doadores = json.loads(fd.read_text(encoding="utf-8"))
    pun = punidas()

    # 3. concentração: um fornecedor leva grande parte do que a secretaria paga a empresas
    sec_tot = defaultdict(float)
    sec_cred = defaultdict(lambda: defaultdict(float))
    for x in linhas:
        if x["ano"] == ANOS[-1]:
            sec_tot[x["sec"]] += x["p"]
            sec_cred[x["sec"]][x["cnpj"]] += x["p"]
    for sec, tot in sec_tot.items():
        if tot < 2_000_000:
            continue
        priv = {c: v for c, v in sec_cred[sec].items() if not PUBLICA.search((cad.get(c) or {}).get("natureza") or "")}
        if not priv:
            continue
        cnpj, v = max(priv.items(), key=lambda kv: kv[1])
        if v / tot >= 0.4:
            add("concentracao", cnpj, "Um fornecedor concentra os pagamentos",
                f"Recebeu {round(100 * v / tot)}% de tudo o que {sec} pagou a empresas e entidades em {ANOS[-1]} ({brl(v)} de {brl(tot)}). Pode ser normal (hospital conveniado, concessionária), mas vale conferir.",
                v, sec)


    for c in alvo:
        x = cad.get(c) or {}
        v = por_cred[c]
        rec = max(v["p"], v["e"])
        if x.get("nao_encontrado") or not x:
            continue
        ab = data_br(x.get("abertura"))
        prim = data_br(v["primeiro"])
        # 4. empresa nova
        natureza = x.get("natureza") or ""
        if ab and prim and 0 <= (prim - ab).days < 365 and rec >= 100_000 and c[8:12] == "0001" and not PUBLICA.search(natureza) and "cons" not in natureza.lower():
            add("nova", c, "Empresa aberta pouco antes de vender para a Prefeitura",
                f"Aberta em {ab.strftime('%d/%m/%Y')}; primeiro empenho no período em {prim.strftime('%d/%m/%Y')} ({(prim - ab).days} dias depois). Valor: {brl(rec)}.",
                rec)
        # 5. situação cadastral
        sit = (x.get("situacao") or "").upper()
        if sit and sit != "ATIVA" and not PUBLICA.search(natureza):
            add("situacao", c, "Empresa com cadastro irregular na Receita",
                f"Situação na Receita Federal: {sit.title()} desde {(data_br(x.get('data_situacao')) or dt.date(1900, 1, 1)).strftime('%d/%m/%Y')}. Valor no período: {brl(rec)}.", rec)
        # 6. capital social muito baixo para o volume recebido
        cap = x.get("capital") or 0
        empresa = re.search(r"empres[áa]ri|limitada|an[ôo]nima|eireli", x.get("natureza") or "", re.I)
        if empresa and rec >= 1_000_000 and 0 < cap < 0.02 * rec:
            add("capital", c, "Capital social muito pequeno para o tamanho do contrato",
                f"Capital social declarado de {brl(cap)} para {brl(rec)} recebidos ou empenhados. Não é ilegal, mas pode indicar empresa sem estrutura.",
                rec)
        # 7. sócio doou para campanha em JF em 2024
        for s in x.get("socios") or []:
            if s in doadores:
                lst = doadores[s]
                cand = "; ".join(sorted({f"{u} ({cg}, {pt})" for u, cg, pt, _ in lst}))
                tot = sum(val for *_, val in lst)
                add("doador", c, "Sócio doou para campanha em Juiz de Fora",
                    f"Um sócio desta empresa aparece como doador da eleição de 2024 em JF ({brl(tot)}), para: {cand}. A empresa recebeu {brl(rec)} da Prefeitura no período. Doar é legal; o sinal é o cruzamento.",
                    rec)
        # 8. empresa punida
        ultimo = data_br(ultimo_emp.get(c))
        for p in pun.get(c, []):
            ini, fim = data_br(p["inicio"]), data_br(p["fim"])
            if not ini or not prim or (ultimo and ini > ultimo) or (fim and fim < prim):
                continue  # sanção fora do período em que recebeu da Prefeitura
            ampla = re.search(r"inidoneidade|sem prazo|proibi[çc][ãa]o de contratar com o poder p", p["sancao"], re.I)
            if ampla:
                add("punida", c, "Empresa declarada inidônea ou proibida de contratar",
                    f"{p['cadastro']}: {p['sancao']} aplicada por {p['orgao']} (de {p['inicio']} a {p['fim'] or 'sem data final'}), período em que também recebeu da Prefeitura ({brl(rec)}). Esse tipo de sanção vale para toda a administração pública.",
                    rec)
            else:
                add("punida_outro", c, "Empresa punida por outro órgão",
                    f"{p['cadastro']}: {p['sancao']} aplicada por {p['orgao']} (de {p['inicio']} a {p['fim'] or 'sem data final'}). Em regra essa punição vale só para o órgão que a aplicou, mas mostra problema anterior na execução de contratos. Valor recebido da Prefeitura no período: {brl(rec)}.",
                    rec)

    # fracionamento só faz sentido para empresas (associações e órgãos recebem repasses parcelados)
    def empresa(c):
        return bool(re.search(r"empres[áa]ri|limitada|an[ôo]nima|eireli|individual", (cad.get(c) or {}).get("natureza") or "", re.I))
    alertas[:] = [a for a in alertas if a["tipo"] != "fracionamento" or empresa(a["cnpj"])]

    TIPOS = {
        "fracionamento": "Possível fracionamento",
        "direta": "Muita contratação sem licitação",
        "emergencia": "Emergência que se repete",
        "concentracao": "Fornecedor concentra pagamentos",
        "nova": "Empresa recém-aberta",
        "situacao": "Cadastro irregular na Receita",
        "capital": "Capital social pequeno",
        "doador": "Sócio doador de campanha",
        "punida": "Empresa inidônea ou proibida",
        "punida_outro": "Punida por outro órgão",
    }
    alertas.sort(key=lambda a: -a["valor"])
    res = {"coletado_em": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "anos": list(ANOS),
           "tipos": TIPOS, "contagem": {t: sum(1 for a in alertas if a["tipo"] == t) for t in TIPOS},
           "fontes": ["Portal da Transparência da Prefeitura de Juiz de Fora (empenhos)",
                      "Receita Federal (cadastro de CNPJ, via minhareceita.org)",
                      "Tribunal Superior Eleitoral (doações de 2024)",
                      "Controladoria-Geral da União (CEIS e CNEP)"],
           "alertas": alertas}
    SAIDA.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("Alertas:", res["contagem"])


if __name__ == "__main__":
    main()
