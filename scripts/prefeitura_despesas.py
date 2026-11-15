"""Prefeitura de Juiz de Fora: para onde vai o dinheiro.

Fonte: arquivos oficiais de despesas do Portal da Transparência da PJF
https://www.pjf.mg.gov.br/transparencia/dados_abertos/arquivos.php
(um arquivo por ano, atualizado semanalmente pela Prefeitura).

Saída em site/dados/prefeitura/:
  resumo.json          totais por ano, por secretaria, por mês, maiores fornecedores
  empenhos_AAAA.json   lista de empenhos para a busca (pessoas físicas sem nome)

Privacidade: credor identificado por CPF ou código "PF" é pessoa física. O site nunca
mostra nome, CPF nem o histórico desses pagamentos; eles aparecem somados.
Se o download vier incompleto ou estranho, o script termina com erro.
"""
import datetime as dt
import json
import os
import re
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path

import requests

BASE = "https://www.pjf.mg.gov.br/transparencia/dados_abertos"
UA = ("RadarJF/1.0 (robo de transparencia, coleta 1x por dia; "
      "codigo aberto em https://github.com/alemantini/radar-jf)")
RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "site" / "dados" / "prefeitura"
CONTAGEM = RAIZ / "data" / "bruto" / "prefeitura_contagem.json"
ANOS = [int(a) for a in os.environ.get("RADAR_ANOS_PREFEITURA", "2025,2026").split(",")]

MESES = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
         "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}
PREPOSICOES = {"de", "da", "do", "das", "dos", "e", "a", "o", "em", "para", "com"}
SIGLAS = {"sus", "ubs", "cesama", "emcasa", "funalfa", "procon", "demlurb", "settra", "pjf",
          "jf", "jfprev", "amac", "empav", "ii", "iii", "iv", "ltda", "me", "epp", "sa", "s/a", "eireli"}


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def titulo(s):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    out = []
    for i, p in enumerate(s.split(" ")):
        lp = p.lower()
        if lp in SIGLAS:
            out.append(p.upper())
        elif i and lp in PREPOSICOES:
            out.append(lp)
        else:
            out.append(lp[:1].upper() + lp[1:])
    return " ".join(out)


ACENTOS = {w.lower().replace("ç", "c").replace("ã", "a").replace("õ", "o").replace("á", "a").replace("é", "e")
           .replace("í", "i").replace("ó", "o").replace("ú", "u").replace("â", "a").replace("ê", "e").replace("ô", "o"): w
           for w in """Saúde Educação Pública Público Públicas Públicos Comunicação Câmara Serviços Instalações Aquisição
           Administração Assistência Segurança Fundação Habitação Trânsito Agropecuária Previdência Inclusão Inovação
           Participação Gestão Jurídica Jurídicas Informação Informações Diárias Física Físicas Contribuições Subvenções Exercícios
           Indenizações Restituições Obrigações Tributárias Auxílio Auxílios Alimentação Locação Previdenciárias Sentenças
           Judiciais Distribuição Gratuita Premiações Artísticas Científicas Desportivas Econômica Econômico Patrimônio
           Transformação Manutenção Conservação Execução Infraestrutura Mobilidade Urbanística Proteção Defesa Civil
           Políticas Mulher Família Assistência Social Esportes Câmaras Órgãos Órgão Município Municipal Técnica Técnico
           Fiscalização Contratação Contratações Remuneração Vantagens Benefícios Financeiras Transferências Consórcios
           Cooperação Convênios Empréstimos Amortização Dívida Juros Aplicações Diretas Indiretas Instituições Privadas
           Autarquia Autarquias Fundações Coordenação Superintendência Regulação Urgência Emergência Atenção Básica
           Vigilância Epidemiológica Ambiental Ação Ações Comunitária Sustentável Agrário Competitividade Fazenda
           Planejamento Controladoria Procuradoria Geral Governo Turismo Cultura Lazer Obras Esporte
           Pensões Variáveis Previdência Indenização Contratação Vencimentos Responsabilidade Patronal""".split()}


def acentuar(s):
    return " ".join(ACENTOS.get(p.lower(), p) if p.lower() in ACENTOS else p for p in s.split(" "))


def numero(v):
    """Aceita 117134.26, 117,134.26, -1,234.50 e também 1.234,56."""
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d,.\-]", "", str(v or ""))
    if not s or s in "-.,":
        return 0.0
    if "," in s and "." in s:
        if s.rfind(".") > s.rfind(","):
            s = s.replace(",", "")
        else:
            s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        partes = s.split(",")
        s = s.replace(",", ".") if len(partes) == 2 and len(partes[1]) <= 2 else s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def data_iso(v):
    m = re.match(r"^\s*(\d{1,2})/(\d{1,2})/(\d{2,4})\s*$", str(v or ""))
    if not m:
        return ""
    a, b, ano = int(m.group(1)), int(m.group(2)), int(m.group(3))
    ano = ano + 2000 if ano < 100 else ano
    mes, dia = (a, b) if a <= 12 else (b, a)  # o arquivo usa mês/dia/ano
    try:
        return dt.date(ano, mes, dia).isoformat()
    except ValueError:
        return ""


