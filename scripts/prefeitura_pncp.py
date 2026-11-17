"""Sinais a partir do Portal Nacional de Contratações Públicas (PNCP).

O PNCP recebe da própria Prefeitura (obrigação da Lei 14.133/2021) as licitações, os
resultados por item e os contratos. Ele não bloqueia o robô, ao contrário do site da Prefeitura.

Sinais gerados (um sinal NÃO é prova):
  - aditivo: contrato cujo valor global ficou bem acima do valor inicial (acréscimo ou
    prorrogação; a lei limita acréscimos a 25%, ou 50% em reforma, mas prorrogar serviço
    contínuo é permitido).
  - acima: licitação homologada por valor acima do que a própria Prefeitura orçou.
  - desconto: licitação grande homologada praticamente pelo valor orçado (desconto abaixo de 1%),
    o que costuma indicar pouca disputa.

Saída: site/dados/prefeitura/pncp_sinais.json (lido por prefeitura_alertas.py).
"""
import datetime as dt
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "data" / "prefeitura" / "pncp_sinais.json"  # copiado para o site pela atualização diária
CACHE = RAIZ / "data" / "cache" / "pncp_vencedores.json"
TEMPO = 420  # segundos no máximo por execução buscando vencedores novos
CNPJ = "18338178000102"
H = {"User-Agent": "RadarJF/1.0 (robo de transparencia)"}
API = "https://pncp.gov.br/api"
ANOS = (2025, 2026)
MODALIDADES = {4: "Concorrência eletrônica", 5: "Concorrência presencial", 6: "Pregão eletrônico", 7: "Pregão presencial"}


def get(url, **p):
    for t in range(3):
        try:
            r = requests.get(url, params=p, headers=H, timeout=60)
        except requests.RequestException:
            time.sleep(5)
            continue
        if r.status_code in (204, 404):
            return None
        if r.status_code == 200:
            return r.json()
        time.sleep(5 * (t + 1))
    return None


def paginas(url, **p):
    pag = 1
    while True:
        d = get(url, pagina=pag, tamanhoPagina=50, **p)
        if not d or not d.get("data"):
            return
        yield from d["data"]
        if not d.get("paginasRestantes"):
            return
        pag += 1
        time.sleep(0.3)


def brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def janela(ano):
    fim = min(dt.date(ano, 12, 31), dt.date.today())
    return f"{ano}0101", fim.strftime("%Y%m%d")


def link_compra(c):
    return f"https://pncp.gov.br/app/editais/{CNPJ}/{c['anoCompra']}/{c['sequencialCompra']}"


VENC, INICIO = {}, time.time()


def vencedor(c):
    """Fornecedor que mais ganhou na compra (pelos resultados dos itens), com cache."""
    k = c.get("numeroControlePNCP")
    if k in VENC:
        return tuple(VENC[k])
    if time.time() - INICIO > TEMPO:
        return "", "", 0
    tot = {}
    itens = sorted(get(f"{API}/pncp/v1/orgaos/{CNPJ}/compras/{c['anoCompra']}/{c['sequencialCompra']}/itens", pagina=1, tamanhoPagina=50) or [],
                   key=lambda it: -(it.get("valorTotal") or 0))[:12]  # os 12 itens de maior valor bastam para achar o principal vencedor
    base = f"{API}/pncp/v1/orgaos/{CNPJ}/compras/{c['anoCompra']}/{c['sequencialCompra']}/itens/"
    with ThreadPoolExecutor(6) as ex:
        resultados = list(ex.map(lambda it: get(base + f"{it['numeroItem']}/resultados") or [], itens))
    for rs in resultados:
        for r in rs:
            if r.get("dataCancelamento"):
                continue
            kf = (r.get("niFornecedor") or "", r.get("nomeRazaoSocialFornecedor") or "")
            tot[kf] = tot.get(kf, 0) + (r.get("valorTotalHomologado") or 0)
    if not tot:
        return "", "", 0
    (cnpj, nome), v = max(tot.items(), key=lambda kv: kv[1])
    VENC[k] = [cnpj, nome, len(tot)]
    return cnpj, nome, len(tot)


