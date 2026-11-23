"""Gera páginas fixas para o Google e para o compartilhamento no WhatsApp.

- site/v/<id>/index.html e site/v/<id>/card.jpg: uma página por vereador, com
  resumo em texto e imagem própria (foto oficial e números) para a prévia do link.
- site/empresa/<cnpj>/index.html: uma página por empresa ou entidade que recebeu
  da Prefeitura, com totais, órgãos, sinais de alerta e últimos lançamentos.
- site/sitemap.xml e site/robots.txt.

Roda no fim da atualização, depois que todos os dados estão em site/dados.
"""
import html
import json
import urllib.parse
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

RAIZ = Path(__file__).resolve().parent.parent
SITE = RAIZ / "site"
DADOS = SITE / "dados"
FONTES = RAIZ / "tools" / "fontes"
URL = "https://jflandia.com.br/"
EMAIL = "radarjflandia@gmail.com"

AZUL, AMARELO, VERMELHO = (11, 37, 69), (242, 183, 5), (255, 90, 95)


def ler(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception as e:  # dado ausente não derruba a geração
        print("sem", p, e)
        return None


def norm(s):
    return unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()


def e(s):
    return html.escape(str(s or ""), quote=True)


def n_br(x):
    return f"{int(round(x or 0)):,}".replace(",", ".")


def reais(x, curto=False):
    x = x or 0
    if curto and abs(x) >= 1e9:
        return f"R$ {x / 1e9:.1f} bi".replace(".", ",")
    if curto and abs(x) >= 1e6:
        return f"R$ {x / 1e6:.1f} mi".replace(".", ",")
    if curto and abs(x) >= 1e3:
        return f"R$ {x / 1e3:.0f} mil"
    return "R$ " + f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def cnpj_fmt(c):
    c = str(c)
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}" if len(c) == 14 else c


def data_br(d):
    d = str(d or "")
    return "/".join(reversed(d.split("-"))) if "-" in d else d


def fonte(peso, tam):
    return ImageFont.truetype(str(FONTES / f"barlow-condensed-latin-{peso}-normal.woff"), tam)


# ---------- molde das páginas ----------
CSS = """
*{box-sizing:border-box}body{margin:0;font-family:Barlow,system-ui,sans-serif;color:#1c2430;background:#f6f7f9;line-height:1.5}
a{color:#0b6b4f}.top{background:#0b2545;color:#fff;padding:12px 18px}.top a{color:#fff;text-decoration:none;font-family:'Barlow Condensed';font-weight:800;font-size:24px}
.top a b{color:#ff5a5f}main{max-width:760px;margin:0 auto;padding:18px}
h1{font-family:'Barlow Condensed';font-weight:800;font-size:38px;line-height:1.05;margin:8px 0 4px;color:#0b2545}
h2{font-family:'Barlow Condensed';font-weight:700;font-size:24px;margin:26px 0 8px;color:#0b2545;border-bottom:3px solid #f2b705;padding-bottom:2px}
.sub{color:#5b6573;font-size:15px}.nums{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0}
.nums span{flex:1 1 150px;background:#fff;border-radius:12px;padding:10px 14px;box-shadow:0 1px 2px rgba(11,37,69,.08);font-size:14px;color:#5b6573}
.nums b{display:block;font-family:'Barlow Condensed';font-size:28px;color:#0b2545;line-height:1.1}
.linha{display:flex;justify-content:space-between;gap:12px;background:#fff;border-radius:10px;padding:9px 13px;margin:6px 0;font-size:15px}
.linha .vl{white-space:nowrap;font-weight:600}.alerta{background:#fff6d6;border-left:5px solid #f2b705;border-radius:8px;padding:10px 13px;margin:8px 0;font-size:15px}
.alerta b{display:block;color:#7a5a00}.lanc{background:#fff;border-radius:10px;padding:9px 13px;margin:6px 0;font-size:14px}
.lanc small{color:#5b6573;display:block}.botoes{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0}
.btn{display:inline-block;padding:13px 18px;border-radius:12px;text-decoration:none;font-weight:700;font-size:16px}
.btn.ver{background:#0b2545;color:#fff}.btn.zap{background:#1f9d55;color:#fff}
.foto{width:96px;height:96px;border-radius:14px;object-fit:cover;float:right;margin:0 0 8px 12px;border:3px solid #f2b705}
footer{max-width:760px;margin:30px auto;padding:0 18px 40px;color:#5b6573;font-size:13px}
.trilha{font-size:13px;color:#5b6573;margin:2px 0 6px}.trilha a{color:#5b6573}.rodape-links{margin-top:10px;font-size:14px}
.lista a{display:flex;justify-content:space-between;gap:12px;background:#fff;border-radius:10px;padding:9px 13px;margin:6px 0;font-size:15px;text-decoration:none;color:#1c2430}
.lista a .vl{white-space:nowrap;font-weight:600;color:#0b2545}.lista a:hover{outline:2px solid #f2b705}
.tema{display:block;background:#fff;border-radius:12px;padding:11px 14px;margin:8px 0;text-decoration:none;color:#1c2430;box-shadow:0 1px 2px rgba(11,37,69,.08)}
.tema b{display:block;color:#0b2545;font-size:17px}.tema span{font-size:14px;color:#5b6573}
"""

