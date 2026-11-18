"""Prefeitura de Juiz de Fora: gastos que o povo mais gosta de fiscalizar ("Na lupa").

Lê os empenhos já baixados (site/dados/prefeitura/empenhos_AAAA.json) e separa por tema:
  - veículos, máquinas e combustível
  - diárias e viagens
  - publicidade e propaganda
  - shows, festas e eventos
  - aluguel de imóveis
  - corrida de dezembro (gasto empenhado no fim do ano comparado com os outros meses)

A classificação usa o tipo de despesa (elemento), o texto do empenho (histórico) e o nome da
empresa. Pagamentos a pessoas físicas entram só nos totais, sem nome nem texto.
Saída: site/dados/prefeitura/lupa.json
"""
import datetime as dt
import json
import re
import statistics
import unicodedata
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "site" / "dados" / "prefeitura"
SAIDA = DADOS / "lupa.json"


def conserta(t):
    t = str(t or "")
    if "Ã" in t or "Â" in t:
        try:
            b = b"".join(ch.encode("cp1252") if ch not in "\x81\x8d\x8f\x90\x9d" else ch.encode("latin-1") for ch in t)
            return b.decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return t


def chave(t):
    return "".join(c for c in unicodedata.normalize("NFD", conserta(t)) if unicodedata.category(c) != "Mn").lower()


# (id, título, explicação, regex do elemento, regex do histórico, regex do nome da empresa)
TEMAS = [
    ("veiculos", "Veículos, máquinas e combustível",
     "Combustível, aluguel de carros, caminhões, ônibus e máquinas, e manutenção da frota.",
     r"combust|veicul|tracao mecanica",
     r"combust|gasolina|oleo diesel|\bdiesel\b|abastecimento de (veicul|frota|combust|maquin)|locacao de (\d+ ?\(?\w*\)? ?)?(veicul|caminh|onibus|maquin|automo|van|carro|retroescav|motonivel)|(manutencao|abastecimento|locacao|gestao|controle|rastreamento|seguro|lavagem)( \w+){0,3} (da |de |para )?(a )?frota|veiculos? (leve|pesad|oficia|com motorista|automotor)|manutencao (preventiva e corretiva )?(de|da|dos) (veicul|frota)|pneus",
     r"locadora|rent a car|petroleo|combustiv|auto ?pecas|pneus"),
    ("viagens", "Diárias e viagens",
     "Diárias pagas a servidores em viagem, passagens (inclusive as compradas para a assistência social) e despesas de locomoção.",
     r"diaria|passage|locomo",
     r"passage(m|ns) aere|passagens? rodovi|agenciamento de viage",
     r"turismo e viage|agencia de viage|viagens e turismo"),
    ("publicidade", "Publicidade e propaganda",
     "Campanhas, anúncios, agências de publicidade e divulgação em rádio, TV, jornal e internet.",
     r"publicid|propagand",
     r"publicidad|propaganda|publicitar|campanhas? (publicit|educativ|institucion|de (divulga|comunica|conscientiza|esclarecimento))|veiculacao|divulgacao institucional|agencia de (publicidade|comunicacao)|(?<!multi)\bmidias?\b",
     r"publicid|propaganda|marketing|(?<!tele)comunicacao(?! de dados)|\bmidia|\bradio\b|televis|\btv\b|jornal"),
    ("eventos", "Shows, festas e eventos",
     "Shows, cachês, festas, palco, som, luz e estrutura de eventos, e premiações.",
     r"festividad|premiac",
     r"\bshows?\b|apresentacao artistic|festival|carnaval|reveillon|\bpalco|sonorizacao|iluminacao (cenica|de palco)|cache|festividade|estrutura (para|de) eventos?|infraestrutura (para|de) eventos?|producao de eventos?|decoracao natalina|natal iluminado|festividades de fim de ano|aniversario da cidade|banda (de musica|musical)",
     r"eventos|producoes artist|entretenimento|sonorizacao|shows?\b|palcos?"),
    ("alugueis", "Aluguel de imóveis",
     "Prédios, salas, galpões e casas alugados pela Prefeitura para escolas, postos de saúde, secretarias e abrigos. Não inclui o aluguel social pago às famílias.",
     r"locacao de imove|locacoes de imove",
     r"(locacao|aluguel|alugueis) (de |do |dos |da )?(um |uma )?(imove|predio|sala|galpao|galpoes|casa|espaco fisico|loja|edificac|terreno)",
     r"imobiliari|administradora de imove|empreendimentos imobil"),
]
NAO_FOLHA = re.compile(r"vencim|patronal|aposent|pens|provent|rpps|rgps|previd|aliq|gratif|auxilio|divida|juros|amortiza|"
                       r"indenizac|contratacao por tempo|obrigac|sentenc|deficit atuarial|descontos efetuados|restitui|salario|"
                       r"exercicios anteriores|subvenc|contribuic|transf")


