"""Monta data/prefeitura/comissionados.json a partir da planilha CSV baixada no
Portal da Transparência da Prefeitura (Servidores > PJF > pesquisar sem filtro >
CSV, com todos os servidores da competência).

Entram dois grupos de cargos de confiança:
  c = comissionados (vínculo "Comissionado", nomeados sem concurso);
  f = servidores concursados (efetivos ou celetistas) com a coluna "Função" preenchida
      (função de confiança: secretário, subsecretário, gerente etc.).
Prefeita e vice (vínculo próprio) não entram.

O portal bloqueia os robôs do GitHub, então as planilhas são baixadas à mão uma
vez por mês e passadas para este script:

    python3 tools/comissionados.py Servidores_*.csv
"""
import csv
import json
import sys
from datetime import date
from pathlib import Path

SAIDA = Path(__file__).resolve().parent.parent / "data" / "prefeitura" / "comissionados.json"

# Nomes só onde a sigla é conhecida com segurança; as demais aparecem como sigla.
SIGLAS = {
    "CGM": "Controladoria-Geral do Município",
    "PGM": "Procuradoria-Geral do Município",
    "MULHERES": "Secretaria das Mulheres",
    "SAS": "Secretaria de Assistência Social",
    "SDA": "Secretaria de Desenvolvimento Agrário",
    "SE": "Secretaria de Educação",
    "SE/FUND": "Secretaria de Educação, escolas de ensino fundamental",
    "SEBEAL": "Secretaria de Bem-Estar Animal",
    "SECOM": "Secretaria de Comunicação",
    "SEDH": "Secretaria de Direitos Humanos",
    "SEDIC": "Secretaria de Desenvolvimento Sustentável e Inclusivo, da Inovação e Competitividade",
    "SEDUPP": "Secretaria de Desenvolvimento Urbano com Participação Popular",
    "SEIR": "Secretaria de Igualdade Racial",
    "SEL": "Secretaria de Esporte e Lazer",
    "SELICON": "Secretaria de Licitações e Contratos",
    "SESUC": "Secretaria de Segurança Urbana e Cidadania",
    "SETUR": "Secretaria de Turismo",
    "SF": "Secretaria da Fazenda",
    "SG": "Secretaria de Governo",
    "SMA": "Secretaria de Meio Ambiente e Mudanças Climáticas",
    "SMU": "Secretaria de Mobilidade Urbana",
    "SO": "Secretaria de Obras",
    "SRH": "Secretaria de Recursos Humanos",
    "SS": "Secretaria de Saúde",
}


def valor(t):
    t = (t or "").strip()
    if t in ("", "-"):
        return 0.0
    return float(t.replace(".", "").replace(",", "."))


def main(arquivos):
    pessoas, competencias = {}, set()
    for arq in arquivos:
        nome = Path(arq).name
        m = __import__("re").search(r"(\d{2})(20\d{2})", nome)
        if m:
            competencias.add(m.group(1) + m.group(2))
        with open(arq, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f, delimiter=";"):
                vinc = r["Vínculo"].strip().upper()
                funcao = (r.get("Função") or "-").strip()
                if vinc == "COMISSIONADO":
                    tipo, posto, origem = "c", r["Cargo"].strip(), ""
                elif funcao not in ("", "-"):
                    tipo, posto, origem = "f", funcao, r["Cargo"].strip()
                else:
                    continue
                pessoas[r["Matrícula"]] = [
                    r["Nome"].strip(), posto, r["Lotação"].strip(), r["Admissão"].strip(),
                    round(valor(r["Cargo/Emprego(R$)"]), 2), round(valor(r["Total Bruto(R$)"]), 2),
                    tipo, origem, round(valor(r.get("Função Gratificada(R$)")), 2),
                ]
    comp = sorted(competencias)[-1] if competencias else ""
    lista = sorted(pessoas.values(), key=lambda p: (p[2], p[1], p[0]))
    out = {
        "competencia": f"{comp[:2]}/{comp[2:]}" if comp else "",
        "baixado_em": date.today().isoformat(),
        "colunas": ["nome", "cargo_ou_funcao", "lotacao", "admissao", "salario_cargo", "bruto_mes", "tipo", "cargo_de_origem", "funcao_gratificada"],
        "siglas": {k: v for k, v in SIGLAS.items() if any(p[2] == k for p in lista)},
        "pessoas": lista,
        "fonte": "Portal da Transparência da Prefeitura de Juiz de Fora, Servidores (PJF), todos os servidores da competência: vínculo Comissionado e servidores com função de confiança",
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{sum(p[6] == 'c' for p in lista)} comissionados e {sum(p[6] == 'f' for p in lista)} concursados em função, competência {out['competencia']} -> {SAIDA}")


if __name__ == "__main__":
    main(sys.argv[1:])