def mes_num(v):
    k = sem_acento(str(v or "")).lower()[:3]
    return MESES.get(k, 0)


def tipo_credor(doc):
    d = str(doc or "").strip()
    digitos = re.sub(r"\D", "", d)
    if d.upper().startswith("PF") or len(digitos) == 11:
        return "pf", ""
    if len(digitos) == 14:
        return "pj", digitos
    return "outro", digitos


def baixar(url, tentativas=4):
    for i in range(tentativas):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=600)
            if r.status_code == 200 and len(r.content) > 1000:
                return r.content
            print(f"  HTTP {r.status_code} ({len(r.content)} bytes) em {url}", file=sys.stderr)
        except requests.RequestException as e:
            print(f"  erro {e} em {url}", file=sys.stderr)
        time.sleep(15 * (i + 1))
    raise RuntimeError(f"Falha ao baixar {url}")


def data_atualizacao_fonte():
    try:
        html = baixar(f"{BASE}/arquivos.php", tentativas=2).decode("utf-8", "replace")
        m = re.search(r"Atualizado em:\s*([\d/]+)", html)
        return m.group(1) if m else ""
    except RuntimeError:
        return ""


def processar_ano(ano, registros):
    total = {"e": 0.0, "l": 0.0, "p": 0.0}
    unidades = defaultdict(lambda: {"e": 0.0, "l": 0.0, "p": 0.0, "n": 0,
                                    "meses": defaultdict(float), "cred": defaultdict(lambda: [0.0, 0.0, 0]),
                                    "elem": defaultdict(float), "categoria": ""})
    credores = {}  # cnpj -> nome
    cred_total = defaultdict(lambda: {"e": 0.0, "p": 0.0, "n": 0, "u": defaultdict(float)})
    pf = {"e": 0.0, "p": 0.0, "n": 0}
    pf_elem = defaultdict(float)
    empenhos = []
    nomes_u, idx_u = [], {}
    nomes_el, idx_el = [], {}
    lista_c, idx_c = [], {}

    def idx(lista, mapa, chave):
        if chave not in mapa:
            mapa[chave] = len(lista)
            lista.append(chave)
        return mapa[chave]

    for x in registros:
        e, l, p = numero(x.get("empenhado")), numero(x.get("liquidado")), numero(x.get("pago"))
        u = acentuar(titulo(x.get("unidade orcamentaria") or "Não informado"))
        el = acentuar(titulo(x.get("nome elemento de despesa orcamentaria") or x.get("nome natureza de despesa com subelemento") or ""))
        mes = mes_num(x.get("mes"))
        tipo, cnpj = tipo_credor(x.get("cpf/cnpj"))
        for k, v in (("e", e), ("l", l), ("p", p)):
            total[k] += v
            unidades[u][k] += v
        U = unidades[u]
        U["n"] += 1
        U["categoria"] = acentuar(titulo(x.get("categoria") or "")) if x.get("categoria") not in (None, "#N/A") else U["categoria"]
        if mes:
            U["meses"][mes] += p
        if el:
            U["elem"][el] += p
        if tipo == "pj":
            nome = titulo(x.get("nome do credor") or "")
            credores.setdefault(cnpj, nome)
            ct = cred_total[cnpj]
            ct["e"] += e
            ct["p"] += p
            ct["n"] += 1
            ct["u"][u] += p
            uc = U["cred"][cnpj]
            uc[0] += p
            uc[1] += e
            uc[2] += 1
            ic = idx(lista_c, idx_c, cnpj)
            hist = re.sub(r"\s+", " ", str(x.get("historico") or "")).strip()[:160]
        else:
            pf["e"] += e
            pf["p"] += p
            pf["n"] += 1
            pf_elem[el] += p
            ic = -1
            hist = ""  # nunca publicar texto de pagamento a pessoa física
        empenhos.append([
            data_iso(x.get("data do empenho")),
            idx(nomes_u, idx_u, u),
            ic,
            idx(nomes_el, idx_el, el),
            round(e, 2),
            round(p, 2),
            hist,
            str(x.get("nº do empenho") or "").strip(),
        ])

    def r2(d):
        return {k: round(v, 2) for k, v in d.items()}

    lista_u = []
    for nome, U in unidades.items():
        top_c = sorted(U["cred"].items(), key=lambda kv: -kv[1][0])[:25]
        lista_u.append({
            "nome": nome,
            "categoria": U["categoria"],
            "e": round(U["e"], 2), "l": round(U["l"], 2), "p": round(U["p"], 2), "n": U["n"],
            "meses": [round(U["meses"].get(m, 0.0), 2) for m in range(1, 13)],
            "fornecedores": [{"cnpj": c, "nome": credores[c], "p": round(v[0], 2), "e": round(v[1], 2), "n": v[2]} for c, v in top_c],
            "elementos": [{"nome": n, "p": round(v, 2)} for n, v in sorted(U["elem"].items(), key=lambda kv: -kv[1])[:12]],
        })
    lista_u.sort(key=lambda u: -u["p"])
    top_cred = sorted(cred_total.items(), key=lambda kv: -kv[1]["p"])[:200]
    resumo = {
        "total": r2(total),
        "n": len(registros),
        "secretarias": lista_u,
        "fornecedores": [{"cnpj": c, "nome": credores[c], "p": round(v["p"], 2), "e": round(v["e"], 2), "n": v["n"],
                          "secretarias": [n for n, _ in sorted(v["u"].items(), key=lambda kv: -kv[1])[:4]]}
                         for c, v in top_cred],
        "n_fornecedores": len(cred_total),
        "pessoa_fisica": r2(pf) | {"n": pf["n"], "elementos": [{"nome": n, "p": round(v, 2)} for n, v in sorted(pf_elem.items(), key=lambda kv: -kv[1])[:8]]},
    }
    busca = {
        "ano": ano,
        "secretarias": nomes_u,
        "elementos": nomes_el,
        "credores": [[c, credores[c]] for c in lista_c],
        "campos": ["data", "secretaria", "credor", "elemento", "empenhado", "pago", "historico", "numero"],
        "empenhos": empenhos,
    }
    return resumo, busca


