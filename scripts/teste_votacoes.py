"""Teste "Qual vereador combina com você?", Parte 1.

Junta as perguntas escritas à mão em data/manual/teste_votacoes.json com os votos
lidos das atas (site/dados/executivo.json, gerado por camara_executivo.py) e grava
site/dados/teste.json com os vereadores nomeados em cada lado.

As atas só dão nome a quem vota contra (projetos do Executivo) ou ao placar do veto.
Quem votou a favor de projeto do Executivo não aparece com nome: "so_contra_nomeado".
"""
import datetime as dt
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "data" / "manual" / "teste_votacoes.json"
EXECUTIVO = RAIZ / "site" / "dados" / "executivo.json"
SAIDA = RAIZ / "site" / "dados" / "teste.json"


def montar(perguntas, executivo):
    proj = {p["msg"]: p for p in executivo.get("projetos", [])}
    vetos = {}
    for v in executivo.get("vetos", []):
        vetos.setdefault(v["projeto"], []).append(v)
    saida = []
    for q in perguntas:
        if q["fonte"] == "manual":
            sim, nao = sorted(q["sim"]), sorted(q["nao"])
            item = {"data": q["data"], "ata": q.get("ata"), "resultado": q["resultado"]}
        elif q["fonte"] == "executivo":
            p = proj.get(q["ref"])
            votos = [v for v in (p or {}).get("votos", []) if not q.get("disc") or v["disc"] == q["disc"]]
            if not votos:
                raise SystemExit(f"pergunta {q['id']}: {q['ref']} {q.get('disc') or ''} não está no executivo.json")
            v = votos[-1]
            contra = sorted(set(v["contra"]))
            sim, nao = ([], contra) if q["sim_e"] == "aprovar" else (contra, [])
            item = {"data": v["data"], "ata": v["ata"], "resultado": v["res"]}
        else:
            lista = vetos.get(q["ref"])
            if not lista:
                raise SystemExit(f"pergunta {q['id']}: veto do {q['ref']} não está no executivo.json")
            v = lista[-1]
            der, man = sorted(set(v["derrubar"])), sorted(set(v["manter"]))
            sim, nao = (der, man) if q["sim_e"] == "derrubar" else (man, der)
            item = {"data": v["data"], "ata": v["ata"], "resultado": "veto " + v["res"]}
        saida.append({"id": q["id"], "pergunta": q["pergunta"], "explica": q["explica"], "ref": q["ref"],
                      "tipo": q["fonte"], "sim": sim, "nao": nao, "so_contra_nomeado": not (sim and nao),
                      "aviso": q.get("aviso"), "link": q.get("link"), **item})
    return {"gerado": dt.date.today().isoformat(), "perguntas": saida}


def main():
    perguntas = json.load(open(ENTRADA, encoding="utf-8"))
    executivo = json.load(open(EXECUTIVO, encoding="utf-8"))
    r = montar(perguntas, executivo)
    SAIDA.write_text(json.dumps(r, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"teste.json: {len(r['perguntas'])} perguntas")


if __name__ == "__main__":
    main()
