"""Monta data/prefeitura/supersalarios.json a partir da mesma planilha de todos os
servidores usada em tools/comissionados.py (Portal da Transparência da Prefeitura).

    python3 tools/supersalarios.py servidores_pjf_MMAAAA.csv

Regras (art. 37, XI, da Constituição):
  - teto dos servidores do Município: subsídio da prefeita, lido na própria planilha;
  - procuradores municipais: 90,25% do subsídio de ministro do STF (STF, RE 663.696, Tema 510);
  - entram no teto: cargo/emprego, outras verbas permanentes, função gratificada e honorários
    (o STF reafirmou em 2026 que honorários da advocacia pública se sujeitam ao teto);
  - ficam fora: 13º, férias, abono de permanência, verbas temporárias e indenizações;
  - a "retenção por teto" que a Prefeitura já descontou é abatida;
  - como as parcelas da planilha nem sempre somam o bruto, usa-se o menor valor entre a soma
    das parcelas permanentes e o bruto sem 13º, férias, abono e verbas temporárias.
Cada linha da planilha é uma matrícula; em acumulação lícita o teto vale para cada vínculo.
"""
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

SAIDA = Path(__file__).resolve().parent.parent / "data" / "prefeitura" / "supersalarios.json"
STF = 46366.19
TETO_PROCURADOR = round(STF * 0.9025, 2)


def valor(t):
    t = (t or "").strip()
    return 0.0 if t in ("", "-") else float(t.replace(".", "").replace(",", "."))


def main(arq):
    rows = list(csv.DictReader(open(arq, encoding="utf-8-sig"), delimiter=";"))
    pref = next(r for r in rows if r["Cargo"].strip() == "PREFEITO")
    teto = valor(pref["Cargo/Emprego(R$)"])
    m = re.search(r"(\d{2})(20\d{2})", Path(arq).name)
    acima, maiores, com_ret = [], [], 0
    for r in rows:
        if r["Cargo"].strip() in ("PREFEITO", "VICE-PREFEITO"):
            continue
        cargo = r["Cargo"].strip()
        partes = {k: valor(r[k + "(R$)"]) for k in ("Cargo/Emprego", "Outras Verbas de Natureza Permanente", "Função Gratificada", "Honorários")}
        perm = sum(partes.values())
        ret = valor(r["Retenção por Teto Constitucional(R$)"])
        bruto = valor(r["Total Bruto(R$)"])
        fora = sum(valor(r[k + "(R$)"]) for k in ("Décimo Terceiro", "Férias", "Abono Permanência", "Outras Verbas de Natureza Temporária"))
        # As parcelas da planilha nem sempre somam o bruto (em boa parte das linhas não batem).
        # Conta conservadora: o menor entre a soma das parcelas permanentes e o bruto sem 13º, férias, abono e temporárias.
        perm = min(perm, max(bruto - fora, 0))
        if ret > 0:
            com_ret += 1
        lim = TETO_PROCURADOR if cargo.startswith("PROCURADOR MUNICIPAL") else teto
        func = (r.get("Função") or "-").strip()
        base = [r["Nome"].strip(), cargo, "" if func == "-" else func, r["Vínculo"].strip(), r["Lotação"].strip()]
        if perm - ret > lim + 0.01:
            acima.append(base + [round(partes["Cargo/Emprego"], 2), round(partes["Outras Verbas de Natureza Permanente"], 2),
                                 round(partes["Função Gratificada"], 2), round(partes["Honorários"], 2), round(ret, 2),
                                 round(perm - ret, 2), lim, round(perm - ret - lim, 2), round(bruto, 2)])
        maiores.append(base + [round(bruto, 2), round(max(perm - ret, 0), 2), round(valor(r["Remuneração Líquida(R$)"]), 2)])
    acima.sort(key=lambda x: -x[-2])
    maiores.sort(key=lambda x: -x[5])
    out = {
        "competencia": f"{m.group(1)}/{m.group(2)}" if m else "",
        "baixado_em": date.today().isoformat(),
        "teto": teto, "teto_procurador": TETO_PROCURADOR, "stf": STF,
        "servidores": len(rows), "com_retencao": com_ret,
        "acima_cols": ["nome", "cargo", "funcao", "vinculo", "lotacao", "cargo_emprego", "permanentes", "funcao_gratificada",
                       "honorarios", "retencao", "sujeito_ao_teto", "teto_aplicado", "excesso", "bruto"],
        "acima": acima,
        "maiores_cols": ["nome", "cargo", "funcao", "vinculo", "lotacao", "bruto", "sujeito_ao_teto", "liquido"],
        "maiores": maiores[:50],
        "fonte": "Portal da Transparência da Prefeitura de Juiz de Fora, Servidores (PJF), planilha de todos os servidores da competência",
    }
    SAIDA.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"teto R$ {teto:,.2f}; {len(acima)} acima do teto; {com_ret} com retenção; maior bruto R$ {maiores[0][5]:,.2f}")
    for a in acima:
        print(" ", a[0][:30], "|", a[1][:28], "|", a[4], "| sujeito", a[10], "teto", a[11], "excesso", a[12])


if __name__ == "__main__":
    main(sys.argv[1])