def corrigir_acentos(f):
    """Conserta no próprio arquivo publicado os textos com acento quebrado (vale também para a busca)."""
    d = json.loads(f.read_text(encoding="utf-8"))
    n = 0
    for x in d["empenhos"]:
        if x[6] and ("Ã" in x[6] or "Â" in x[6]):
            novo = conserta(x[6])
            if novo != x[6]:
                x[6] = novo
                n += 1
    for c in d["credores"]:
        if "Ã" in c[1] or "Â" in c[1]:
            c[1] = conserta(c[1])
            n += 1
    if n:
        f.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"{f.name}: {n} textos com acento consertado")


def main():
    for f in DADOS.glob("empenhos_*.json"):
        corrigir_acentos(f)
    anos = sorted(int(f.stem.split("_")[1]) for f in DADOS.glob("empenhos_*.json"))
    temas = {t[0]: {"id": t[0], "titulo": t[1], "texto": t[2], "anos": {}} for t in TEMAS}
    dezembro = {}
    for ano in anos:
        d = json.loads((DADOS / f"empenhos_{ano}.json").read_text(encoding="utf-8"))
        secs, els, creds = d["secretarias"], d["elementos"], d["credores"]
        el_k = [chave(e) for e in els]
        cred_k = [chave(n) for _, n in creds]
        acc = {t[0]: {"p": 0.0, "e": 0.0, "n": 0, "pf": 0.0, "meses": [0.0] * 12, "sec": defaultdict(float),
                      "forn": defaultdict(lambda: [0.0, 0]), "maiores": []} for t in TEMAS}
        mes_sec = defaultdict(lambda: [0.0] * 12)
        mes_tot = [0.0] * 12
        for data, u, ic, ie, e, p, hist, num, *_ in d["empenhos"]:
            hk = chave(hist)
            mes = int(data[5:7]) - 1 if data and len(data) >= 7 else None
            if mes is not None and e and not NAO_FOLHA.search(el_k[ie]):
                mes_tot[mes] += e
                mes_sec[secs[u]][mes] += e
            for tid, _, _, rel, rhi, rcr in TEMAS:
                if re.search(rel, el_k[ie]) or (ic >= 0 and (re.search(rhi, hk) or re.search(rcr, cred_k[ic]))):
                    a = acc[tid]
                    a["p"] += p or 0
                    a["e"] += e or 0
                    a["n"] += 1
                    if mes is not None:
                        a["meses"][mes] += p or 0
                    a["sec"][secs[u]] += p or 0
                    if ic >= 0:
                        f = a["forn"][ic]
                        f[0] += p or 0
                        f[1] += 1
                        a["maiores"].append([data, secs[u], creds[ic][0], creds[ic][1], round(max(p or 0, e or 0), 2), conserta(hist), num])
                    else:
                        a["pf"] += p or 0
                    break
        for tid, a in acc.items():
            if not a["n"]:
                continue
            a["maiores"].sort(key=lambda x: -x[4])
            temas[tid]["anos"][str(ano)] = {
                "p": round(a["p"], 2), "e": round(a["e"], 2), "n": a["n"], "pf": round(a["pf"], 2),
                "meses": [round(v, 2) for v in a["meses"]],
                "secretarias": [[s, round(v, 2)] for s, v in sorted(a["sec"].items(), key=lambda kv: -kv[1])[:8] if v > 0],
                "fornecedores": [[creds[i][0], creds[i][1], round(v[0], 2), v[1]] for i, v in sorted(a["forn"].items(), key=lambda kv: -kv[1][0])[:12] if v[0] > 0],
                "maiores": a["maiores"][:12],
            }
        # corrida de dezembro: só anos completos (dezembro já passou)
        hoje = dt.date.today()
        if ano < hoje.year or (ano == hoje.year and hoje.month == 12 and hoje.day > 20):
            outros = mes_tot[1:11]  # fevereiro a novembro (janeiro tem os empenhos do ano inteiro)
            med = statistics.median(outros) if any(outros) else 0
            lista = []
            for s, m in mes_sec.items():
                base = statistics.median(m[1:11])
                if m[11] >= 1_000_000 and m[11] > 2.5 * max(base, 1):
                    lista.append([s, round(m[11], 2), round(base, 2)])
            lista.sort(key=lambda x: -x[1])
            dezembro[str(ano)] = {"meses": [round(v, 2) for v in mes_tot], "mediana": round(med, 2), "dez": round(mes_tot[11], 2),
                                  "secretarias": lista[:10]}
        print(f"Lupa {ano}: " + ", ".join(f"{t} R$ {acc[t]['p'] / 1e6:.1f} mi ({acc[t]['n']})" for t in acc))
    SAIDA.write_text(json.dumps({
        "atualizado": dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M"),
        "anos": [str(a) for a in anos],
        "temas": list(temas.values()),
        "dezembro": dezembro,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for a, z in dezembro.items():
        print(f"Dezembro {a}: R$ {z['dez'] / 1e6:.1f} mi contra mediana de R$ {z['mediana'] / 1e6:.1f} mi; {len(z['secretarias'])} secretarias em disparada")


if __name__ == "__main__":
    main()