GOAT = ('<script>window.goatcounter={path:function(){return location.pathname}}</script>'
        '<script data-goatcounter="https://jflandia.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>')


def trilha_html(trilha):
    if not trilha:
        return ""
    partes = ['<a href="/">Início</a>'] + [f'<a href="/{c}">{e(n)}</a>' if c is not None else f"<span>{e(n)}</span>" for n, c in trilha]
    return '<nav class="trilha" aria-label="Você está em">' + " › ".join(partes) + "</nav>"


def ld_trilha(trilha, caminho, titulo):
    itens = [("Início", "")] + [(n, c if c is not None else caminho) for n, c in trilha]
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": URL + c} for i, (n, c) in enumerate(itens)]}


def pagina(caminho, titulo, descricao, imagem, corpo, msg_zap, trilha=None, ld=None):
    url = URL + caminho
    grafo = ([ld_trilha(trilha, caminho, titulo)] if trilha else []) + (ld or [])
    ld_html = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": grafo}, ensure_ascii=False).replace("</", "<\\/") + "</script>") if grafo else ""
    zap = "https://wa.me/?text=" + html.escape(
        urllib.parse.quote(f"{msg_zap}\n{url}"), quote=True)
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titulo)}</title>
<meta name="description" content="{e(descricao)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Radar JFlândia">
<meta property="og:title" content="{e(titulo)}"><meta property="og:description" content="{e(descricao)}">
<meta property="og:url" content="{url}"><meta property="og:image" content="{imagem}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:locale" content="pt_BR">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0b2545"><link rel="icon" href="/favicon.png">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800&family=Barlow:wght@400;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style>{ld_html}</head><body>
<div class="top"><a href="/">RADAR <b>JF</b>LÂNDIA</a></div>
<main>
{trilha_html(trilha)}
{corpo.replace("<!--ZAP-->", f'<div class="botoes"><a class="btn zap" href="{zap}" target="_blank" rel="noopener">Compartilhar no WhatsApp</a></div>', 1)}
<div class="botoes"><a class="btn zap" href="{zap}" target="_blank" rel="noopener">Compartilhar no WhatsApp</a></div>
</main>
<footer>Radar JFlândia: Câmara e Prefeitura de Juiz de Fora com dados oficiais, atualizado todo dia. Sinal não é prova: confira sempre nos documentos oficiais.
Achou um erro? <a href="mailto:{EMAIL}">{EMAIL}</a>.
<nav class="rodape-links"><a href="/">Página inicial</a> · <a href="/vereadores/">Vereadores</a> · <a href="/empresas/">Quem recebe da Prefeitura</a> · <a href="/temas/">Todos os temas</a></nav></footer>
{GOAT}
</body></html>"""


LISTA_VER, LISTA_EMP = [], []

# ---------- vereadores ----------
CRITERIOS = [("leis", True, 2), ("pedidos", True, 1), ("cobrancas", True, 2), ("emendas", True, 1), ("gabinete", False, 1)]


def emendas_de(v, emendas):
    if not emendas:
        return None
    alvo = norm(v.get("nome"))
    props = emendas.get("proponentes", {})
    k = next((p for p in props if norm(p) == alvo), None) or next((p for p in props if norm(p) in alvo or alvo in norm(p)), None)
    return props[k] if k else None


def placar(atuais, gab, tse, emendas):
    def valor(v, k):
        if k == "emendas":
            em = emendas_de(v, emendas)
            return em["pago"] / em["previsto"] if em and em.get("previsto") else None
        if k == "gabinete":
            g = (gab or {}).get("vereadores", {}).get(str(v["id"]))
            return g["media"] if g else None
        return (v.get("contagem") or {}).get(k, 0)
    faixa = {}
    for k, _, _ in CRITERIOS:
        vals = [x for x in (valor(v, k) for v in atuais) if x is not None]
        faixa[k] = (min(vals), max(vals)) if vals else (0, 0)
    notas = {}
    for v in atuais:
        soma = peso = 0
        for k, mais, p in CRITERIOS:
            x = valor(v, k)
            if x is None:
                continue
            a, b = faixa[k]
            nt = 10 if b == a else 10 * (x - a) / (b - a)
            soma += (nt if mais else 10 - nt) * p
            peso += p
        notas[v["id"]] = soma / peso if peso else None
    ordem = sorted(atuais, key=lambda v: -(notas[v["id"]] if notas[v["id"]] is not None else -1))
    return {v["id"]: i + 1 for i, v in enumerate(ordem)}, notas


def quebra(texto, f, larg, draw):
    linhas, atual = [], ""
    for pal in texto.split():
        t = (atual + " " + pal).strip()
        if draw.textlength(t, font=f) <= larg:
            atual = t
        else:
            linhas.append(atual)
            atual = pal
    return linhas + [atual]


def card_vereador(v, numeros, destino):
    im = Image.new("RGB", (1200, 630), AZUL)
    d = ImageDraw.Draw(im)
    for r, w in ((520, 6), (400, 8), (280, 10)):  # ondas do radar ao fundo
        d.ellipse((1050 - r, -120 - r, 1050 + r, -120 + r), outline=(26, 52, 86), width=w)
    foto = SITE / "fotos" / f"{v['id']}.jpg"
    x0 = 64
    if foto.exists():
        f = ImageOps.fit(Image.open(foto).convert("RGB"), (300, 360), centering=(0.5, 0.3))
        m = Image.new("L", f.size, 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, *f.size), 26, fill=255)
        d.rounded_rectangle((x0 - 6, 70, x0 + 306, 436), 30, fill=AMARELO)
        im.paste(f, (x0, 76), m)
        tx = x0 + 350
    else:
        tx = x0
    fl = fonte(800, 34)
    d.text((tx, 66), "RADAR ", font=fl, fill=(255, 255, 255))
    x1 = tx + d.textlength("RADAR ", font=fl)
    d.text((x1, 66), "JF", font=fl, fill=VERMELHO)
    d.text((x1 + d.textlength("JF", font=fl), 66), "LÂNDIA", font=fl, fill=(255, 255, 255))
    larg = 1200 - tx - 60
    fn = fonte(800, 82)
    linhas = quebra(v["apelido"], fn, larg, d)
    if len(linhas) > 2:
        fn = fonte(800, 62)
        linhas = quebra(v["apelido"], fn, larg, d)[:2]
    y = 112
    for l in linhas:
        d.text((tx, y), l, font=fn, fill=(255, 255, 255))
        y += int(fn.size * 0.98)
    d.text((tx, y + 6), f"Vereador(a){', ' + v['partido'] if v.get('partido') else ''}", font=fonte(600, 34), fill=(201, 214, 232))
    y = 330
    bw = (larg - 2 * 16) // 3
    for i, (val, rot) in enumerate(numeros[:3]):
        bx = tx + i * (bw + 16)
        d.rounded_rectangle((bx, y, bx + bw, y + 116), 18, fill=(30, 56, 92))
        fv = fonte(800, 50)
        while d.textlength(val, font=fv) > bw - 28 and fv.size > 28:
            fv = fonte(800, fv.size - 4)
        d.text((bx + 16, y + 12), val, font=fv, fill=AMARELO)
        d.text((bx + 16, y + 74), rot, font=fonte(600, 24), fill=(201, 214, 232))
    d.rectangle((0, 520, 1200, 630), fill=AMARELO)
    d.text((64, 538), f"jflandia.com.br/v/{v['id']}", font=fonte(800, 56), fill=AZUL)
    d.text((1136, 556), "Só dados oficiais", font=fonte(700, 30), fill=AZUL, anchor="ra")
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.save(destino, quality=86)


def vereadores():
    R = ler(DADOS / "resumo.json")
    if not R:
        return []
    gab, tse, emendas = ler(DADOS / "gabinetes.json"), ler(DADOS / "tse.json"), ler(DADOS / "prefeitura" / "emendas_resumo.json")
    atuais = [v for v in R["vereadores"] if not v.get("fora_da_lista")]
    pos, notas = placar(atuais, gab, tse, emendas)
    urls = []
    for v in atuais:
        c = v.get("contagem") or {}
        g = (gab or {}).get("vereadores", {}).get(str(v["id"]))
        t = (tse or {}).get("vereadores", {}).get(str(v["id"]))
        em = emendas_de(v, emendas)
        numeros = [(n_br(c.get("total")), "propostas")]
        if g:
            numeros.append((reais(g["media"], True), "gabinete por mês"))
        numeros.append((f"{pos[v['id']]}º", "no placar padrão"))
        caminho = f"v/{v['id']}/"
        card_vereador(v, numeros, SITE / caminho / "card.jpg")
        partido = f", {v['partido']}" if v.get("partido") else ""
        desc = (f"{v['apelido']}{partido}: {n_br(c.get('total'))} propostas na Câmara de Juiz de Fora"
                + (f", gabinete com custo médio de {reais(g['media'], True)} por mês" if g else "")
                + f", {pos[v['id']]}º no placar padrão do Radar. Dados oficiais.")
        foto = f'<img class="foto" src="/fotos/{v["id"]}.jpg" alt="Foto oficial de {e(v["apelido"])}">' if (SITE / "fotos" / f"{v['id']}.jpg").exists() else ""
        corpo = f"""{foto}<p class="sub">Vereador(a) de Juiz de Fora</p>
