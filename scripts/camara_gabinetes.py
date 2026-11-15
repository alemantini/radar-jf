"""Custo dos gabinetes: quanto a Câmara paga, por mês, à equipe de cada vereador.

Fonte oficial: Portal da Transparência da Câmara Municipal de Juiz de Fora,
"Remuneração dos servidores" (transparencia/remuneracaoServidores.php). Cada servidor aparece com a
lotação; os assessores de cada vereador ficam lotados em "Gabinete <nome do vereador>".

Totais mês a mês por gabinete e, para o mês mais recente, a lista da equipe de cada gabinete
(nome, cargo e remuneração bruta), como publicada pela própria Câmara (dados públicos de servidores).

Saída: site/dados/gabinetes.json
"""
import datetime as dt
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
B = "https://www.camarajf.mg.gov.br/transparencia/"
UA = {"User-Agent": "RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
CACHE = RAIZ / "data" / "cache" / "gabinetes.json"
SAIDA = RAIZ / "site" / "dados" / "gabinetes.json"
INICIO = (2025, 1)
REVER = 2  # meses mais recentes sempre baixados de novo (a folha pode ser corrigida)


def chave(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def num(s):
    s = (s or "").replace("*", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def baixar(mes, ano):
    p = {"codcetil": "", "mesref": f"{mes:02d}/{ano}", "mes": f"{mes:02d}", "ano": str(ano),
         "nome": "", "codsetor": "", "codfuncao": ""}
    for i in range(3):
        try:
            r = requests.get(B + "lista_servidor.php", params=p, headers=UA, timeout=120)
            if r.status_code == 200:
                d = r.json()
                if isinstance(d, list):
                    return d
            print(f"  HTTP {r.status_code} em {mes:02d}/{ano}", file=sys.stderr)
        except (requests.RequestException, ValueError) as e:
            print(f"  erro {e}", file=sys.stderr)
        time.sleep(10 * (i + 1))
    return None


def ultimo_mes():
    try:
        t = requests.get(B + "remuneracaoServidores.php", headers=UA, timeout=60).text
        m = re.search(r'maxmesref\s*=\s*"(\d{4})(\d{2})"', t)
        if m:
            return int(m.group(1)), int(m.group(2))
    except requests.RequestException as e:
        print(f"  erro {e}", file=sys.stderr)
    return None


def campo(x, *partes):
    for k, v in x.items():
        if any(p in k.lower() for p in partes):
            return (v or "").strip() if isinstance(v, str) else v
    return ""


def equipes(linhas):
    """Equipe de cada gabinete no mês: nome, cargo e remuneração bruta (como no portal da Câmara)."""
    eq = {}
    for x in linhas:
        lot = (x.get("lotacao") or "").strip()
        if lot.lower().startswith("gabinete ") and "presid" not in lot.lower():
            eq.setdefault(lot[9:].strip(), []).append([
                campo(x, "nome"), campo(x, "cargo", "funcao", "função"), round(num(x.get("rembruta")), 2)])
    for v in eq.values():
        v.sort(key=lambda r: -r[2])
    return eq


def resumir(linhas):
    """Totais do mês, sem nomes: por gabinete e da Câmara toda."""
    gab, total, n = {}, 0.0, 0
    for x in linhas:
        bruto = num(x.get("rembruta"))
        total += bruto
        n += 1
        lot = (x.get("lotacao") or "").strip()
        if lot.lower().startswith("gabinete ") and "presid" not in lot.lower():
            g = gab.setdefault(lot[9:].strip(), {"n": 0, "custo": 0.0})
            g["n"] += 1
            g["custo"] = round(g["custo"] + bruto, 2)
    return {"gabinetes": gab, "folha_total": round(total, 2), "pessoas": n}


def main():
    fim = ultimo_mes()
    if not fim:
        print("Gabinetes: portal não informou o último mês")
        sys.exit(1)
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    meses, (a, m) = [], INICIO
    while (a, m) <= fim:
        meses.append((a, m))
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    equipe_ultimo = {}
    for a, m in meses:
        k = f"{a}-{m:02d}"
        if k in cache and (a, m) not in meses[-REVER:]:
            continue
        linhas = baixar(m, a)
        if linhas is None:
            continue
        if linhas:
            if (a, m) == meses[-1]:
                print("  campos do portal:", list(linhas[0].keys()))
                equipe_ultimo = equipes(linhas)
            cache[k] = resumir(linhas)
            print(f"  {k}: {len(cache[k]['gabinetes'])} gabinetes, {cache[k]['pessoas']} pessoas")
        time.sleep(1.5)
    if not cache:
        print("Gabinetes: nada coletado")
        sys.exit(1)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, sort_keys=True, indent=0), encoding="utf-8")

    # liga cada gabinete ao vereador pelo nome completo
    vereadores = json.loads((RAIZ / "data" / "bruto" / "vereadores.json").read_text())
    def achar(nome_gab):
        nome = nome_gab.split(" - ")[0]
        cg = chave(nome)
        for v in vereadores:
            cv = chave(v["nome"])
            if cv and (cv == cg or cv in cg or cg in cv):
                return v["id"]
        return None

    por = {}
    for g, lst in equipe_ultimo.items():
        vid = achar(g)
        if vid is not None:
            por.setdefault(str(vid), {"meses": {}})["equipe"] = lst
    for k in sorted(cache):
        for g, x in cache[k]["gabinetes"].items():
            vid = achar(g)
            if vid is None:
                continue
            p = por.setdefault(str(vid), {"meses": {}})
            p["meses"][k] = [x["n"], x["custo"]]
    ultimo = max(cache)
    for p in por.values():
        vals = [c for _, c in p["meses"].values()]
        p["total"] = round(sum(vals), 2)
        p["media"] = round(sum(vals) / len(vals), 2) if vals else 0
        n_u, c_u = p["meses"].get(ultimo, [0, 0])
        p["atual"] = {"n": n_u, "custo": c_u}
    res = {"fonte": "Portal da Transparência da Câmara Municipal de Juiz de Fora (remuneração dos servidores)",
           "fonte_url": B + "remuneracaoServidores.php",
           "coletado_em": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
           "desde": f"{INICIO[1]:02d}/{INICIO[0]}", "ultimo_mes": ultimo,
           "folha_camara": {k: cache[k]["folha_total"] for k in sorted(cache)},
           "vereadores": por}
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Gabinetes: {len(por)} vereadores ligados, último mês {ultimo}")
    if len(por) < 15:
        print("Gabinetes: poucos vereadores ligados, confira os nomes")


if __name__ == "__main__":
    main()
