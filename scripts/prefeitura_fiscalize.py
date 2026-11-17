"""Prefeitura de Juiz de Fora: temas que a população mais gosta de fiscalizar.

Lê os empenhos já baixados por prefeitura_despesas.py (site/dados/prefeitura/empenhos_AAAA.json)
e separa, pelo elemento de despesa e pelo texto do histórico de cada empenho:
  shows       shows, festas e eventos (cachês, palco, som, carnaval, festivais)
  propaganda  publicidade e propaganda (e, separado, publicações oficiais obrigatórias)
  veiculos    aluguel de carros e máquinas, combustível, manutenção e peças
  diarias     diárias, passagens e locomoção
  escolas     repasses às caixas escolares (dinheiro que vai direto para cada escola)
  obras       todas as obras, com busca por bairro ou rua, e as sem nenhum pagamento há meses

Saída: site/dados/prefeitura/fiscalize.json e site/dados/prefeitura/obras.json

Regras de privacidade iguais ao resto do site: pagamentos a pessoas físicas aparecem só somados,
sem nome nem histórico. A classificação é feita por palavras e pode ter erros; o site avisa isso.
"""
import datetime as dt
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "site" / "dados" / "prefeitura"
FONTE = "https://www.pjf.mg.gov.br/transparencia/dados_abertos/arquivos.php"
DIAS_PARADA = 120
MIN_PARADA = 50_000


def conserta(s):
    """Desfaz texto com acentuação corrompida (ex.: 'PUBLICAÃ‡ÃƒO' -> 'PUBLICAÇÃO')."""
    s = str(s or "")
    if "Ã" not in s and "Â" not in s:
        return s
    for b, c in (("\x81", "Á"), ("\x8d", "Í"), ("\x8f", "Ï"), ("\x90", "Ð"), ("\x9d", "Ý")):
        s = s.replace("Ã" + b, c)
    try:
        return s.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    def um(m):
        try:
            return m.group(0).encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return m.group(0)
    s = re.sub(r"[ÃÂ][\u0080-¿‘-›Œ-ƒˆ-˜€™]", um, s)
    for errado, certo in (("ÃUDIO", "ÁUDIO"), ("VÃDEO", "VÍDEO"), ("MUNICÃPIO", "MUNICÍPIO"), ("BÃSIC", "BÁSIC"),
                          ("ÃREA", "ÁREA"), ("ÃNDICE", "ÍNDICE"), ("SAÃDE", "SAÚDE"), ("ÃGUA", "ÁGUA")):
        s = s.replace(errado, certo)
    return s.replace("Â", "")


def norm(s):
    s = conserta(s)
    s = re.sub(r"([A-Za-zÀ-ÿ])\s?-\s?([A-Za-zÀ-ÿ])", r"\1\2", s)  # sílaba quebrada: "PU-BLICAÇÃO"
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").upper()
    return " " + re.sub(r"[^A-Z0-9]+", " ", s) + " "


def limpo(s):
    s = re.sub(r"\s+", " ", conserta(s)).strip()
    letras = [c for c in s if c.isalpha()]
    if letras and sum(c.isupper() for c in letras) > 0.7 * len(letras):
        s = s.upper()  # históricos vêm em maiúsculas; corrige acentos que ficaram minúsculos
    return s.replace("Nº", "nº")


R = lambda p: re.compile(p)
SHOWS = R(r" SHOWS? |APRESENTACA[OE]S? (ARTISTIC|MUSIC|CULTUR)| CACHES? |CONTRATACAO D[OAE]S? (BANDAS?|ARTISTAS?|CANTOR|GRUPO MUSICAL)"
          r"| CARNAVAL| REVEILLON| FESTIVA[LI]S?| PALCOS?| SONORIZACAO| TRIO ELETRICO| ARTISTAS? ")
SHOWS_NAO = R(r"PROGRAMA GENTE EM PRIMEIRO LUGAR|LIMPEZA|BRIGADISTA")
PROPAG = R(r"PUBLICIDAD|PUBLICITARI|PROPAGANDA| VEICULACAO|CAMPANHAS? (INSTITUCIONA|EDUCATIVA|PUBLICIT|DE DIVULG)")
OFICIAL = R(r"PUBLICACA?O?E?S? (OFICIA|LEGA|DE ATOS|NO DIARIO|EM JORNA|DE EDITA|DE EXTRATO)|DIARIO OFICIAL|IMPRENSA OFICIAL|IMPRENSA NACIONAL")
LOCACAO = R(r"LOCACAO D[EO]S? (\d+ )?(VEICUL|AUTOMOV|CAMINH|ONIBUS|VANS?|CARROS?|MOTOCICL|MAQUINAS (PESADAS|E EQUIPAMENTOS DIVERSOS)|ESCAVADEIRA|RETROESCAV)"
            r"| LOCACAO DE FROTA|VEICULOS? (LOCAD|COM MOTORISTA)| ALUGUEL DE (CARROS|VEICUL)")