def main():
    if CACHE.exists():
        VENC.update(json.loads(CACHE.read_text(encoding="utf-8")))
    sinais = []
    vistos = set()
    n_contratos = n_compras = n_hom = 0
    for ano in ANOS:
        ini, fim = janela(ano)
        # contratos que cresceram
        for k in paginas(f"{API}/consulta/v1/contratos", dataInicial=ini, dataFinal=fim, cnpjOrgao=CNPJ):
            n_contratos += 1
            chave = k.get("numeroControlePNCP")
            if chave in vistos:
                continue
            vistos.add(chave)
            vi, vg = k.get("valorInicial") or 0, k.get("valorGlobal") or 0
            npar = k.get("numeroParcelas") or 0
            parcela = npar > 1 and abs(vg - vi * npar) <= 0.02 * vg  # "valor inicial" lançado como valor da parcela
            if vi > 0 and vi * 1.25 < vg < vi * 10 and not parcela and vg - vi >= 100_000 and len(k.get("niFornecedor") or "") == 14:
                pct = round(100 * (vg / vi - 1))
                sinais.append({"tipo": "aditivo", "cnpj": k["niFornecedor"], "nome": k.get("nomeRazaoSocialFornecedor", ""),
                               "titulo": "Contrato cresceu muito além do valor inicial",
                               "detalhe": f"Contrato {k.get('numeroContratoEmpenho') or ''} ({(k.get('objetoContrato') or '')[:160].strip()}) começou em {brl(vi)} e o valor global está em {brl(vg)}, {pct}% a mais. A lei limita acréscimos a 25% (50% em reforma); prorrogar serviço contínuo é permitido, então vale ver os termos aditivos.",
                               "valor": round(vg, 2), "secretaria": (k.get("unidadeOrgao") or {}).get("nomeUnidade"),
                               "refs": [], "link": f"https://pncp.gov.br/app/contratos/{CNPJ}/{k['anoContrato']}/{k['sequencialContrato']}"})
        print(f"{ano}: {n_contratos} contratos lidos até agora, {len(sinais)} sinais", flush=True)
        # licitações acima do orçado ou sem desconto
        for mod in MODALIDADES:
            print(f"{ano}: modalidade {mod} ({round(time.time() - INICIO)} s)", flush=True)
            for c in paginas(f"{API}/consulta/v1/contratacoes/publicacao", dataInicial=ini, dataFinal=fim, codigoModalidadeContratacao=mod, cnpj=CNPJ):
                n_compras += 1
                est, hom = c.get("valorTotalEstimado") or 0, c.get("valorTotalHomologado") or 0
                if hom:
                    n_hom += 1
                if est < 500_000 or hom <= 0 or c.get("numeroControlePNCP") in vistos:
                    continue
                vistos.add(c.get("numeroControlePNCP"))
                tipo = None
                if hom > est * 1.01:
                    tipo, titulo = "acima", "Licitação fechada acima do valor orçado"
                    det = f"{MODALIDADES[mod]} {c.get('numeroCompra')}/{c.get('anoCompra')} ({(c.get('objetoCompra') or '')[:160].strip()}): a Prefeitura orçou {brl(est)} e homologou {brl(hom)}, {round(100 * (hom / est - 1))}% acima. Normalmente a disputa derruba o preço."
                elif est >= 1_000_000 and hom >= est * 0.99:
                    tipo, titulo = "desconto", "Licitação grande com desconto quase zero"
                    det = f"{MODALIDADES[mod]} {c.get('numeroCompra')}/{c.get('anoCompra')} ({(c.get('objetoCompra') or '')[:160].strip()}): orçada em {brl(est)} e homologada por {brl(hom)}, desconto de {max(0, 100 * (1 - hom / est)):.1f}%. Em licitações com boa disputa o desconto costuma ser bem maior."
                if not tipo:
                    continue
                cnpj, nome, nforn = vencedor(c)
                if not cnpj:
                    continue
                sinais.append({"tipo": tipo, "cnpj": cnpj, "nome": nome, "titulo": titulo,
                               "detalhe": det + (f" Itens divididos entre {nforn} fornecedores; aqui aparece o que mais ganhou." if nforn > 1 else ""),
                               "valor": round(hom, 2), "secretaria": (c.get("unidadeOrgao") or {}).get("nomeUnidade"),
                               "refs": [], "link": link_compra(c)})
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(VENC, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps({"coletado_em": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "sinais": sinais,
                                 "contratos_lidos": n_contratos, "compras_lidas": n_compras, "compras_com_valor_homologado": n_hom}, ensure_ascii=False), encoding="utf-8")
    cont = {}
    for s in sinais:
        cont[s["tipo"]] = cont.get(s["tipo"], 0) + 1
    print(f"PNCP: {n_contratos} contratos e {n_compras} licitações lidos ({n_hom} com valor homologado); sinais {cont}")
    if n_contratos == 0 and n_compras == 0:
        raise SystemExit("PNCP sem resposta")


if __name__ == "__main__":
    main()