<h1>{e(v['apelido'])}</h1>
<p class="sub">{e(v.get('nome'))}{e(partido)}</p>
<div class="nums">
<span><b>{n_br(c.get('total'))}</b>propostas apresentadas</span>
<span><b>{pos[v['id']]}º de {len(atuais)}</b>no placar padrão do Radar</span>
{f"<span><b>{reais(g['media'], True)}</b>custo médio do gabinete por mês</span>" if g else ""}
{f"<span><b>{n_br(t.get('votos'))}</b>votos em 2024</span>" if t and t.get('votos') else ""}
</div><!--ZAP-->
<h2>O que apresentou na Câmara</h2>
<div class="linha"><span>Propostas de lei</span><span class="vl">{n_br(c.get('leis'))}</span></div>
<div class="linha"><span>Pedidos para os bairros</span><span class="vl">{n_br(c.get('pedidos'))}</span></div>
<div class="linha"><span>Fiscalização e cobranças à Prefeitura</span><span class="vl">{n_br(c.get('cobrancas'))}</span></div>
<div class="linha"><span>Homenagens, moções e nomes de rua</span><span class="vl">{n_br(c.get('homenagens'))}</span></div>
{f'''<h2>Emendas ao orçamento</h2>
<div class="linha"><span>Indicado em {n_br(em.get('n'))} emendas</span><span class="vl">{reais(em.get('previsto'), True)}</span></div>
<div class="linha"><span>Já pago pela Prefeitura</span><span class="vl">{reais(em.get('pago'), True)}</span></div>''' if em else ""}
<p class="sub">O placar padrão dá peso 2 a propostas de lei e fiscalização e peso 1 a pedidos para os bairros, emendas pagas e gabinete econômico. No Radar você muda os pesos e monta o seu ranking.</p>
<div class="botoes"><a class="btn ver" href="/#/v/{v['id']}">Ver tudo sobre {e(v['apelido'])} no Radar</a><a class="btn ver" href="/#/placar">Ver o ranking dos vereadores</a></div>
<h2>Outros vereadores de Juiz de Fora</h2>
<p>{" · ".join(f'<a href="/v/{o["id"]}/">{e(o["apelido"])}</a>' for o in sorted(atuais, key=lambda o: norm(o["apelido"])) if o["id"] != v["id"])}</p>"""
        pessoa = {"@type": "Person", "name": v.get("nome") or v["apelido"], "alternateName": v["apelido"],
                  "jobTitle": "Vereador(a) de Juiz de Fora", "url": URL + caminho,
                  "worksFor": {"@type": "GovernmentOrganization", "name": "Câmara Municipal de Juiz de Fora", "url": "https://www.camarajf.mg.gov.br/"}}
        if v.get("partido"):
            pessoa["affiliation"] = {"@type": "Organization", "name": v["partido"]}
        if (SITE / "fotos" / f"{v['id']}.jpg").exists():
            pessoa["image"] = URL + f"fotos/{v['id']}.jpg"
        LISTA_VER.append((v, c, g, pos[v["id"]], len(atuais)))
        msg = f"Veja o que {v['apelido']} fez na Câmara de Juiz de Fora: {n_br(c.get('total'))} propostas, custo do gabinete e posição no placar. Dados oficiais no Radar JFlândia."
        (SITE / caminho / "index.html").write_text(pagina(caminho, f"{v['apelido']}: o que fez na Câmara de Juiz de Fora | Radar JFlândia",
                                                           desc, URL + caminho + "card.jpg", corpo, msg,
                                                           trilha=[("Vereadores", "vereadores/"), (v["apelido"], None)], ld=[pessoa]), encoding="utf-8")
        urls.append(caminho)
    print(f"{len(urls)} páginas de vereadores")
    return urls


# ---------- empresas ----------
def empresas():
    R = ler(DADOS / "prefeitura" / "resumo.json") or {}
    anos = sorted({int(p.stem.split("_")[1]) for p in (DADOS / "prefeitura").glob("empenhos_*.json")}, reverse=True)
    if not anos:
        return []
    A = ler(DADOS / "prefeitura" / "alertas.json") or {}
    al = defaultdict(list)
    for a in A.get("alertas", []):
        al[a.get("cnpj")].append(a)
    info = {}
    for ano in anos:
        d = ler(DADOS / "prefeitura" / f"empenhos_{ano}.json")
        if not d:
            continue
        for x in d["empenhos"]:
            if x[2] < 0:
                continue
            cnpj, nome = d["credores"][x[2]][0], d["credores"][x[2]][1]
            if not cnpj or len(str(cnpj)) != 14:
                continue
            f = info.setdefault(cnpj, {"nome": nome, "anos": defaultdict(lambda: [0.0, 0.0]), "sec": defaultdict(float), "lanc": []})
            f["anos"][ano][0] += x[4] or 0
            f["anos"][ano][1] += x[5] or 0
            f["sec"][d["secretarias"][x[1]]] += x[5] or 0
            f["lanc"].append((x[0] or "", d["secretarias"][x[1]], x[6] if len(x) > 6 else "", x[4] or 0, x[5] or 0, ano))
    urls = []
    for cnpj, f in info.items():
        pago = sum(v[1] for v in f["anos"].values())
        emp = sum(v[0] for v in f["anos"].values())
        if pago + emp < 1000:
            continue
        caminho = f"empresa/{cnpj}/"
        anos_txt = " e ".join(str(a) for a in sorted(f["anos"]))
        alertas = al.get(cnpj, [])
        desc = (f"{f['nome']} (CNPJ {cnpj_fmt(cnpj)}) recebeu {reais(pago, True)} da Prefeitura de Juiz de Fora em {anos_txt}"
                + (f". {len(alertas)} sinal(is) de alerta no Radar" if alertas else "") + ". Dados oficiais.")
        f["lanc"].sort(key=lambda l: l[0], reverse=True)
        ano_link = max(f["anos"])
        corpo = f"""<p class="sub">Empresa ou entidade que recebe da Prefeitura de Juiz de Fora</p>