COMBUST = R(r"COMBUSTIV| GASOLINA| DIESEL| ETANOL| ABASTECIMENTO D[AE] (FROTA|VEICUL)|GERENCIAMENTO E CONTROLE DE FROTA")
MANUT = R(r"MANUTENCAO (PREVENTIVA (E|E/OU) CORRETIVA |CORRETIVA |PREVENTIVA )?D[AEO]S? (FROTA|VEICUL)|PECAS AUTOMOTIV|PECAS (PARA|DE) VEICUL| PNEUS ")
ESCOLAR_NAO = R(r"TRANSPORTE ESCOLAR|TRANSPORTE D[EO]S? PACIENT")
PACIENTE = R(r"PACIENT| TFD |TRATAMENTO FORA")
DIARIA_EL = R(r"DIARIA|PASSAGE|LOCOMOC")
OBRA_EL = R(r" OBRAS ")
CAIXA = R(r"CAIXA ESCOLAR|CX ESCOLAR|CAIXA ESC ")


def escola_de(nome):
    n = re.sub(r"(?i)^(caixa escolar|cx\.? escolar)\s*(d[aoe]s?\s+)?", "", limpo(nome)).strip(" .-")
    n = re.sub(r"(?i)^e\.?\s?m\.?\s*", "E.M. ", n)
    n = re.sub(r"(?i)^em\s+", "E.M. ", n)
    n = re.sub(r"(?i)\bver\.", "Ver. ", n)
    n = re.sub(r"(?i)\bdr\.", "Dr. ", n)
    n = re.sub(r"(?i)\bprof\.?(?=\S)", "Prof. ", n)
    return re.sub(r"\s+", " ", n).strip()


