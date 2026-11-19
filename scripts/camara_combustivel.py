"""Combustível dos carros dos vereadores: litros por mês, como publicado pela Câmara.

Fonte oficial: Portal da Transparência da Câmara Municipal de Juiz de Fora,
"Despesas com Combustíveis dos Veículos Oficiais" (transparencia/combustiveis.php).
Cada mês tem um relatório em PDF com o valor pago no mês e a lista de carros
(placa, gabinete ou "Administração" e litros abastecidos).

Os carros são locados pela Câmara e o combustível é pago pela Câmara. Usar o carro faz parte
do mandato (visitar bairros, reuniões), então litro alto não é, por si só, sinal de irregularidade.

Saída: site/dados/combustivel.json   Cache: data/cache/combustivel.json
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
from pypdf import PdfReader

RAIZ = Path(__file__).resolve().parent.parent
B = "https://www.camarajf.mg.gov.br/"
UA = {"User-Agent": "RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
CACHE = RAIZ / "data" / "cache" / "combustivel.json"
SAIDA = RAIZ / "site" / "dados" / "combustivel.json"
INICIO = "2025-01"  # legislatura atual
TETO_L, TETO_R = 400, 2000  # a Câmara paga até 400 litros por carro no mês (até mai/2025: R$ 2.000)
REVER = 2  # meses mais recentes sempre lidos de novo
MESES = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
LINHA = re.compile(r"Placa:\s*([A-Z0-9-]+)\s*-\s*(.+?)\s*-\s*Litros:\s*([\d.,]+)\s*-\s*Litros Pagos/CMJF:\s*([\d.,]+)")
# fev a mai/2025 a Câmara publicou o valor em reais, não os litros
VALOR = re.compile(r"Placa:\s*([A-Z0-9-]+)\s*-\s*(.+?)\s*-\s*Valor gasto:\s*([\d.,]+)\s*-\s*Valor Pago/CMJF:\s*([\d.,]+)")
PERIODO = re.compile(r"(\d\d)/(\d\d)/(\d{4})\s*[àa]\s*(\d\d)/(\d\d)/(\d{4})")


def sem_acento(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def num(s):
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0


def br(v):
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


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
    t = sem_acento(rotulo)
    a = re.search(r"(20\d\d)", t)
    for i, m in enumerate(MESES):
        if m in t and a:
            return f"{a.group(1)}-{i + 1:02d}"
    return None


def ler(cod):
    r = get(B + "relatorio.php", params={"cod_relatorio": cod})
    if not r or r.content[:4] != b"%PDF":
        return None
    texto = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(r.content)).pages)
    per = PERIODO.search(texto)
    if per and (per.group(2), per.group(3)) != (per.group(5), per.group(6)):
        print(f"  relatório {cod} cobre {per.group(0)}: não é de um mês só, fica de fora", file=sys.stderr)
        return {"consolidado": per.group(0), "carros": []}
    pago = None
    for ln in texto.splitlines():
        if ln.strip().lower().startswith("despesas com"):
            ns = [num(x) for x in re.findall(r"\d[\d.]*,\d\d", ln)]
            if len(ns) >= 7:
                pago = ns[5]  # colunas: dotação, crédito, empenhado no mês, liquidado no ano, saldo, pago no mês, pago no ano
                break
            if ns:
                pago = max(ns)
                break
    plano = re.sub(r"\s+", " ", texto)
    carros = []
    for placa, quem, litros, pagos in LINHA.findall(plano):
        carros.append({"placa": placa, "quem": quem.strip(), "litros": round(num(pagos), 2), "abastecidos": round(num(litros), 2)})
    for placa, quem, gasto, pg in VALOR.findall(plano):
        carros.append({"placa": placa, "quem": quem.strip(), "reais": round(num(pg), 2)})
    return {"pago": pago, "carros": carros}


def mapa_vereadores():
    try:
        R = json.loads((RAIZ / "site" / "dados" / "resumo.json").read_text())
    except (OSError, ValueError):
        return []
    out = []
    for v in R.get("vereadores", []):
        ap = set(re.findall(r"[a-z]+", sem_acento(v["apelido"]))) - {"dr", "de", "da", "do", "dos"}
        nm = set(re.findall(r"[a-z]+", sem_acento(v.get("nome", "")))) - {"de", "da", "do", "dos"}
        out.append((v["id"], ap, nm))
    return out


def quem_e(rotulo, VER):
    t = set(re.findall(r"[a-z]+", sem_acento(rotulo))) - {"dr", "de", "da", "do", "dos"}
    if not t or "administracao" in t:
        return None
    for campo in (1, 2):
        ach = [v[0] for v in VER if t <= v[campo]]
        if len(ach) == 1:
            return ach[0]
    return None


def main():
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    r = get(B + "transparencia/geraIntervalo.php", params={"ct": 15})
    lista = []
    if r:
        try:
            lista = r.json()
        except ValueError:
            lista = []
    meses = sorted({m: x["cod"] for x in lista if (m := mes_de(x.get("value", ""))) and m >= INICIO}.items(), reverse=True)
    if not meses and not cache:
        sys.exit("sem lista de relatórios de combustível")
    for i, (m, cod) in enumerate(meses):
        if m in cache and i >= REVER and cache[m].get("cod") == cod:
            continue
        d = ler(cod)
        if d and d.get("consolidado"):
            cache.pop(m, None)
        elif d and d["carros"]:
            cache[m] = {"cod": cod, **d}
            print(f"  {m}: {len(d['carros'])} carros, pago {d['pago']}")
        time.sleep(1)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=0, sort_keys=True))

    VER = mapa_vereadores()
    saida_meses = []
    por = {}
    avisos, marcas = [], {}
    for m in sorted(cache, reverse=True):
        c = cache[m]
        if not c.get("carros"):
            continue
        em_litros = any("litros" in x for x in c["carros"])
        lt = sum(x.get("litros", 0) for x in c["carros"])
        rs = sum(x.get("reais", 0) for x in c["carros"])
        pago = c.get("pago") or (rs or None)
        preco = round(pago / lt, 2) if em_litros and pago and lt else None
        if preco and not (3 <= preco <= 12):
            preco = None  # valor fora do razoável: provável leitura errada ou pagamento de outro mês
        soma = {}
        for x in c["carros"]:
            vid = quem_e(x["quem"], VER)
            k = vid if vid is not None else ("adm" if "administra" in sem_acento(x["quem"]) else x["quem"])
            a = soma.setdefault(k, [0.0, 0.0])
            a[0] += x.get("litros", 0)
            a[1] += x.get("reais", 0) or (x.get("litros", 0) * preco if preco else 0)
            ab = x.get("abastecidos") or 0
            if ab > TETO_L * 5:
                avisos.append({"m": m, "placa": x["placa"], "quem": x["quem"], "abastecidos": ab, "pagos": x.get("litros"),
                               "texto": f"O relatório oficial mostra {br(ab)} litros abastecidos pelo carro {x['placa']} ({x['quem']}), número impossível para um mês. A Câmara pagou {br(x.get('litros', 0))} litros. Parece erro de digitação no relatório."})
            elif isinstance(k, int):
                bateu = x.get("litros", 0) >= TETO_L - 0.5 or x.get("reais", 0) >= TETO_R - 0.5
                if bateu or ab > (x.get("litros") or 0) + 0.5:
                    marcas.setdefault(k, []).append({"m": m, "teto": bateu, "abastecidos": ab or None, "pagos": x.get("litros") or x.get("reais")})
        for k, (l, r) in soma.items():
            if isinstance(k, int):
                p = por.setdefault(k, {"litros": 0, "meses": 0, "reais_est": 0.0, "meses_reais": 0})
                if em_litros:
                    p["litros"] = round(p["litros"] + l, 2)
                    p["meses"] += 1
                if r:
                    p["reais_est"] = round(p["reais_est"] + r, 2)
                    p["meses_reais"] += 1
        saida_meses.append({"m": m, "pago": pago, "em": "litros" if em_litros else "reais", "litros": round(lt, 2), "preco_medio": preco,
                            "cod": c["cod"], "por": [{"id": k if isinstance(k, int) else None,
                                                      "quem": "Administração" if k == "adm" else (k if isinstance(k, str) else ""),
                                                      "litros": round(l, 2), "reais": round(r, 2)} for k, (l, r) in sorted(soma.items(), key=lambda kv: -(kv[1][0] or kv[1][1]))]})
    sem = sorted({x["quem"] for mm in saida_meses for x in mm["por"] if x["id"] is None and x["quem"] != "Administração"})
    if sem:
        print("  sem vereador identificado:", sem, file=sys.stderr)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps({
        "atualizado": dt.date.today().isoformat(),
        "fonte": B + "transparencia/combustiveis.php",
        "relatorio": B + "relatorio.php?cod_relatorio={}",
        "meses": saida_meses,
        "por_vereador": {str(k): {**v, "teto": sorted(marcas.get(k, []), key=lambda x: x["m"])} for k, v in por.items()},
        "teto_litros": TETO_L, "teto_reais": TETO_R,
        "avisos": avisos,
    }, ensure_ascii=False, separators=(",", ":")))
    print(f"combustivel.json: {len(saida_meses)} meses, {len(por)} vereadores")


if __name__ == "__main__":
    main()
