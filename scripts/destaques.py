"""Destaques para o banner da página inicial ("Veja o que está acontecendo em Juiz de Fora").

Lê os arquivos que as outras etapas do Radar já geraram em site/dados/ e monta frases curtas,
cada uma com um número e o link para a página de onde ele vem. Se um arquivo não existir,
aquele destaque simplesmente não aparece.

Saída: site/dados/destaques.json
"""
import datetime as dt
import json
from pathlib import Path

DADOS = Path(__file__).resolve().parent.parent / "site" / "dados"
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]


def ler(rel):
    try:
        return json.loads((DADOS / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def reais(v):
    a = abs(v)
    if a >= 1e9:
        t = f"{a / 1e9:.2f}".rstrip("0").rstrip(".") + " bi"
    elif a >= 1e6:
        t = f"{a / 1e6:.1f}".rstrip("0").rstrip(".") + " mi"
    elif a >= 1e3:
        t = f"{a / 1e3:.0f} mil"
    else:
        t = f"{a:.0f}"
    return "R$ " + t.replace(".", ",")


def fmt(n):
    return f"{n:,}".replace(",", ".")


def main():
    D = []
    vereadores = {v["id"]: v for v in (ler("resumo.json") or {}).get("vereadores", [])}

    Q = ler("atas_quente.json")
    if Q and Q.get("meses"):
        m = next((x for x in Q["meses"] if x["reunioes"] >= 8 and x["pautas"]), None)
        if m:
            p = m["pautas"][0]
            D.append({"area": "camara", "ic": "alerta", "rot": "Assunto do mês", "v": p["p"],
                      "d": f"Foi o assunto que mais vereadores levaram às reuniões em {MESES[int(m['m'][5:]) - 1]}: "
                           f"{len(p['vereadores'])} vereadores falaram dele.", "href": f"#/quente/{m['m']}"})

    C = ler("prefeitura/chuvas.json")
    if C and C.get("categorias"):
        e = sum(c["e"] for c in C["categorias"])
        p = sum(c["p"] for c in C["categorias"])
        D.append({"area": "prefeitura", "ic": "alerta", "rot": "Dinheiro das chuvas", "v": reais(e),
                  "d": f"reservados pela Prefeitura para as chuvas desde dezembro de 2025. Já foram pagos {reais(p)}.",
                  "href": "#/prefeitura/chuvas"})

    F = ler("atas_falas.json")
    if F and F.get("vereadores"):
        cands = []
        for vid, f in F["vereadores"].items():
            v = vereadores.get(int(vid))
            if not v or v.get("fora_da_lista") or str(v.get("mesa", "")).strip().lower() == "presidente" or f["reunioes"] < 60:
                continue
            cands.append((f["falou"] / f["reunioes"], v["apelido"]))
        if cands:
            pct, nome = max(cands)
            D.append({"area": "camara", "ic": "fala", "rot": "Quem mais fala", "v": nome,
                      "d": f"falou em {round(100 * pct)}% das reuniões da Câmara desde a posse, segundo as atas.",
                      "href": "#/placar/tribuna"})
        temas = {}
        for f in F["vereadores"].values():
            for t, n in f.get("temas", []):
                temas[t] = temas.get(t, 0) + n
        if temas:
            t = max(temas, key=temas.get)
            D.append({"area": "camara", "ic": "fala", "rot": "Quem defende o quê", "v": t,
                      "d": "é o assunto que os vereadores mais levam para a tribuna desde 2025. Veja quem fala de quê.",
                      "href": "#/defende"})

    H = ler("prefeitura/hospitais.json")
    if H and H.get("anos"):
        ano = max(H["anos"])
        L = H["anos"][ano]
        D.append({"area": "prefeitura", "ic": "coracao", "rot": "Hospitais", "v": reais(sum(h["p"] for h in L)),
                  "d": f"pagos pela Prefeitura a {len(L)} hospitais em {ano}, até agora.", "href": "#/prefeitura/hospitais"})

    E = ler("prefeitura/emprestimos.json")
    if E and E.get("entradas"):
        x = E["entradas"][-1]
        ate = f" até {MESES[x['ate_mes'] - 1]}" if x.get("ate_mes", 12) < 12 else ""
        D.append({"area": "prefeitura", "ic": "dinheiro", "rot": "Empréstimos", "v": reais(x.get("recebido") or 0),
                  "d": f"em empréstimos entraram nos cofres da Prefeitura em {x['ano']}{ate}.", "href": "#/prefeitura/emprestimos"})

    CR = ler("prefeitura/creditos.json")
    if CR and CR.get("anos"):
        ano = max(CR["anos"])
        A = CR["anos"][ano]
        D.append({"area": "prefeitura", "ic": "repete", "rot": "Orçamento que muda", "v": reais(A["valor"]),
                  "d": f"colocados em outras áreas do orçamento por decreto da prefeita em {ano}, em {fmt(A['n'])} decretos.",
                  "href": "#/prefeitura/creditos"})

    AL = ler("prefeitura/alertas.json")
    if AL and AL.get("alertas"):
        D.append({"area": "alerta", "ic": "alerta", "rot": "Sinais de alerta", "v": f"{fmt(len(AL['alertas']))} sinais",
                  "d": "nos gastos da Prefeitura que merecem uma pergunta: compras fatiadas, empresas punidas e mais.",
                  "href": "#/prefeitura/alertas"})

    AT = ler("atas.json")
    if AT and AT.get("atas"):
        D.append({"area": "camara", "ic": "lupa", "rot": "Atas da Câmara", "v": f"{fmt(len(AT['atas']))} atas",
                  "d": "das reuniões e audiências públicas para pesquisar por tema, bairro ou vereador.", "href": "#/atas"})

    agora = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M")
    (DADOS / "destaques.json").write_text(json.dumps({"atualizado": agora, "itens": D}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Destaques: {len(D)}")


if __name__ == "__main__":
    main()
