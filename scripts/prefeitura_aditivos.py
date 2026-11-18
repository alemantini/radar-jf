"""Aditivos de contratos da Prefeitura, a partir dos extratos publicados no Diário Oficial.

Um termo aditivo muda um contrato já assinado: prorroga o prazo, reajusta o preço, aumenta ou
diminui a quantidade (a lei limita o acréscimo a 25% do valor, ou 50% em reforma) ou altera
outras condições. Prorrogar serviço contínuo e reajustar pela inflação são permitidos; muitos
aditivos seguidos ou acréscimos grandes merecem uma pergunta.

Fonte: data/cache/atos/ (resumos dos atos do Diário Oficial, de prefeitura_atos.py). O resumo
traz o número do contrato com o número do aditivo (01.2014.236/14 = 14º aditivo do contrato
01.2014.236), as partes, o objeto e, às vezes, o valor.

Saída: site/dados/prefeitura/aditivos.json
"""
import datetime as dt
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ATOS = RAIZ / "data" / "cache" / "atos"
SAIDA = RAIZ / "site" / "dados" / "prefeitura" / "aditivos.json"
LINK = "https://www.pjf.mg.gov.br/e_atos/e_atos_vis.php?id="


def sa(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn").lower()


def num(s):
    return float(s.replace(".", "").replace(",", "."))


PJ = re.compile(r"ltda|\bs\.?\s?a\.?(?:\s|$)|s/a|eireli|\bme\b|\bepp\b|empresa|companhia|associa|igreja|instituto|fundac|banco|caixa|"
                r"cooperativ|consorcio|engenharia|servic|comerci|uniao|ministerio|hospital|clinica|sociedade|condominio|imobiliari|"
                r"construc|universidade|municipio|estado de|governo|federacao|sindicato|paroquia|mitra|conselho|centro|escola|colegio|"
                r"agencia|autarquia|departamento|secretaria|tecnologia|sistemas|solucoes|industria|distribuid|transport|locac|gestao|grupo|holding|participac")


def empresa_ou_pessoa(nome):
    """Nunca publica nome de pessoa física (por exemplo, quem aluga um imóvel para a Prefeitura)."""
    if not nome:
        return ""
    return nome if PJ.search(sa(nome)) else "Pessoa física (nome não publicado pelo Radar)"


def tipo_aditivo(obj):
    t = sa(obj)
    tipos = []
    if re.search(r"quantitativ|acresc|acrescimo|supress|acrescid", t):
        tipos.append("Acréscimo ou supressão de quantidade")
    if re.search(r"reajust|repactua|reequilibr|realinhament", t):
        tipos.append("Reajuste de preço")
    if re.search(r"prorroga|renova|vigencia", t):
        tipos.append("Prorrogação de prazo")
    if not tipos:
        tipos.append("Outras alterações")
    return tipos


def ler():
    atos = []
    for f in sorted(ATOS.glob("20*.json")):
        atos += [a for a in json.loads(f.read_text(encoding="utf-8")).values()
                 if a.get("tipo") == "Extrato de Contrato" and "aditivo" in sa(a.get("texto"))]
    return sorted(atos, key=lambda a: (a["data"], a["id"]))


def interpretar(a):
    t = re.sub(r"\s+", " ", a.get("texto") or "")
    m = re.search(r"CONTRATO N[.º°o\s]*([\d]{2}\.\d{4}\.\d{3,4})(?:/(\d{1,3}))?", t, re.I)
    if not m:
        return None
    orgao = t.split("–")[0].split(" - ")[0].strip()[:30]
    emp = re.search(r"(?:CONTRATANTES|PARTES):\s*Munic[ií]pio de Juiz de Fora(?: e| –)\s*(.+?)\s*[–-]\s*(?:OBJETO|CNPJ)", t, re.I)
    obj = re.search(r"OBJETO:\s*(.+?)(?:\s*[–-]\s*(?:VALOR|A PARTIR|VIG[EÊ]NCIA|PRAZO|DOTA)|$)", t, re.I)
    v = re.search(r"VALOR(?: GLOBAL)?(?: ANUAL)?(?: ESTIMADO)?(?: TOTAL)?(?: DO ADITIVO)?:\s*R\$\s*([\d\.]+,\d{2})", t, re.I)
    vm = re.search(r"VALOR MENSAL:\s*R\$\s*([\d\.]+,\d{2})", t, re.I)
    objeto = obj.group(1).strip() if obj else ""
    return {"id": a["id"], "d": a["data"], "contrato": m.group(1), "seq": int(m.group(2)) if m.group(2) else None,
            "ano_contrato": int(m.group(1).split(".")[1]), "orgao": orgao, "empresa": empresa_ou_pessoa((emp.group(1).strip() if emp else "")[:90]),
            "objeto": objeto[:200], "tipos": tipo_aditivo(objeto or t),
            "valor": num(v.group(1)) if v else None, "mensal": num(vm.group(1)) if vm else None}


def main():
    itens = [x for x in (interpretar(a) for a in ler()) if x]
    por_contrato = defaultdict(list)
    for x in itens:
        por_contrato[x["contrato"]].append(x)
    contratos = []
    for c, xs in por_contrato.items():
        xs.sort(key=lambda x: (x["d"], x["seq"] or 0))
        ult = xs[-1]
        seqs = [x["seq"] for x in xs if x["seq"]]
        contratos.append({"contrato": c, "ano": ult["ano_contrato"], "empresa": next((x["empresa"] for x in reversed(xs) if x["empresa"]), ""),
                          "orgao": ult["orgao"], "objeto_ult": ult["objeto"], "aditivos_total": max(seqs) if seqs else len(xs),
                          "publicados": len(xs), "tipos": sorted({t for x in xs for t in x["tipos"]}),
                          "valor_ult": next((x["valor"] for x in reversed(xs) if x["valor"]), None),
                          "atos": [{"id": x["id"], "d": x["d"], "seq": x["seq"], "objeto": x["objeto"], "valor": x["valor"]} for x in xs[-6:]]})
    tipos = Counter(t for x in itens for t in x["tipos"])
    hoje = dt.date.today().year
    saida = {
        "atualizado": dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M"),
        "link_ato": LINK, "desde": itens[0]["d"] if itens else None, "ate": itens[-1]["d"] if itens else None,
        "n": len(itens), "n_contratos": len(contratos),
        "por_ano": dict(Counter(x["d"][:4] for x in itens)),
        "tipos": tipos.most_common(),
        "mais_aditivados": sorted(contratos, key=lambda c: (-c["aditivos_total"], c["ano"]))[:30],
        "mais_antigos": sorted((c for c in contratos if c["ano"] <= hoje - 5), key=lambda c: (c["ano"], -c["aditivos_total"]))[:30],
        "quantitativos": sorted(({k: x[k] for k in ("id", "d", "contrato", "seq", "empresa", "orgao", "objeto", "valor")}
                                 for x in itens if "Acréscimo ou supressão de quantidade" in x["tipos"]),
                                key=lambda x: x["d"], reverse=True)[:60],
        "por_empresa": [[e, n] for e, n in Counter(x["empresa"] for x in itens if x["empresa"] and not x["empresa"].startswith("Pessoa física")).most_common(20)],
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Aditivos: {len(itens)} termos em {len(contratos)} contratos; tipos {tipos.most_common()}")


if __name__ == "__main__":
    main()
