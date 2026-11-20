"""Diárias de viagem pagas pela Câmara (relatórios mensais do Portal da Transparência da Câmara).

Fonte: transparencia/viagens.php -> geraIntervalo.php?ct=25 -> relatorio.php?cod_relatorio=N (PDF com tabela:
DATA | MOTIVO | LOCALIDADE | SERVIDORES/CARGO | VALOR | NÚMERO | DIÁRIAS).

Quem recebe a diária são servidores e motoristas, não os vereadores. Muitas viagens são para levar ou
acompanhar um vereador, citado no motivo; essas ficam ligadas ao vereador.
Por prudência o site mostra o cargo de quem recebeu, não o nome do servidor.

Saída: site/dados/diarias.json   Cache: data/cache/diarias.json
"""
import datetime as dt
import io
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
B = "https://www.camarajf.mg.gov.br/"
UA = {"User-Agent": "RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
CACHE = RAIZ / "data" / "cache" / "diarias.json"
SAIDA = RAIZ / "site" / "dados" / "diarias.json"
INICIO = "2025-01"
VERSAO = 3  # muda quando a leitura do PDF muda, para reler tudo
REVER = 2
MESES = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
NUMERO = re.compile(r"^\s*(\d{1,3})(?:\s*/\s*(20\d\d))?\s*$")  # "42/2026" ou só "65"
STOP = {"dr", "de", "da", "do", "dos", "das", "e", "para", "ate", "no", "na", "ao", "que", "com", "em", "a", "o", "ate", "junto", "sr", "sra"}


def sa(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def limpa(s):
    return re.sub(r"\s+", " ", s or "").strip()


def get(url, **kw):
    for i in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=90, **kw)
            if r.status_code == 200:
                return r
            print(f"  HTTP {r.status_code} {url}", file=sys.stderr)
        except requests.RequestException as e:
            print(f"  erro {e}", file=sys.stderr)
        time.sleep(8 * (i + 1))
    return None


def mes_de(rotulo):
    t = sa(rotulo)
    a = re.search(r"(20\d\d)", t)
    for i, m in enumerate(MESES):
        if re.search(r"\b" + m + r"\b", t) and a:
            return f"{a.group(1)}-{i + 1:02d}"
    return None


def valor(s):
    s = limpa(s)
    if "cancel" in sa(s) or "anulad" in sa(s):
        return None, True
    m = re.search(r"(\d[\d.]*,\d{2})", s)
    if not m:
        return None, False
    return float(m.group(1).replace(".", "").replace(",", ".")), False


def ler(cod, ano):
    import pdfplumber
    r = get(B + "relatorio.php", params={"cod_relatorio": cod})
    if not r or r.content[:4] != b"%PDF":
        return None
    regs = []
    with pdfplumber.open(io.BytesIO(r.content)) as pdf:
        for pg in pdf.pages:
            for tb in pg.extract_tables():
                for row in tb:
                    row = [limpa(c) for c in row] + [""] * 7
                    data, motivo, local, quem, val, num, dias = row[:7]
                    if sa(motivo).startswith("motivo") or sa(data) == "data":
                        continue
                    m = NUMERO.match(num)
                    if m:
                        v, canc = valor(val)
                        canc = canc or "anulad" in sa(local) or "cancelad" in sa(local)
                        regs.append({"n": f"{int(m.group(1))}/{m.group(2) or ano}", "data": data, "motivo": motivo, "local": local,
                                     "quem": quem, "valor": v, "cancelado": canc, "diarias": dias})
                    elif regs and any([data, motivo, dias]):
                        # continuação da linha anterior (a tabela quebrou de página)
                        a = regs[-1]
                        a["data"] = limpa(a["data"] + " " + data)
                        a["motivo"] = limpa(a["motivo"] + " " + motivo)
                        a["diarias"] = limpa(a["diarias"] + " " + dias)
                        if not a["local"] and local:
                            a["local"] = local
                        if a["valor"] is None and not a["cancelado"] and val:
                            a["valor"], a["cancelado"] = valor(val)
    return regs


def vereadores():
    try:
        R = json.loads((RAIZ / "site" / "dados" / "resumo.json").read_text())
    except (OSError, ValueError):
        return []
    out = []
    for v in R.get("vereadores", []):
        ap = set(re.findall(r"[a-z]+", sa(v["apelido"]))) - STOP
        nm = set(re.findall(r"[a-z]+", sa(v.get("nome", "")))) - STOP
        out.append((v["id"], ap, nm))
        frases = {re.sub(r"^dr\.? ", "", sa(v["apelido"])).replace("-", " ").strip()}
        if len(nm) >= 2:
            frases.add(" ".join(re.findall(r"[a-z]+", sa(v.get("nome", "")))))
        VER_TXT.append((v["id"], [f for f in frases if len(f) >= 8]))
    return out


VER_TXT = []


def citados(motivo, VER):
    """Vereadores citados no motivo, no formato 'vereador(a) Fulano de Tal'."""
    t = sa(motivo).replace("thiago", "tiago")
    achados = []
    for m in re.finditer(r"vereador(?:a|es|as)?\s+((?:dr\.?\s+)?[a-z]+(?:\s+(?:da |de |do )?[a-z]+){0,2})", t):
        nome = m.group(1)
        toks = [x for x in re.findall(r"[a-z]+", nome) if x not in STOP]
        vid = None
        for k in (len(toks), 2, 1):
            tt = set(toks[:k])
            if not tt:
                continue
            for campo in (1, 2):
                ach = [v[0] for v in VER if tt <= v[campo]]
                if len(ach) == 1:
                    vid = ach[0]
                    break
            if vid:
                break
        if vid is None and (len(toks) < 2 or {"camara", "municipal", "juiz", "fora"} & set(toks)):
            continue
        achados.append({"id": vid, "nome": " ".join(w.capitalize() for w in toks[:3])})
    # segunda passada: apelido ou nome completo escrito no texto ("os vereadores Marlon Siqueira e Letícia Delgado")
    for v in VER_TXT:
        if v[0] not in {x["id"] for x in achados} and any(f in t for f in v[1]):
            achados.append({"id": v[0], "nome": ""})
    achados = [x for x in achados if x["id"]]  # só vereadores identificados
    vistos, out = set(), []
    for a in achados:
        k = a["id"] or a["nome"]
        if k not in vistos:
            vistos.add(k)
            out.append(a)
    return out


UFS = r"(MG|RJ|SP|DF|ES|BA|GO|PR|SC|RS)"


def destino(s):
    s = re.sub(r"([a-zà-ú])([A-ZÀ-Ú])", r"\1 \2", s or "")
    s = re.sub(r"\s*[-–]\s*" + UFS + r"\b\.?", "", s)
    s = re.sub(r"\s*/\s*" + UFS + r"\b\.?", "", s)
    s = limpa(s).strip(" .-–")
    pal = [w.lower() if w.lower() in ("de", "do", "da", "dos", "das") else w[:1].upper() + w[1:].lower() for w in s.split()]
    return " ".join(pal)


def cargo(quem):
    m = re.search(r"\(([^)]+)\)", quem)
    c = limpa(m.group(1)) if m else ""
    c = c.rstrip(". ")
    c = c[:1].upper() + c[1:].lower() if c.isupper() else c
    c = c[:1].upper() + c[1:]
    return c or "Servidor(a)"


def main():
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    r = get(B + "transparencia/geraIntervalo.php", params={"ct": 25})
    lista = []
    if r:
        try:
            lista = r.json()
        except ValueError:
            pass
    meses = sorted({m: x["cod"] for x in lista if (m := mes_de(x.get("value", ""))) and m >= INICIO}.items(), reverse=True)
    if not meses and not cache:
        sys.exit("sem lista de relatórios de diárias")
    for i, (m, cod) in enumerate(meses):
        if m in cache and i >= REVER and cache[m].get("cod") == cod and cache[m].get("v") == VERSAO:
            continue
        d = ler(cod, m[:4])
        if d is not None:
            cache[m] = {"cod": cod, "v": VERSAO, "regs": d}
            print(f"  {m}: {len(d)} diárias")
        time.sleep(1)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=0, sort_keys=True))

    VER = vereadores()
    viagens, por_ver, sem_id = [], {}, set()
    for m in sorted(cache, reverse=True):
        for g in cache[m]["regs"]:
            cit = citados(g["motivo"], VER)
            for c in cit:
                if c["id"] is None:
                    sem_id.add(c["nome"])
            dm = re.search(r"(\d\d)/(\d\d)/(20\d\d)", g["data"])
            viagens.append({
                "m": m, "n": g["n"], "data": f"{dm.group(3)}-{dm.group(2)}-{dm.group(1)}" if dm else "",
                "destino": destino(g["local"]), "cargo": cargo(g["quem"]), "motorista": "motorista" in sa(g["quem"]),
                "valor": g["valor"], "cancelado": g["cancelado"], "diarias": g["diarias"][:80],
                "motivo": g["motivo"][:400], "vereadores": cit, "cod": cache[m]["cod"],
            })
            if not g["cancelado"] and g["valor"]:
                for c in cit:
                    if c["id"]:
                        p = por_ver.setdefault(str(c["id"]), {"viagens": 0, "valor": 0.0, "destinos": {}})
                        p["viagens"] += 1
                        p["valor"] = round(p["valor"] + g["valor"], 2)
                        dest = destino(g["local"])
                        p["destinos"][dest] = p["destinos"].get(dest, 0) + 1
    if sem_id:
        print("  vereadores citados sem identificação:", sorted(sem_id), file=sys.stderr)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps({
        "atualizado": dt.date.today().isoformat(),
        "fonte": B + "transparencia/viagens.php",
        "relatorio": B + "relatorio.php?cod_relatorio={}",
        "meses": [{"m": m, "cod": cache[m]["cod"]} for m in sorted(cache, reverse=True)],
        "viagens": viagens,
        "por_vereador": por_ver,
    }, ensure_ascii=False, separators=(",", ":")))
    print(f"diarias.json: {len(viagens)} diárias, {len(por_ver)} vereadores citados")


if __name__ == "__main__":
    main()