<h1>{e(f['nome'])}</h1>
<p class="sub">CNPJ {cnpj_fmt(cnpj)}</p>
<div class="nums">
<span><b>{reais(pago, True)}</b>pagos pela Prefeitura em {anos_txt}</span>
<span><b>{reais(emp, True)}</b>reservados (empenhados)</span>
</div><!--ZAP-->
{"".join(f'<div class="linha"><span>{a}</span><span class="vl">{reais(v[1])} pagos</span></div>' for a, v in sorted(f["anos"].items(), reverse=True))}
{f'<h2>Sinais de alerta</h2>' + "".join(f'<div class="alerta"><b>{e(a.get("titulo"))}</b>{e(a.get("detalhe"))}</div>' for a in alertas) + '<p class="sub">Sinal não é prova. Pode haver explicação legal; vale perguntar à Prefeitura.</p>' if alertas else ""}
<h2>Por órgão da Prefeitura</h2>
{"".join(f'<div class="linha"><span>{e(s)}</span><span class="vl">{reais(v)}</span></div>' for s, v in sorted(f["sec"].items(), key=lambda kv: -kv[1])[:12])}
<h2>Últimos lançamentos</h2>
{"".join(f'<div class="lanc"><small>{data_br(l[0])} · {e(l[1])}</small>{e(str(l[2])[:160])}<small>empenhado {reais(l[3])} · pago {reais(l[4])}</small></div>' for l in f["lanc"][:8])}
<div class="botoes"><a class="btn ver" href="/#/prefeitura/empresa/{ano_link}/{cnpj}">Ver todos os lançamentos no Radar</a><a class="btn ver" href="/#/prefeitura/alertas">Ver todos os sinais de alerta</a></div>
<p class="sub">Fonte: Portal da Transparência da Prefeitura de Juiz de Fora (empenhos), na última versão baixada pelo Radar.</p>"""
        msg = f"Quanto {f['nome']} recebeu da Prefeitura de Juiz de Fora: {reais(pago, True)} pagos em {anos_txt}. Dados oficiais no Radar JFlândia."
        (SITE / caminho).mkdir(parents=True, exist_ok=True)
        (SITE / caminho / "index.html").write_text(pagina(caminho, f"{f['nome']}: quanto recebeu da Prefeitura de Juiz de Fora | Radar JFlândia",
                                                           desc, URL + "compartilhar.jpg", corpo, msg,
                                                           trilha=[("Quem recebe da Prefeitura", "empresas/"), (f["nome"], None)]), encoding="utf-8")
        LISTA_EMP.append((cnpj, f["nome"], pago, len(alertas)))
        urls.append(caminho)
    print(f"{len(urls)} páginas de empresas")
    return urls


# ---------- páginas de entrada (hubs) e de temas ----------
TEMAS = [
    ("Câmara Municipal", [
        ("#/camara", "Vereadores", "O que cada vereador apresentou desde a posse: propostas, pedidos para os bairros, cobranças à Prefeitura e custo do gabinete."),
        ("#/placar", "Ranking dos vereadores", "Placar com pesos que você escolhe: leis, fiscalização, pedidos, emendas pagas e gabinete econômico."),
        ("#/prefeita", "Com a prefeita ou contra?", "Como cada vereador votou nos projetos e vetos que a prefeita enviou à Câmara, lido nas atas oficiais."),
        ("#/votacoes", "Como votaram", "Votações em plenário lidas nas atas oficiais da Câmara."),
        ("#/custo", "Quanto a Câmara custa por morador", "Gasto da Câmara de Juiz de Fora por habitante comparado com cidades de porte parecido."),
        ("#/diarias", "Diárias de viagem", "Diárias de viagem pagas pela Câmara a servidores e motoristas, com motivo, destino e valor."),
        ("#/imoveis", "Imóveis alugados", "Imóveis alugados pela Câmara."),
        ("#/combustivel", "Combustível dos vereadores", "Gastos com combustível dos vereadores, mês a mês."),
        ("#/obra", "O pedido virou obra?", "Pedidos de obra dos vereadores comparados com os gastos e contratos de obra da Prefeitura na mesma rua."),
        ("#/repetidos", "Pedidos que voltam", "Pedidos feitos de novo para a mesma rua porque não foram atendidos."),
        ("#/quente", "Assunto do mês", "O que mais vereadores levaram às reuniões da Câmara em cada mês, contado nas atas."),
        ("#/defende", "Quem defende o quê", "Os assuntos que cada vereador mais levou às reuniões da Câmara, contados nas atas."),
        ("#/busca", "Meu bairro", "Tudo o que os vereadores pediram para a sua rua ou bairro."),
        ("#/agenda", "Agenda da Câmara", "Pauta do plenário do dia e audiências públicas."),
        ("#/atas", "Atas das reuniões", "Atas oficiais das reuniões da Câmara."),
    ]),
    ("Prefeitura", [
        ("#/prefeitura", "Gastos por secretaria", "Para onde vai o dinheiro da Prefeitura de Juiz de Fora, secretaria por secretaria."),
        ("#/prefeitura/fornecedores", "Quem recebe", "Empresas e entidades que mais recebem da Prefeitura."),
        ("#/prefeitura/busca", "Buscar gasto", "Pesquise qualquer gasto da Prefeitura por palavra, empresa ou órgão."),
        ("#/prefeitura/alertas", "Sinais de alerta", "Compras fatiadas, dispensas repetidas, empresas punidas, sócios doadores de campanha e outros sinais que merecem uma pergunta."),
        ("#/prefeitura/supersalarios", "Supersalários", "Servidores da Prefeitura acima do teto e o abate-teto aplicado."),
        ("#/prefeitura/comissionados", "Cargos de confiança", "Comissionados e concursados em função de confiança, por secretaria."),
        ("#/prefeitura/impostometro", "Impostômetro", "Impostos municipais pagos no ano: IPTU, ISS e ITBI, ao vivo."),
        ("#/prefeitura/iptu", "Calculadora do IPTU", "Simule o IPTU do seu imóvel."),
        ("#/prefeitura/emendas", "Emendas dos vereadores", "Dinheiro indicado por cada vereador no orçamento e quanto já foi pago."),
        ("#/prefeitura/combustivel", "Combustível da Prefeitura", "Quanto a Prefeitura paga em combustível, por ano e por órgão."),
        ("#/prefeitura/chuvas", "Dinheiro das chuvas", "Para onde foi o dinheiro ligado às chuvas."),
        ("#/prefeitura/obras", "Obras: previsto x feito", "Orçamento previsto para obras comparado com o que foi executado."),
        ("#/prefeitura/hospitais", "Hospitais", "Quanto a Prefeitura paga aos hospitais."),
        ("#/prefeitura/previdencia", "Previdência", "Multas, juros e débitos parcelados com a previdência dos servidores (JFPREV)."),
        ("#/prefeitura/alugueis", "Imóveis alugados", "Imóveis alugados pela Prefeitura."),
        ("#/prefeitura/emprestimos", "Empréstimos", "Empréstimos da Prefeitura."),
        ("#/prefeitura/aditivos", "Aditivos de contratos", "Contratos que tiveram valor ou prazo aumentado."),
        ("#/prefeitura/creditos", "Orçamento que muda", "Dinheiro do orçamento que muda de lugar durante o ano."),
        ("#/prefeitura/lupa", "Na lupa", "Veículos, diárias, publicidade, shows e eventos."),
        ("#/prefeitura/curiosas", "Coisas curiosas", "Lançamentos que chamam a atenção nos gastos."),
        ("#/prefeitura/placar", "Placar fiscal", "Indicadores fiscais do Município pelo Tesouro Nacional."),
    ]),
]


def escrever(caminho, *a, **k):
    (SITE / caminho).mkdir(parents=True, exist_ok=True)
    (SITE / caminho / "index.html").write_text(pagina(caminho, *a, **k), encoding="utf-8")
    return caminho


def pg_vereadores():
    if not LISTA_VER:
        return []
    itens = sorted(LISTA_VER, key=lambda t: norm(t[0]["apelido"]))
    corpo = f"""<h1>Vereadores de Juiz de Fora</h1>
