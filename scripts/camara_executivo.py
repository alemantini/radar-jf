"""Com a prefeita ou contra? Votos dos vereadores nos projetos enviados pelo Executivo.

Lê o texto das atas guardado em data/cache/atas/AAAA.jsonl.gz (coletado por camara_atas.py)
e, para cada votação de projeto enviado por "Mensagem do Executivo", registra quem votou
contra ou se absteve, pelo nome escrito na ata. Gera site/dados/executivo.json.

Limites (aparecem na página):
  - As atas não trazem a lista de presença de cada votação. "Unanimidade dos presentes"
    quer dizer que ninguém presente votou contra; o vereador pode ter estado ausente.
    Por isso a página conta votos CONTRÁRIOS, que são registrados com nome.
  - Vetos, emendas e pedidos de vista não entram.
"""
import datetime as dt
import gzip
import json
import re
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "data" / "cache" / "atas"
VEREADORES = RAIZ / "data" / "bruto" / "vereadores.json"
SAIDA = RAIZ / "site" / "dados" / "executivo.json"
ANOS = range(2025, dt.date.today().year + 1)  # legislatura atual
ATA = "https://www.camarajf.mg.gov.br/sal/ata.php?cod={}"


def sa(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[\s ​]+", " ", s)


def main():
    V = json.load(open(VEREADORES, encoding="utf-8"))
    ident = {}
    for v in V:
        for k in {v["apelido"], v["nome"]}:
            ident[sa(k)] = v["id"]
    ident.setdefault("andre luiz", next((v["id"] for v in V if v["apelido"].startswith("André Luiz")), None))
    chaves = sorted((k for k in ident if ident[k]), key=len, reverse=True)

    def acha(trecho):
        s, r = sa(trecho), []
        for k in chaves:
            p = r"\b" + re.escape(k) + r"\b"
            if re.search(p, s):
                r.append(ident[k])
                s = re.sub(p, "#", s)
        return sorted(set(r))

    INI = re.compile(r"Em (?:\d+ª |única |redação final[^,]{0,10})?(?:discussão|votação)[^,]{0,30},")
    RES = re.compile(r"(?:O|A) (projeto|matéria|substitutivo|proposição)(?! de emenda)[^.]{0,80}? foi (aprovad[oa]|rejeitad[oa])([^.]*)\.")
    proj, avisos, ultima = {}, [], ""
    for ano in ANOS:
        arq = CACHE / f"{ano}.jsonl.gz"
        if not arq.exists():
            continue
        for linha in gzip.open(arq, "rt", encoding="utf-8"):
            a = json.loads(linha)
            if a.get("tipo") not in ("Reunião ordinária", "Reunião extraordinária"):
                continue
            ultima = max(ultima, a["data"])
            t = re.sub(r"\s+", " ", a.get("texto") or "")
            t = re.sub(r", conforme MP nº 2\.200-2/2001.*?ATA (?:NÃO )?APROVADA", "", t)
            t = re.sub(r"\b(Dr|Dra|Sr|Sra|nº|n|arts|art|inc|incs)\.", r"\1§", t)
            t = re.sub(r"(\d)\.(\d)", r"\1¤\2", t)  # ponto de milhar não encerra frase
            pos = [m.start() for m in INI.finditer(t)] + [len(t)]
            for i in range(len(pos) - 1):
                seg = t[pos[i]:pos[i + 1]]
                m = re.search(r"Mensagem do Executivo nº ?([\d¤]+/\d{4})", seg[:400])
                if not m:
                    continue
                r = RES.search(seg, m.end())
                if not r:
                    continue  # vista, adiamento, retirada de pauta
                if re.search(r"Projeto de Lei(?: Complementar)? nº \d", seg[m.end():r.start()]):
                    continue  # o resultado é de outro projeto
                cauda = r.group(3)
                contra = abst = []
                mc = re.search(r"contrári[oa]s?([^.]*)", cauda)
                if mc:
                    contra = acha(re.split(r"abst", mc.group(1))[0])
                    if not contra:
                        avisos.append(f"{a['data']} {m.group(1)}: contrário sem nome reconhecido")
                ma = re.search(r"abst[^.]*", cauda)
                if ma:
                    abst = acha(ma.group(0))
                msg = m.group(1).replace("¤", ".")
                tit = re.search(r"Mensagem do Executivo nº ?[\d¤]+/\d{4},? (?:que )?(.*?)(?:, referente ao Processo|\.|$)", seg)
                desf = lambda s: s.replace("§", ".").replace("¤", ".")
                p = proj.setdefault(msg, {"msg": msg, "titulo": desf(tit.group(1))[:220] if tit else "", "votos": []})
                p["votos"].append({
                    "data": a["data"], "ata": a["cod"], "disc": re.sub(r",$", "", seg[3:16]).strip(),
                    "res": "aprovado" if r.group(2).startswith("aprov") else "rejeitado",
                    "contra": contra, "abst": abst, "texto": desf(r.group(0))[:400],
                })
    lista = sorted(proj.values(), key=lambda p: p["votos"][0]["data"])
    por = {}
    for v in V:
        c = [p["msg"] for p in lista if any(v["id"] in x["contra"] for x in p["votos"])]
        ab = [p["msg"] for p in lista if any(v["id"] in x["abst"] for x in p["votos"])]
        por[v["id"]] = {"contra": c, "abst": ab}
    saida = {
        "gerado": dt.date.today().isoformat(), "ultima_ata": ultima, "ata_url": ATA,
        "projetos": lista, "por_vereador": por, "avisos": avisos,
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    json.dump(saida, open(SAIDA, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{len(lista)} projetos do Executivo votados; última ata {ultima}; avisos: {len(avisos)}")
    for x in avisos:
        print("  aviso:", x)


if __name__ == "__main__":
    main()
