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


def codigo_nome(nome):
    """Código só do nome completo (para cruzar com listas públicas sem CPF, como os comissionados)."""
    return hashlib.sha256(f"n|{chave(nome)}".encode()).hexdigest()[:20]


def codigo_pessoa(nome, meio_cpf):
    return hashlib.sha256(f"{chave(nome)}|{meio_cpf}".encode()).hexdigest()[:20]


def conserta(t):
    """Textos do arquivo da Prefeitura às vezes vêm com acentos quebrados (Ã§ no lugar de ç)."""
    t = t or ""
    if "Ã" in t or "Â" in t:
        try:
            b = b"".join(ch.encode("cp1252") if ch not in "\x81\x8d\x8f\x90\x9d" else ch.encode("latin-1") for ch in t)
            return b.decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return t


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
        for data, u, ic, ie, e, p, hist, num, *_ in d["empenhos"]:
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
        if x and (hoje - dt.date.fromisoformat(x["_em"])).days < VALIDADE_CNPJ and (("cnaes2" in x and "cep" in x) or x.get("nao_encontrado")):
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
        socios, socios_n = [], []
        for s in d.get("qsa") or []:
            doc = re.sub(r"\D", "", s.get("cnpj_cpf_do_socio") or "")
            if len(doc) == 6:  # CPF mascarado: ***123456**
                socios.append(codigo_pessoa(s.get("nome_socio", ""), doc))
            if len(doc) != 14 and len((s.get("nome_socio") or "").split()) >= 3:
                socios_n.append([codigo_nome(s.get("nome_socio", "")), s.get("qualificacao_socio") or ""])
        cache[c] = {"_em": hoje.isoformat(), "abertura": d.get("data_inicio_atividade"),
                    "situacao": d.get("descricao_situacao_cadastral"), "data_situacao": d.get("data_situacao_cadastral"),
                    "capital": d.get("capital_social"), "porte": d.get("porte"), "cnae": d.get("cnae_fiscal_descricao"),
                    "municipio": d.get("municipio"), "uf": d.get("uf"), "natureza": d.get("natureza_juridica"),
                    "socios": socios, "socios_n": socios_n,
                    "cnaes2": [c.get("descricao") or "" for c in (d.get("cnaes_secundarios") or []) if c.get("descricao")],
                    "cep": re.sub(r"\D", "", str(d.get("cep") or "")), "numero": str(d.get("numero") or "").strip().upper(),
                    "complemento": re.sub(r"\s+", " ", str(d.get("complemento") or "")).strip().upper(),
                    "logradouro": " ".join(x for x in [d.get("descricao_tipo_de_logradouro"), d.get("logradouro")] if x).strip().title(),
                    "bairro": str(d.get("bairro") or "").strip().title()}
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
        eh_empresa = re.search(r"empres[áa]ri|limitada|an[ôo]nima|eireli|individual", natureza, re.I) and not PUBLICA.search(natureza)
        achados = [(s, doadores[s]) for s in (x.get("socios") or []) if s in doadores] if eh_empresa else []
        if achados:
            lst = [d for _, ds in achados for d in ds]
            cand = "; ".join(sorted({f"{u} ({cg}, {pt})" for u, cg, pt, _ in lst}))
            tot = sum(val for *_, val in lst)
            quem = "Um sócio" if len(achados) == 1 else f"{len(achados)} sócios"
            add("doador", c, "Sócio doou para campanha em Juiz de Fora",
                f"{quem} desta empresa aparece{'m' if len(achados) > 1 else ''} como doador{'es' if len(achados) > 1 else ''} da eleição de 2024 em JF ({brl(tot)} no total), para: {cand}. A empresa recebeu {brl(rec)} da Prefeitura no período. Doar é legal; o sinal é o cruzamento.",
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


    # 9. comissionado da Prefeitura com o mesmo nome completo de sócio ou dirigente de fornecedor
    fc = RAIZ / "data" / "prefeitura" / "comissionados.json"
    comiss = {}
    if fc.exists():
        C = json.loads(fc.read_text(encoding="utf-8"))
        for nome, cargo, lot, *resto in C.get("pessoas", []):
            if len(nome.split()) >= 3:
                tipo = resto[4] if len(resto) > 4 else "c"
                comiss.setdefault(codigo_nome(nome), []).append((nome, cargo, C.get("siglas", {}).get(lot, lot), tipo))
    for c in alvo:
        x = cad.get(c) or {}
        if PUBLICA.search(x.get("natureza") or ""):
            continue
        for h, qual in x.get("socios_n") or []:
            for nome, cargo, sec, tipo in comiss.get(h, []):
                rec = max(por_cred[c]["p"], por_cred[c]["e"])
                mesma = any(sec.lower() in l["sec"].lower() or l["sec"].lower() in sec.lower() for l in linhas if l["cnpj"] == c)
                add("comissionado", c, "Ocupante de cargo de confiança com nome igual ao de sócio ou dirigente",
                    f"{nome.title()}, {'comissionado(a)' if tipo == 'c' else 'servidor(a) concursado(a) na função de confiança'} como {cargo.title()} em {sec}, tem o mesmo nome completo de quem aparece como {qual.lower() or 'sócio'} desta empresa ou entidade no cadastro da Receita. "
                    f"Ela recebeu {brl(rec)} da Prefeitura no período{', inclusive da mesma secretaria' if mesma else ''}. Pode ser outra pessoa com o mesmo nome: confira antes de concluir.",
                    rec)

    # 10. pagamento por algo que não combina com a atividade registrada na Receita
    CATEGORIAS = [
        ("transporte e locação de veículos", r"TRANSPORTE ESCOLAR|LOCA[CÇ][AÃ]O DE (\d+ ?\(?\w*\)? ?)?VE[IÍ]CULO|FRETAMENTO",
         r"transporte|locacao de automoveis|locacao de veiculos|fretamento|onibus|passageiros|taxi|veiculo"),
        ("mão de obra, limpeza, vigilância ou apoio operacional",
         r"(?<!MATERIAL E )M[AÃ]O[ -]?DE[ -]?OBRA|APOIO OPERACIONAL|TERCEIRIZ|POSTOS? DE TRABALHO|SERVI[CÇ]OS? DE LIMPEZA|LIMPEZA E CONSERVA|SERVI[CÇ]OS? DE PORTARIA|VIGIL[AÂ]NCIA (PATRIMONIAL|ARMADA|DESARMADA)",
         r"limpeza|vigil|seguranca|mao de obra|recursos humanos|apoio administrativo|servicos combinados|portaria|conservacao|zeladoria|terceiriz|agenciamento|facilities|manutencao|locacao de mao"),
        ("obras e engenharia",
         r"PAVIMENTA|RECAPE|ASFALT|CONSTRU[CÇ][AÃ]O D|DRENAGEM|TERRAPLEN|EXECU[CÇ][AÃ]O DE OBRA|\bOBRAS? DE\b",
         r"constru|obra|engenharia|paviment|terraplen|edific|instalac|demolic|urbaniza|asfalt|infraestrutura|drenag|saneamento|arquitetura|reforma"),
        ("medicamentos", r"MEDICAMENT|F[AÁ]RMACO",
         r"farmac|medicament|produtos para saude|hospitalar|droga|quimic|odontolog|medic"),
        ("combustível", r"(FORNECIMENTO|AQUISI[CÇ][AÃ]O|COMPRA) DE (COMBUST|GASOLINA|[OÓ]LEO DIESEL|ETANOL)|ABASTECIMENTO DE (VE[IÍ]CULOS|FROTA)",
         r"combust|petroleo|posto|derivados|lubrific|gas"),
        ("alimentos e merenda", r"G[EÊ]NEROS ALIMENT|MERENDA|HORTIFRUTI|ALIMENTA[CÇ][AÃ]O ESCOLAR|REFEI[CÇ][OÕ]ES|MARMITEX",
         r"aliment|refeic|restaurante|supermerc|mercad|hortifrut|laticin|carne|padari|cereal|bebida|frigor|atacad|cozinha|lanchon|buffet|cooperativa|agricult|cultivo|criacao|pecuaria|ovos|frutas|legumes|varejista"),
        ("software e informática", r"SOFTWARE|LICEN[CÇ]A DE USO|SISTEMA INFORMATIZADO|LOCA[CÇ][AÃ]O DE SISTEMA|DATA ?CENTER",
         r"software|informatica|programas de computador|tecnologia|processamento de dados|sistemas|dados|internet|telecom|computador"),
        ("ração e cuidado de animais", r"\bRA[CÇ][AÃ]O\b|VETERIN|\bCANIL|CASTRA[CÇ]|ABRIGO\s*EMERGENCIAL DE ANIMAIS|ABRIGO DE ANIMAIS",
         r"animal|animais|veterin|racao|pet|agropecu|zootec|alimentos para"),
    ]
    sem_acento = lambda t: unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    soma_cat = defaultdict(lambda: [0.0, []])
    for l in linhas:
        for nome_cat, rh, _ in CATEGORIAS:
            if re.search(rh, l["hist"]):
                g = soma_cat[(l["cnpj"], nome_cat)]
                g[0] += max(l["e"], l["p"], 0)
                if len(g[1]) < 3:
                    g[1].append(l["hist"][:120].strip())
                break
    for (c, nome_cat), (v, ex) in soma_cat.items():
        x = cad.get(c) or {}
        if v < 100_000 or "cnaes2" not in x or PUBLICA.search(x.get("natureza") or ""):
            continue
        rc = next(r for n, _, r in CATEGORIAS if n == nome_cat)
        ativ = sem_acento(" | ".join([x.get("cnae") or ""] + x.get("cnaes2", [])))
        if not re.search(rc, ativ):
            add("atividade", c, "Pago por algo que não combina com a atividade da empresa",
                f"Recebeu {brl(v)} em empenhos de {nome_cat} (exemplo: \"{ex[0].title()}\"), mas a atividade principal registrada na Receita é \"{x.get('cnae') or 'não informada'}\" e nenhuma atividade secundária é desse ramo. Pode haver explicação, mas vale perguntar como a empresa foi escolhida.",
                v)

    # 12. empresas diferentes com o mesmo sócio, pagas pela mesma secretaria
    sec_de = defaultdict(lambda: defaultdict(float))
    for l in linhas:
        sec_de[l["cnpj"]][l["sec"]] += max(l["p"], l["e"], 0)
    def eh_emp(c):
        nat = (cad.get(c) or {}).get("natureza") or ""
        return bool(re.search(r"empres[áa]ri|limitada|an[ôo]nima|eireli|individual", nat, re.I)) and not PUBLICA.search(nat)
    def recebido(c):
        v = por_cred.get(c) or {}
        return max(v.get("p", 0), v.get("e", 0))
    SAUDE_SUS = re.compile(r"atendimento|atividade m[ée]dica|diagn[óo]s|laborat[óo]rios? cl[íi]nic|fisioterapia|odontol|hemoterapia|di[áa]lise|nefrolog", re.I)
    def ramo(c):
        x = cad.get(c) or {}
        return {x.get("cnae") or ""} | set(x.get("cnaes2") or [])
    def mesmo_ramo(a, b):
        ca, cb = (cad.get(a) or {}).get("cnae") or "", (cad.get(b) or {}).get("cnae") or ""
        if not ca or not cb or SAUDE_SUS.search(ca) or SAUDE_SUS.search(cb):
            return False  # prestadores do SUS são credenciados, não disputam preço entre si
        return ca in ramo(b) or cb in ramo(a)
    por_socio = defaultdict(set)
    for c, x in cad.items():
        if recebido(c) >= 50_000 and eh_emp(c):
            for sc in set(x.get("socios") or []):
                por_socio[sc].add(c)
    pares = defaultdict(set)
    for sc, cs in por_socio.items():
        if 2 <= len(cs) <= 6:
            for a in cs:
                for b in cs:
                    if a[:8] != b[:8]:  # filiais da mesma empresa não contam
                        pares[a].add(b)
    for c, outras in pares.items():
        comuns = [(o, set(sec_de[c]) & set(sec_de[o])) for o in outras]
        comuns = [(o, ss) for o, ss in comuns if ss and mesmo_ramo(c, o)]
        if not comuns:
            continue
        lista = "; ".join(f"{nomes.get(o) or o} (CNPJ {o[:2]}.{o[2:5]}.{o[5:8]}/{o[8:12]}-{o[12:]}, {brl(recebido(o))})" for o, _ in comuns[:4])
        secs = sorted({s for _, ss in comuns for s in ss})[:3]
        add("socio_comum", c, "Tem sócio em comum com outro fornecedor da mesma secretaria",
            f"Pelo menos um sócio desta empresa também é sócio de: {lista}. Atuam no mesmo ramo segundo a Receita e receberam da mesma unidade ({', '.join(secs)}). Ter sócio em comum não é ilegal; o ponto de atenção é se elas disputaram a mesma compra como se fossem concorrentes.",
            recebido(c), sec=secs[0])

    # 13. empresas diferentes no mesmo endereço (mesmo CEP, número e complemento), pagas pela mesma secretaria
    por_end = defaultdict(set)
    for c, x in cad.items():
        if x.get("cep") and x.get("numero") and x["numero"] not in ("S/N", "SN", "0") and recebido(c) >= 50_000 and eh_emp(c):
            por_end[(x["cep"], x["numero"], x.get("complemento", ""))].add(c)
    for (cep, num, comp), cs in por_end.items():
        raizes = {c[:8] for c in cs}
        if len(raizes) < 2 or len(raizes) > 5:
            continue
        for c in cs:
            outras = [o for o in cs if o[:8] != c[:8] and o not in pares.get(c, set()) and set(sec_de[c]) & set(sec_de[o]) and mesmo_ramo(c, o)]
            if not outras:
                continue
            x = cad[c]
            ender = f"{x.get('logradouro') or 'endereço'}, {num}{(' ' + comp.title()) if comp else ''}, {x.get('bairro') or ''} (CEP {cep[:5]}-{cep[5:]})".replace(", (", " (")
            lista = "; ".join(f"{nomes.get(o) or o} ({brl(recebido(o))})" for o in outras[:4])
            secs = sorted({s for o in outras for s in set(sec_de[c]) & set(sec_de[o])})[:3]
            add("endereco", c, "Mesmo endereço de outro fornecedor da mesma secretaria",
                f"No cadastro da Receita esta empresa fica em {ender}, o mesmo endereço de: {lista}. Atuam no mesmo ramo segundo a Receita e receberam da mesma unidade ({', '.join(secs)}). Pode ser um prédio comercial ou um contador em comum; o ponto de atenção é se disputaram a mesma compra.",
                recebido(c), sec=secs[0])

    # 11. sinais do PNCP (contratos que cresceram, licitação acima do orçado ou sem desconto)
    fp = DADOS / "pncp_sinais.json"
    if fp.exists():
        for a in json.loads(fp.read_text(encoding="utf-8")).get("sinais", []):
            a["nome"] = nomes.get(a["cnpj"]) or a.get("nome") or ""
            alertas.append(a)

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
        "comissionado": "Cargo de confiança com nome de sócio",
        "atividade": "Atividade não combina com o pagamento",
        "aditivo": "Contrato cresceu muito",
        "acima": "Licitação acima do orçado",
        "desconto": "Licitação sem desconto",
        "socio_comum": "Sócio em comum com outro fornecedor",
        "endereco": "Mesmo endereço de outro fornecedor",
    }
    alertas.sort(key=lambda a: -a["valor"])
    # data em que cada alerta apareceu pela primeira vez (para o resumo do dia e o canal no WhatsApp)
    hoje = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).date().isoformat()
    chave_a = lambda a: f"{a['tipo']}|{a['cnpj']}|{a['titulo']}"
    antes = {}
    for f in (SAIDA, Path("/tmp/anterior/dados/prefeitura/alertas.json")):
        try:
            for a in json.loads(f.read_text(encoding="utf-8")).get("alertas", []):
                antes.setdefault(chave_a(a), a.get("desde") or "antes")
        except (OSError, ValueError):
            pass
    for a in alertas:
        a["desde"] = antes.get(chave_a(a)) or (hoje if antes else "antes")
    res = {"coletado_em": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "anos": list(ANOS),
           "tipos": TIPOS, "contagem": {t: sum(1 for a in alertas if a["tipo"] == t) for t in TIPOS},
           "fontes": ["Portal da Transparência da Prefeitura de Juiz de Fora (empenhos)",
                      "Receita Federal (cadastro de CNPJ, via minhareceita.org)",
                      "Tribunal Superior Eleitoral (doações de 2024)",
                      "Controladoria-Geral da União (CEIS e CNEP)",
                      "Portal Nacional de Contratações Públicas (PNCP)"],
           "alertas": alertas}
    SAIDA.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("Alertas:", res["contagem"])


if __name__ == "__main__":
    main()