<p class="sub">Os {len(itens)} vereadores da Câmara Municipal de Juiz de Fora acompanhados pelo Radar nesta legislatura e o que cada um apresentou, com dados oficiais da Câmara.</p><!--ZAP-->
<div class="lista">{"".join(f'<a href="/v/{v["id"]}/"><span>{e(v["apelido"])}{", " + e(v["partido"]) if v.get("partido") else ""}</span><span class="vl">{n_br(c.get("total"))} propostas</span></a>' for v, c, g, pos, n in itens)}</div>
<div class="botoes"><a class="btn ver" href="/#/camara">Abrir o painel da Câmara</a><a class="btn ver" href="/#/placar">Ver o ranking</a></div>
<p class="sub">Fonte: sistema oficial da Câmara Municipal de Juiz de Fora (SAL). Quantidade de propostas não mede qualidade.</p>"""
    ld = [{"@type": "ItemList", "name": "Vereadores de Juiz de Fora", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "url": URL + f"v/{t[0]['id']}/", "name": t[0]["apelido"]} for i, t in enumerate(itens)]}]
    return [escrever("vereadores/", "Vereadores de Juiz de Fora: o que cada um fez na Câmara | Radar JFlândia",
                     f"Lista dos {len(itens)} vereadores de Juiz de Fora com propostas, custo do gabinete e posição no ranking. Dados oficiais da Câmara.",
                     URL + "compartilhar.jpg", corpo, "Veja o que cada vereador de Juiz de Fora fez na Câmara. Dados oficiais no Radar JFlândia.",
                     trilha=[("Vereadores", None)], ld=ld)]


def pg_empresas():
    if not LISTA_EMP:
        return []
    itens = sorted(LISTA_EMP, key=lambda t: -t[2])
    total = sum(t[2] for t in itens)
    corpo = f"""<h1>Quem recebe da Prefeitura de Juiz de Fora</h1>
