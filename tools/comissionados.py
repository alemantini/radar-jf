"""Monta data/prefeitura/comissionados.json a partir das planilhas CSV baixadas
no Portal da Transparência da Prefeitura (Servidores > PJF > pesquisa por cargo
> "Gerar CSV com todos resultados").

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
    pessoas, competencias, cargos_buscados = {}, set(), set()
    for arq in arquivos:
        nome = Path(arq).name
        if "_" in nome:
            competencias.add(nome.split("_")[1][:6])
        with open(arq, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f, delimiter=";"):
                cargos_buscados.add(r["Cargo"].split()[0])
                if r["Vínculo"].strip().upper() != "COMISSIONADO":
                    continue
                pessoas[r["Matrícula"]] = [
                    r["Nome"].strip(),
                    r["Cargo"].strip(),
                    r["Lotação"].strip(),
                    r["Admissão"].strip(),
                    round(valor(r["Cargo/Emprego(R$)"]), 2),
                    round(valor(r["Total Bruto(R$)"]), 2),
                ]
    comp = sorted(competencias)[-1] if competencias else ""
    lista = sorted(pessoas.values(), key=lambda p: (p[2], p[1], p[0]))
    out = {
        "competencia": f"{comp[:2]}/{comp[2:]}" if comp else "",
        "baixado_em": date.today().isoformat(),
        "colunas": ["nome", "cargo", "lotacao", "admissao", "salario_cargo", "bruto_mes"],
        "siglas": {k: v for k, v in SIGLAS.items() if any(p[2] == k for p in lista)},
        "pessoas": lista,
        "fonte": "Portal da Transparência da Prefeitura de Juiz de Fora, Servidores (PJF), vínculo Comissionado",
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(lista)} comissionados, competência {out['competencia']} -> {SAIDA}")


if __name__ == "__main__":
    main(sys.argv[1:])
