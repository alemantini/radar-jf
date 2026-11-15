"""Eleição de 2024 dos vereadores: votos, gastos de campanha, origem do dinheiro e patrimônio declarado.

Fonte oficial: Portal de Dados Abertos do TSE (cdn.tse.jus.br/estatistica/sead/odsele).
  consulta_cand 2024 e 2020: candidaturas (liga 2020 e 2024 pelo título de eleitor).
  votacao_candidato_munzona 2024: votos por zona.
  prestacao_contas 2024: despesas contratadas e receitas declaradas pelos candidatos.
  bem_candidato 2024 e 2020: bens declarados.

O site grava só totais por vereador (sem a lista de bens, doadores ou fornecedores).
Como esses dados quase não mudam, o script roda sob demanda (workflow "TSE").

Saída: data/tse.json (copiado para site/dados pelo robô diário)
"""
import csv
import datetime as dt
import io
import json
import re
import shutil
import sys
import tempfile
import unicodedata
import zipfile
from collections import defaultdict
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
CDN = "https://cdn.tse.jus.br/estatistica/sead/odsele/"
UA = {"User-Agent": "RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
UE = "47333"  # código do TSE para Juiz de Fora
SAIDA = RAIZ / "data" / "tse.json"  # o robô diário copia para site/dados
csv.field_size_limit(10_000_000)


def chave(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def num(s):
    try:
        return float((s or "0").replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0


def baixar(caminho):
    tmp = Path(tempfile.gettempdir()) / caminho.split("/")[-1]
    if not tmp.exists():
        print("baixando", caminho)
        with requests.get(CDN + caminho, headers=UA, timeout=1800, stream=True) as r:
            r.raise_for_status()
            with open(tmp, "wb") as f:
                shutil.copyfileobj(r.raw, f, 1 << 20)
    return zipfile.ZipFile(tmp)


def linhas(z, parte):
    nome = next(i.filename for i in z.infolist() if i.filename.endswith(parte))
    with z.open(nome) as fh:
        rd = csv.reader(io.TextIOWrapper(fh, encoding="latin-1"), delimiter=";")
        cab = next(rd)
        for row in rd:
            yield dict(zip(cab, row))


def origem(d):
    o = (d.get("DS_ORIGEM_RECEITA") or "").lower()
    f = (d.get("DS_FONTE_RECEITA") or "").lower()
    if "fundo especial" in f or "fefc" in f or "fundo especial" in o:
        return "fundo_eleitoral"
    if "fundo partid" in f or "fundo partid" in o:
        return "fundo_partidario"
    if "próprios" in o or "proprios" in o:
        return "proprios"
    if "pessoas f" in o:
        return "pessoas_fisicas"
    if "partido" in o or "candidato" in o:
        return "partido_e_outros_candidatos"
    return "outros"


def main():
    vereadores = json.loads((RAIZ / "data" / "bruto" / "vereadores.json").read_text())

    # candidaturas a vereador em JF, 2024
    cand = {}
    for d in linhas(baixar("consulta_cand/consulta_cand_2024.zip"), "_MG.csv"):
        if d["SG_UE"] == UE and d["CD_CARGO"] == "13":
            cand[d["SQ_CANDIDATO"]] = d
    print("candidaturas 2024:", len(cand))

    def achar(v):
        cv = chave(v["nome"])
        for sq, d in cand.items():
            if chave(d["NM_CANDIDATO"]) == cv:
                return sq
        cands = [sq for sq, d in cand.items() if cv and (cv in chave(d["NM_CANDIDATO"]) or chave(d["NM_CANDIDATO"]) in cv)]
        if len(cands) == 1:
            return cands[0]
        ca = chave(v["apelido"])
        cands = [sq for sq, d in cand.items() if ca and chave(d["NM_URNA_CANDIDATO"]) == ca]
        return cands[0] if len(cands) == 1 else None

    alvo = {}
    for v in vereadores:
        sq = achar(v)
        if sq:
            alvo[sq] = v["id"]
        else:
            print("  sem candidatura encontrada:", v["apelido"])
    print("vereadores ligados:", len(alvo))

    votos = defaultdict(int)
    for d in linhas(baixar("votacao_candidato_munzona/votacao_candidato_munzona_2024.zip"), "_MG.csv"):
        if d["SG_UE"] == UE and d["SQ_CANDIDATO"] in alvo:
            votos[d["SQ_CANDIDATO"]] += int(d.get("QT_VOTOS_NOMINAIS_VALIDOS") or d.get("QT_VOTOS_NOMINAIS") or 0)

    z = baixar("prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2024.zip")
    gasto = defaultdict(float)
    for d in linhas(z, "despesas_contratadas_candidatos_2024_MG.csv"):
        if d["SG_UE"] == UE and d["SQ_CANDIDATO"] in alvo:
            gasto[d["SQ_CANDIDATO"]] += num(d["VR_DESPESA_CONTRATADA"])
    receita = defaultdict(lambda: defaultdict(float))
    for d in linhas(z, "receitas_candidatos_2024_MG.csv"):
        if d["SG_UE"] == UE and d["SQ_CANDIDATO"] in alvo:
            receita[d["SQ_CANDIDATO"]][origem(d)] += num(d["VR_RECEITA"])

    bens24 = defaultdict(float)
    for d in linhas(baixar("bem_candidato/bem_candidato_2024.zip"), "_MG.csv"):
        if d["SG_UE"] == UE and d["SQ_CANDIDATO"] in alvo:
            bens24[d["SQ_CANDIDATO"]] += num(d["VR_BEM_CANDIDATO"])

    # 2020: liga pelo título de eleitor
    titulo = {cand[sq]["NR_TITULO_ELEITORAL_CANDIDATO"]: sq for sq in alvo}
    sq20 = {}
    for d in linhas(baixar("consulta_cand/consulta_cand_2020.zip"), "_MG.csv"):
        t = d.get("NR_TITULO_ELEITORAL_CANDIDATO")
        if t in titulo and d.get("NR_TURNO", "1") == "1":
            sq20[d["SQ_CANDIDATO"]] = (titulo[t], d.get("DS_CARGO", ""), d.get("DS_SIT_TOT_TURNO", ""))
    bens20 = defaultdict(float)
    tem20 = {}
    for d in linhas(baixar("bem_candidato/bem_candidato_2020.zip"), "_MG.csv"):
        if d["SQ_CANDIDATO"] in sq20:
            sq24 = sq20[d["SQ_CANDIDATO"]][0]
            bens20[sq24] += num(d["VR_BEM_CANDIDATO"])
    for s20, (sq24, cargo, sit) in sq20.items():
        tem20[sq24] = {"cargo": cargo.title(), "resultado": sit.title()}

    out = {}
    for sq, vid in alvo.items():
        d = cand[sq]
        r = receita.get(sq, {})
        out[str(vid)] = {
            "urna": d["NM_URNA_CANDIDATO"], "partido_2024": d["SG_PARTIDO"],
            "resultado": d.get("DS_SIT_TOT_TURNO", "").title(),
            "votos": votos.get(sq, 0),
            "gasto": round(gasto.get(sq, 0), 2),
            "receita": round(sum(r.values()), 2),
            "origem": {k: round(x, 2) for k, x in r.items() if x},
            "bens_2024": round(bens24.get(sq, 0), 2),
            "eleicao_2020": ({**tem20[sq], "bens": round(bens20.get(sq, 0), 2)} if sq in tem20 else None),
        }
    res = {"fonte": "Tribunal Superior Eleitoral, Portal de Dados Abertos",
           "fonte_url": "https://dadosabertos.tse.jus.br/",
           "coletado_em": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
           "vereadores": out}
    if len(out) < 15:
        print("TSE: poucos vereadores ligados, não gravo")
        sys.exit(1)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for vid, x in out.items():
        print(" ", x["urna"], x["votos"], "votos, gasto", x["gasto"], "bens", x["bens_2024"], "2020:", x["eleicao_2020"])


if __name__ == "__main__":
    main()