def carregar():
    anos = {}
    for f in sorted(PASTA.glob("empenhos_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        anos[int(d["ano"])] = d
    return anos


def novo_tema(titulo):
    return {"titulo": titulo, "anos": defaultdict(lambda: {"e": 0.0, "p": 0.0, "n": 0}),
            "sec": defaultdict(lambda: [0.0, 0.0]), "cred": {}, "sub": defaultdict(lambda: [0.0, 0.0]),
            "pf": defaultdict(lambda: [0.0, 0.0, 0]), "itens": []}


def soma(t, ano, sec, cnpj, nome, e, p, item, sub=""):
    a = t["anos"][str(ano)]
    a["e"] += e
    a["p"] += p
    a["n"] += 1
    t["sec"][sec][0] += e
    t["sec"][sec][1] += p
    if sub:
        t["sub"][sub][0] += e
        t["sub"][sub][1] += p
    if cnpj:
        c = t["cred"].setdefault(cnpj, [cnpj, nome, 0.0, 0.0, 0])
        c[2] += e
        c[3] += p
        c[4] += 1
        t["itens"].append(item)
    else:
        f = t["pf"][sec]
        f[0] += e
        f[1] += p
        f[2] += 1


def fechar(t, max_itens=400):
    r2 = lambda v: round(v, 2)
    itens = sorted(t["itens"], key=lambda i: -i[5])[:max_itens]
    return {
        "titulo": t["titulo"],
        "anos": {a: {"e": r2(v["e"]), "p": r2(v["p"]), "n": v["n"]} for a, v in sorted(t["anos"].items())},
        "secretarias": sorted(([s, r2(v[0]), r2(v[1])] for s, v in t["sec"].items()), key=lambda x: -x[1]),
        "subtemas": sorted(([s, r2(v[0]), r2(v[1])] for s, v in t["sub"].items()), key=lambda x: -x[1]),
        "fornecedores": sorted(([c[0], c[1], r2(c[2]), r2(c[3]), c[4]] for c in t["cred"].values()), key=lambda x: -x[2])[:60],
        "pessoas_fisicas": sorted(([s, r2(v[0]), r2(v[1]), v[2]] for s, v in t["pf"].items()), key=lambda x: -x[1]),
        "n_itens": len(t["itens"]),
        "itens": itens,
    }


def main():
    anos = carregar()
    if not anos:
        raise SystemExit("sem empenhos da Prefeitura para classificar")
    hoje = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).date()
    limite = (hoje - dt.timedelta(days=DIAS_PARADA)).isoformat()
    T = {k: novo_tema(n) for k, n in [
        ("shows", "Shows, festas e eventos"), ("propaganda", "Propaganda"),
        ("veiculos", "Carros, máquinas e combustível"), ("diarias", "Diárias e viagens"),
        ("escolas", "Dinheiro direto para as escolas")]}
    escolas = defaultdict(lambda: {"cnpj": "", "nome": "", "anos": defaultdict(lambda: [0.0, 0.0])})
    obras = []
    for ano, d in sorted(anos.items()):
        secs, els, creds = d["secretarias"], d["elementos"], d["credores"]
        for x in d["empenhos"]:
            data, si, ci, ei, e, p, hist, num = x
            sec, el = secs[si], els[ei]
            cnpj, nome = (creds[ci] if ci is not None and ci >= 0 else ("", ""))
            nome = limpo(nome)
            h, ne = norm(hist), norm(el)
            texto = h + "|" + ne
            item = [ano, data, sec, nome, cnpj, round(e, 2), round(p, 2), limpo(hist)[:260], num, ""]
            # shows e eventos
            if SHOWS.search(h) and not SHOWS_NAO.search(texto):
                soma(T["shows"], ano, sec, cnpj, nome, e, p, item)
            # propaganda e publicações oficiais
            if OFICIAL.search(h):
                soma(T["propaganda"], ano, sec, cnpj, nome, e, p, item[:9] + ["Publicações oficiais obrigatórias"], "Publicações oficiais obrigatórias")
            elif PROPAG.search(h):
                soma(T["propaganda"], ano, sec, cnpj, nome, e, p, item[:9] + ["Publicidade e propaganda"], "Publicidade e propaganda")
            # veículos
            if not ESCOLAR_NAO.search(h):
                hv = h.replace(" SEM COMBUSTIVEL", " ").replace(" SEM MOTORISTA", " ")
                sub = ("Aluguel de veículos e máquinas" if LOCACAO.search(hv) else
                       "Combustível" if COMBUST.search(hv) or "COMBUSTIVEIS" in ne else
                       "Manutenção e peças" if MANUT.search(hv) or "MANUTENCAO E CONSERVACAO DE VEICULOS" in ne or "MANUTENCAO DE VEICULOS" in ne else "")
                if sub:
                    soma(T["veiculos"], ano, sec, cnpj, nome, e, p, item[:9] + [sub], sub)
            # diárias e viagens
            if DIARIA_EL.search(ne):
                sub = ("Diárias" if "DIARIA" in ne else "Transporte de pacientes" if PACIENTE.search(h)
                       else "Passagens, viagens e locomoção")
                soma(T["diarias"], ano, sec, cnpj, nome, e, p, item[:9] + [sub], sub)
            # caixas escolares
            if cnpj and CAIXA.search(norm(nome)):
                soma(T["escolas"], ano, sec, cnpj, nome, e, p, item)
                es = escolas[cnpj]
                es["cnpj"], es["nome"] = cnpj, escola_de(nome)
                es["anos"][str(ano)][0] += e
                es["anos"][str(ano)][1] += p
            # obras
            if OBRA_EL.search(ne):
                parada = bool(cnpj) and data <= limite and p == 0 and e >= MIN_PARADA and ano == hoje.year
                obras.append([ano, data, sec, nome, cnpj, round(e, 2), round(p, 2), limpo(hist)[:400], num, 1 if parada else 0])
    saida = {k: fechar(t) for k, t in T.items()}
    saida["escolas"]["lista"] = sorted(
        ({"cnpj": v["cnpj"], "nome": v["nome"], "anos": {a: [round(x[0], 2), round(x[1], 2)] for a, x in sorted(v["anos"].items())}}
         for v in escolas.values()), key=lambda v: v["nome"])
    agora = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M")
    (PASTA / "fiscalize.json").write_text(json.dumps({"atualizado": agora, "fonte": FONTE, "temas": saida},
                                                     ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    obras.sort(key=lambda o: (-o[9], -o[5]))
    paradas = [o for o in obras if o[9]]
    (PASTA / "obras.json").write_text(json.dumps({
        "atualizado": agora, "fonte": FONTE, "dias_parada": DIAS_PARADA, "min_parada": MIN_PARADA,
        "campos": ["ano", "data", "secretaria", "credor", "cnpj", "empenhado", "pago", "historico", "numero", "sem_pagamento"],
        "obras": obras}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for k, t in saida.items():
        print(f"{k}: " + ", ".join(f"{a} R$ {v['p'] / 1e6:.2f} mi pagos ({v['n']} empenhos)" for a, v in t["anos"].items()))
    print(f"obras: {len(obras)} empenhos, {len(paradas)} sem nenhum pagamento há mais de {DIAS_PARADA} dias")


if __name__ == "__main__":
    main()