SITE_PUBLICADO = "https://jflandia.com.br/dados/prefeitura/resumo.json"
ANTERIOR = "/tmp/anterior/dados/prefeitura/resumo.json"  # baixado por tools/versao_anterior.sh


def precisa_baixar():
    """Só baixa os arquivos grandes quando a Prefeitura publicou uma versão nova.
    Se não der para confirmar, não baixa (o site fica com a última versão boa)."""
    if os.environ.get("RADAR_FORCAR_PREFEITURA") == "1":
        return True, "forçado"
    nova = data_atualizacao_fonte()
    if not nova:
        return False, "não consegui ler a data de atualização na página da Prefeitura"
    try:
        if os.path.exists(ANTERIOR):
            with open(ANTERIOR, encoding="utf-8") as f:
                publicada = json.load(f).get("fonte_atualizada_em", "")
        else:
            r = requests.get(SITE_PUBLICADO, headers={"User-Agent": UA}, timeout=60)
            publicada = r.json().get("fonte_atualizada_em", "") if r.status_code == 200 else ""
    except (requests.RequestException, ValueError):
        publicada = ""
    if publicada == nova:
        return False, f"sem novidade: a Prefeitura não atualizou desde {nova}"
    return True, f"versão nova na Prefeitura ({nova}; publicada no site: {publicada or 'nenhuma'})"


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    baixa, motivo = precisa_baixar()
    print("Prefeitura:", motivo)
    if not baixa:
        return  # sem arquivos novos: o workflow reaproveita a última versão publicada
    anterior = json.loads(CONTAGEM.read_text()) if CONTAGEM.exists() else {}
    contagem, anos_resumo, problemas = {}, {}, []
    for ano in ANOS:
        aa = str(ano)[-2:]
        conteudo = baixar(f"{BASE}/arquivos/despesas_{aa}.json")
        dados = json.loads(conteudo.decode("utf-8", "replace"))
        registros = dados if isinstance(dados, list) else next(v for v in dados.values() if isinstance(v, list))
        n = len(registros)
        contagem[str(ano)] = n
        print(f"{ano}: {n} empenhos ({len(conteudo) / 1e6:.0f} MB)")
        if n_ant := anterior.get(str(ano)):
            if n < 0.9 * n_ant:
                problemas.append(f"{ano}: caiu de {n_ant} para {n} registros")
        if n == 0 or "empenhado" not in registros[0]:
            problemas.append(f"{ano}: arquivo sem o formato esperado")
            continue
        resumo, busca = processar_ano(ano, registros)
        anos_resumo[str(ano)] = resumo
        (SAIDA / f"empenhos_{ano}.json").write_text(json.dumps(busca, ensure_ascii=False, separators=(",", ":")))
        t = resumo["total"]
        print(f"  empenhado R$ {t['e']/1e9:.2f} bi | liquidado R$ {t['l']/1e9:.2f} bi | pago R$ {t['p']/1e9:.2f} bi | "
              f"{len(resumo['secretarias'])} unidades | {resumo['n_fornecedores']} empresas")
    if problemas:
        print("COLETA DA PREFEITURA REJEITADA:")
        for p in problemas:
            print(" -", p)
        sys.exit(1)
    resumo = {
        "fonte": f"{BASE}/arquivos.php",
        "fonte_atualizada_em": data_atualizacao_fonte(),
        "coletado_em": dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M"),
        "anos": anos_resumo,
    }
    (SAIDA / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, separators=(",", ":")))
    CONTAGEM.parent.mkdir(parents=True, exist_ok=True)
    CONTAGEM.write_text(json.dumps(contagem, indent=1))
    print("OK prefeitura")


if __name__ == "__main__":
    main()