<p class="sub">{n_br(len(itens))} empresas e entidades que receberam da Prefeitura, em ordem do valor pago. Juntas somam {reais(total, True)} pagos no período baixado pelo Radar. Clique para ver órgãos, lançamentos e sinais de alerta.</p><!--ZAP-->
<div class="lista">{"".join(f'<a href="/empresa/{cnpj}/"><span>{e(nome)}{" ⚠️" if na else ""}</span><span class="vl">{reais(pago, True)}</span></a>' for cnpj, nome, pago, na in itens)}</div>
<p class="sub">⚠️ tem sinal de alerta no Radar. Sinal não é prova. Fonte: Portal da Transparência da Prefeitura de Juiz de Fora (empenhos). Pessoas físicas não aparecem.</p>"""
    return [escrever("empresas/", "Quem recebe da Prefeitura de Juiz de Fora: empresas e valores | Radar JFlândia",
                     f"{n_br(len(itens))} empresas e entidades que receberam da Prefeitura de Juiz de Fora, com valores pagos e sinais de alerta. Dados oficiais.",
                     URL + "compartilhar.jpg", corpo, "Veja quais empresas mais recebem da Prefeitura de Juiz de Fora. Dados oficiais no Radar JFlândia.",
                     trilha=[("Quem recebe da Prefeitura", None)])]


def pg_temas():
    blocos = ""
    for area, temas in TEMAS:
        blocos += f"<h2>{e(area)}</h2>" + "".join(f'<a class="tema" href="/{rota}"><b>{e(nome)}</b><span>{e(d)}</span></a>' for rota, nome, d in temas)
    corpo = f"""<h1>Tudo o que o Radar JFlândia mostra</h1>
