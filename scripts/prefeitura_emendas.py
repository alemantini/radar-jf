"""Emendas parlamentares municipais (dos vereadores) e em que etapa estão.

Fonte oficial: Monitor de Emendas Parlamentares da Prefeitura de Juiz de Fora
(https://www.pjf.mg.gov.br/transparencia/emendas/index.php). O painel lê uma planilha publicada
pela Prefeitura em CSV; o robô lê a mesma planilha.

Saída:
  site/dados/prefeitura/emendas_resumo.json  totais por vereador (pequeno, usado nos crachás)
  site/dados/prefeitura/emendas.json         lista das emendas (para a página de emendas)
Não publica dados bancários, nem nome de gestor ou de pessoa física.
"""
import csv
import datetime as dt
import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import requests

PAINEL = "https://diegorrpessoa.github.io/cgm/emendas.html"
CSV_PADRAO = ("https://docs.google.com/spreadsheets/d/e/2PACX-1vTkqC4aoZJcALRrSITEjr57Qk8D7-my9cguXVZLbVLZcP0hA3yFWKph6sOSQl30zDO8Z-XmN5TyLJG3"
              "/pub?output=csv")
UA = "RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"
SAIDA = Path(__file__).resolve().parent.parent / "site" / "dados" / "prefeitura"
ANO_INICIAL = 2025

# etapas oficiais agrupadas em poucas palavras simples (a etapa oficial também é publicada)
ETAPAS = [
    ("Executada", r"^EXECUTADA$"),
    ("Pagamento", r"PAGAMENTO|LIQUIDA"),
    ("Em execução", r"EXECU|CONTRATAD|LICITA|FORMALIZ|EMPENHO"),
    ("Inapta", r"INAPT"),
    ("Em análise", r"AN[AÁ]LISE|INPUT|\bPT\b|OSC|ALTERA"),
]


def etapa(s):
    s = (s or "").strip()
    for nome, rx in ETAPAS:
        if re.search(rx, s, re.I):
            return nome
    return "Não informado"


def numero(v):
    s = re.sub(r"[^\d,.\-]", "", str(v or ""))
    if not s or s in "-.,":
        return 0.0
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def url_planilha():
    try:
        html = requests.get(PAINEL, headers={"User-Agent": UA}, timeout=60).text
        m = re.search(r"https://docs\.google\.com/spreadsheets/[^\"'`\s]+", html)
        if m:
            return m.group(0)
    except requests.RequestException:
        pass
    return CSV_PADRAO


def limpa(s, n=None):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s[:n] if n else s


def main():
    url = url_planilha()
    r = requests.get(url, headers={"User-Agent": UA}, timeout=180)
    if r.status_code != 200 or len(r.content) < 10000:
        print(f"Emendas: download falhou (HTTP {r.status_code})")
        sys.exit(1)
    linhas = list(csv.DictReader(io.StringIO(r.content.decode("utf-8", "replace"))))
    if not linhas or "Proponente" not in linhas[0]:
        print("Emendas: planilha sem o formato esperado")
        sys.exit(1)
    atualizado = next((limpa(x.get("Atualizacao")) for x in linhas if limpa(x.get("Atualizacao"))), "")

    emendas = []
    por = defaultdict(lambda: {"previsto": 0.0, "pago": 0.0, "n": 0, "etapas": Counter()})
    total = {"previsto": 0.0, "pago": 0.0, "n": 0}
    etapas_total = Counter()
    for x in linhas:
        try:
            ano = int(limpa(x.get("Ano")))
        except ValueError:
            continue
        if ano < ANO_INICIAL or not re.search(r"munic", x.get("Origem dos recursos") or "", re.I):
            continue
        prop = limpa(x.get("Proponente")) or "Não informado"
        prev, pago = numero(x.get("Valor alocado/previsto")), numero(x.get("Valor Pago"))
        sit = limpa(x.get("Situação administrativa")) or "Não informado"
        et = etapa(sit)
        emendas.append({
            "ano": ano, "p": prop, "id": limpa(x.get("Identificação da Emenda")),
            "obj": limpa(x.get("Objeto da Despesa"), 300),
            "benef": limpa(x.get("Órgão ou entidade executora ou beneficiária"), 120),
            "cnpj": re.sub(r"\D", "", x.get("CNPJ do Órgão ou entidade executora ou beneficiária") or "")[:14],
            "ug": limpa(x.get("Unidade Gestora"), 80),
            "local": limpa(x.get("Localidade beneficiada"), 80),
            "funcao": limpa(x.get("Função de Governo Função programática"), 60),
            "prev": round(prev, 2), "pago": round(pago, 2), "sit": sit, "et": et,
        })
        P = por[prop]
        P["previsto"] += prev
        P["pago"] += pago
        P["n"] += 1
        P["etapas"][et] += 1
        total["previsto"] += prev
        total["pago"] += pago
        total["n"] += 1
        etapas_total[et] += 1

    if total["n"] < 100:
        print(f"Emendas: só {total['n']} emendas municipais desde {ANO_INICIAL}; não publica")
        sys.exit(1)

    resumo = {
        "fonte": "Monitor de Emendas Parlamentares, Prefeitura de Juiz de Fora",
        "fonte_url": "https://www.pjf.mg.gov.br/transparencia/emendas/index.php",
        "atualizado_fonte": atualizado,
        "coletado_em": dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M"),
        "desde": ANO_INICIAL,
        "total": {k: round(v, 2) for k, v in total.items()},
        "etapas": dict(etapas_total.most_common()),
        "proponentes": {p: {"previsto": round(v["previsto"], 2), "pago": round(v["pago"], 2), "n": v["n"],
                            "etapas": dict(v["etapas"])} for p, v in por.items()},
    }
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "emendas_resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, separators=(",", ":")))
    (SAIDA / "emendas.json").write_text(json.dumps(emendas, ensure_ascii=False, separators=(",", ":")))
    print(f"OK emendas: {total['n']} desde {ANO_INICIAL}, previsto R$ {total['previsto']/1e6:.1f} mi, "
          f"pago R$ {total['pago']/1e6:.1f} mi, {len(por)} proponentes; etapas {dict(etapas_total)}")


if __name__ == "__main__":
    main()
