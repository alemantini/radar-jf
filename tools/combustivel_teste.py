"""Prefeitura de Juiz de Fora: combustível da frota.

Lê os empenhos já baixados (site/dados/prefeitura/empenhos_AAAA.json). Cada empenho (nota de empenho,
"NE") aparece em várias linhas: a reserva, os reforços, as anulações e os pagamentos. Por isso a
classificação é feita no empenho inteiro (secretaria + número + fornecedor; o mesmo número se repete
entre fornecedores diferentes), usando todos os textos dele:
  - entra se o tipo de despesa for "Combustíveis Automotivos", ou se o texto falar em compra,
    fornecimento ou abastecimento de combustível (gasolina, etanol, diesel), ou se o fornecedor for
    distribuidora ou posto de combustível;
  - sai se o texto for de aluguel de veículo, transporte (escolar, de pacientes) ou de outra coisa
    (o aluguel "sem motorista e sem combustível" fica fora).
Pagamentos a pessoas físicas não entram. Saída: site/dados/prefeitura/combustivel.json
"""
import datetime as dt
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "site" / "dados" / "prefeitura"
SAIDA = DADOS / "combustivel.json"

FUEL = re.compile(r"combustiv|gasolina|oleo diesel|\bdiesel\b|etanol|abastecimento d[aeo]s? (veiculos|frota)")
COMPRA = re.compile(r"(aquisi|fornecimento|abastecimento|compra|referente|ref\.?|despesa|gerenciamento)[^.]{0,80}(combustiv|gasolina|diesel|etanol)|oleo diesel ?b|gasolina comum|etanol hidratado")
FORA = re.compile(r"sem (motorista e sem )?combustiv|bicombustiv|locacao|aluguel|transporte escolar|transporte de pacient|prestacao de servico de ?transporte|generos alimenticios|ceasa")
FORNECEDOR = re.compile(r"petroleo|combustiv|\bposto\b|lubrif")
GERENCIA = re.compile(r"gerenciamento|cartao")


def chave(t):
    t = str(t or "")
    if "Ã" in t or "Â" in t:
        try:
            t = t.encode("cp1252", "ignore").decode("utf-8", "ignore") or t
        except Exception:
            pass
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn").lower()


def tipo(textos):
    t = " ".join(textos)
    tem = [n for n, r in (("diesel", r"diesel"), ("gasolina", r"gasolina"), ("etanol", r"etanol|alcool")) if re.search(r, t)]
    if GERENCIA.search(t):
        return "cartão de abastecimento (gasolina e etanol)"
    if tem == ["diesel"]:
        return "diesel"
    if tem == ["gasolina"]:
        return "gasolina"
    if tem == ["etanol"]:
        return "etanol"
    if set(tem) == {"gasolina", "etanol"}:
        return "gasolina e etanol"
    return "combustível (tipo não informado)" if not tem else "vários tipos"


def main():
    anos = sorted(int(f.stem.split("_")[1]) for f in DADOS.glob("empenhos_*.json"))
    saida = {"atualizado": dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M"), "anos": {}}
    for ano in anos:
        d = json.loads((DADOS / f"empenhos_{ano}.json").read_text(encoding="utf-8"))
        secs, els, creds = d["secretarias"], d["elementos"], d["credores"]
        ne = defaultdict(lambda: {"linhas": [], "textos": set(), "els": set(), "cred": None})
        datas = []
        for data, u, ic, ie, e, p, hist, num, *_ in d["empenhos"]:
            if data:
                datas.append(data)
            if ic < 0:
                continue  # pessoa física: fora
            x = ne[(u, num, ic)]
            x["linhas"].append((data, e or 0, p or 0))
            x["textos"].add(chave(hist))
            x["els"].add(chave(els[ie]))
            x["cred"] = ic
        tot_e = tot_p = 0.0
        sec = defaultdict(lambda: [0.0, 0.0, 0])
        forn = defaultdict(lambda: [0.0, 0.0, 0])
        tip = defaultdict(lambda: [0.0, 0.0])
        lista = []
        for (u, num, _ic), x in ne.items():
            t = " ".join(x["textos"])
            ck = chave(creds[x["cred"]][1])
            el_comb = any("combustiveis automotivos" in e for e in x["els"])
            fora = FORA.search(t) and not COMPRA.search(t.replace("sem combustivel", "").replace("sem motorista e sem combustivel", ""))
            ok = el_comb or (not fora and (COMPRA.search(t) or (FORNECEDOR.search(ck) and FUEL.search(t))))
            if FORA.search(t) and not el_comb and not FORNECEDOR.search(ck) and not GERENCIA.search(t):
                ok = False
            if not ok:
                continue
            e = sum(l[1] for l in x["linhas"])
            p = sum(l[2] for l in x["linhas"])
            if abs(e) < 0.01 and abs(p) < 0.01:
                continue
            tp = tipo(x["textos"])
            data0 = min(l[0] for l in x["linhas"] if l[0])
            tot_e += e
            tot_p += p
            s = sec[secs[u]]; s[0] += e; s[1] += p; s[2] += 1
            f = forn[x["cred"]]; f[0] += e; f[1] += p; f[2] += 1
            tip[tp][0] += e; tip[tp][1] += p
            texto = max(x["textos"], key=len)
            lub = "lubrific" in t
            lista.append([data0, secs[u], creds[x["cred"]][0], creds[x["cred"]][1], round(e, 2), round(p, 2), num, tp, lub])
        lista.sort(key=lambda z: -max(z[4], z[5]))
        saida["anos"][str(ano)] = {
            "ate": max(datas) if datas else "",
            "empenhado": round(tot_e, 2), "pago": round(tot_p, 2), "empenhos": len(lista),
            "secretarias": [[s, round(v[0], 2), round(v[1], 2), v[2]] for s, v in sorted(sec.items(), key=lambda kv: -max(kv[1][0], kv[1][1]))],
            "fornecedores": [[creds[i][0], creds[i][1], round(v[0], 2), round(v[1], 2), v[2]] for i, v in sorted(forn.items(), key=lambda kv: -max(kv[1][0], kv[1][1]))],
            "tipos": [[k, round(v[0], 2), round(v[1], 2)] for k, v in sorted(tip.items(), key=lambda kv: -kv[1][1])],
            "maiores": lista[:30],
            "com_lubrificante": sum(1 for z in lista if z[8]),
        }
        a = saida["anos"][str(ano)]
        print(f"Combustível {ano}: empenhado R$ {tot_e / 1e6:.2f} mi, pago R$ {tot_p / 1e6:.2f} mi, {len(lista)} empenhos, até {a['ate']}")
    SAIDA.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