<p class="sub">Câmara Municipal e Prefeitura de Juiz de Fora em um só lugar, só com dados oficiais e atualizado todo dia.</p>
<p>Páginas fixas: <a href="/vereadores/">vereadores</a>, <a href="/empresas/">quem recebe da Prefeitura</a>, <a href="/supersalarios/">supersalários</a>, <a href="/cargos-de-confianca/">cargos de confiança</a> e <a href="/custo-da-camara/">custo da Câmara por morador</a>.</p><!--ZAP-->
{blocos}"""
    return [escrever("temas/", "Câmara e Prefeitura de Juiz de Fora: todos os temas do Radar JFlândia",
                     "Vereadores, gastos da Prefeitura, supersalários, cargos de confiança, impostômetro, emendas, sinais de alerta e mais, com dados oficiais de Juiz de Fora.",
                     URL + "compartilhar.jpg", corpo, "Tudo sobre a Câmara e a Prefeitura de Juiz de Fora, com dados oficiais, no Radar JFlândia.",
                     trilha=[("Todos os temas", None)])]


def dado(nome):
    for base in (DADOS / "prefeitura", RAIZ / "data" / "prefeitura", DADOS, RAIZ / "data"):
        if (base / nome).exists():
            return ler(base / nome)
    return None


def pg_supersalarios():
    S = dado("supersalarios.json")
    if not S:
        return []
    ab = S.get("abate") or {}
    corpo = f"""<p class="sub">Prefeitura de Juiz de Fora · competência {e(S['competencia'])}</p>
<h1>Supersalários na Prefeitura de Juiz de Fora</h1>
<p>O Radar leu a planilha oficial com todos os {n_br(S['servidores'])} pagamentos de servidores da Prefeitura na competência {e(S['competencia'])} e comparou com o teto: o salário da prefeita, {reais(S['teto'])}. Para os procuradores municipais o teto é 90,25% do salário de ministro do STF, {reais(S['teto_procurador'])}.</p>
<div class="nums">
<span><b>{n_br(S['com_retencao'])}</b>servidores com abate-teto aplicado pela Prefeitura</span>
<span><b>{reais(ab.get('total', 0), True)}</b>cortados pelo abate-teto no mês</span>
<span><b>{n_br(len(S.get('acima') or []))}</b>acima do teto pela conta do Radar</span>
</div><!--ZAP-->
<h2>Como a conta é feita</h2>
<p>Contam para o teto o salário do cargo, as verbas permanentes, a função gratificada e os honorários, menos o abate-teto. A conta é conservadora: quando as parcelas da planilha não fecham com o bruto, o Radar usa o menor valor. 13º, férias, abono e verbas temporárias ficam de fora.</p>
<div class="botoes"><a class="btn ver" href="/#/prefeitura/supersalarios">Ver a lista completa no Radar</a></div>
<p class="sub">Fonte: {e(S.get('fonte'))}, baixada em {data_br(S.get('baixado_em'))}.</p>"""
    return [escrever("supersalarios/", f"Supersalários na Prefeitura de Juiz de Fora ({S['competencia']}) | Radar JFlândia",
                     f"Quem ganha acima do teto na Prefeitura de Juiz de Fora: {S['com_retencao']} servidores com abate-teto e {len(S.get('acima') or [])} acima do teto pela conta do Radar ({S['competencia']}). Dados oficiais.",
                     URL + "compartilhar.jpg", corpo, "Supersalários na Prefeitura de Juiz de Fora, com dados oficiais, no Radar JFlândia.",
                     trilha=[("Todos os temas", "temas/"), ("Supersalários", None)])]


def pg_comissionados():
    C = dado("comissionados.json")
    if not C:
        return []
    pes = C.get("pessoas") or []
    nc = sum(1 for x in pes if x[6] == "c")
    nf = sum(1 for x in pes if x[6] == "f")
    por = defaultdict(int)
    for x in pes:
        por[x[2]] += 1
    sig = C.get("siglas") or {}
    linhas = "".join(f'<div class="linha"><span>{e(sig.get(k, k))}</span><span class="vl">{n}</span></div>' for k, n in sorted(por.items(), key=lambda kv: -kv[1]))
    corpo = f"""<p class="sub">Prefeitura de Juiz de Fora · competência {e(C['competencia'])}</p>
<h1>Cargos de confiança na Prefeitura de Juiz de Fora</h1>
<p>Quantas pessoas ocupam cargos de confiança na Prefeitura, pela planilha oficial de servidores da competência {e(C['competencia'])}.</p>
<div class="nums">
<span><b>{n_br(nc)}</b>comissionados (vínculo comissionado)</span>
<span><b>{n_br(nf)}</b>concursados em função de confiança</span>
<span><b>{n_br(nc + nf)}</b>no total</span>
</div><!--ZAP-->
<h2>Por órgão</h2>{linhas}
<div class="botoes"><a class="btn ver" href="/#/prefeitura/comissionados">Ver cargos e salários no Radar</a></div>
<p class="sub">Fonte: {e(C.get('fonte'))}, baixada em {data_br(C.get('baixado_em'))}.</p>"""
    return [escrever("cargos-de-confianca/", f"Cargos de confiança na Prefeitura de Juiz de Fora ({C['competencia']}) | Radar JFlândia",
                     f"{nc} comissionados e {nf} concursados em função de confiança na Prefeitura de Juiz de Fora ({C['competencia']}), por órgão. Dados oficiais.",
                     URL + "compartilhar.jpg", corpo, "Cargos de confiança na Prefeitura de Juiz de Fora, com dados oficiais, no Radar JFlândia.",
                     trilha=[("Todos os temas", "temas/"), ("Cargos de confiança", None)])]


def pg_custo_camara():
    D = dado("camara_comparada.json")
    if not D:
        return []
    ano = max((a for a in ("2026", "2025", "2024") if any(c.get(a) for c in D["cidades"])), default=None)
    if not ano:
        return []
    todas = sorted(((c[ano]["leg"] / c["pop"], c) for c in D["cidades"] if c.get(ano) and c[ano].get("leg") and c.get("pop")), key=lambda t: t[0])
    pos = next((i for i, (_, c) in enumerate(todas) if c["cod"] == D["jf"]), None)
    if pos is None:
        return []
    pc, jf = todas[pos]
    vals = sorted(t[0] for t in todas)
    m = len(vals) // 2
    med = vals[m] if len(vals) % 2 else (vals[m - 1] + vals[m]) / 2
    mais = todas[-1]
    corpo = f"""<p class="sub">Câmara Municipal de Juiz de Fora · {ano}</p>
<h1>Quanto a Câmara de Juiz de Fora custa por morador</h1>
<div class="nums">
<span><b>{reais(pc)}</b>por morador em {ano}</span>
<span><b>{reais(jf[ano]['leg'], True)}</b>gastos pela Câmara no ano</span>
<span><b>{pos + 1}ª de {len(todas)}</b>mais barata do grupo comparado</span>
</div><!--ZAP-->
<p>A mediana do grupo foi {reais(med)} por morador. A mais cara foi {e(mais[1]['nome'])} ({e(mais[1]['uf'])}), com {reais(mais[0])}.</p>
<p class="sub">Grupo: {e(D.get('grupo'))}.</p>
<div class="botoes"><a class="btn ver" href="/#/custo">Ver a comparação completa no Radar</a></div>
<p class="sub">Fonte: {e(D.get('fonte'))}; população: {e(D.get('pop_fonte'))}.</p>"""
    return [escrever("custo-da-camara/", f"Quanto a Câmara de Juiz de Fora custa por morador ({ano}) | Radar JFlândia",
                     f"A Câmara de Juiz de Fora custou {reais(pc)} por morador em {ano}, {pos + 1}ª mais barata de {len(todas)} cidades comparadas. Dados do Tesouro Nacional.",
                     URL + "compartilhar.jpg", corpo, "Quanto a Câmara de Juiz de Fora custa por morador, comparada com outras cidades. Radar JFlândia.",
                     trilha=[("Todos os temas", "temas/"), ("Custo da Câmara", None)])]


def extras():
    urls = []
    for f in (pg_vereadores, pg_empresas, pg_temas, pg_supersalarios, pg_comissionados, pg_custo_camara):
        try:
            urls += f()
        except Exception as erro:  # uma página com problema não derruba as outras
            print("falhou", f.__name__, erro)
    print(f"{len(urls)} páginas de entrada e temas")
    return urls


def main():
    urls = [""] + vereadores() + empresas()
    urls = urls[:1] + extras() + urls[1:]
    hoje = date.today().isoformat()
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{URL}{u}</loc><lastmod>{hoje}</lastmod></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {URL}sitemap.xml\n", encoding="utf-8")
    print(f"sitemap com {len(urls)} endereços")


if __name__ == "__main__":
    main()
