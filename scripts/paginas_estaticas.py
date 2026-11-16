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
"""

GOAT = ('<script>window.goatcounter={path:function(){return location.pathname}}</script>'
        '<script data-goatcounter="https://jflandia.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>')


def pagina(caminho, titulo, descricao, imagem, corpo, msg_zap):
    url = URL + caminho
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
<style>{CSS}</style></head><body>
<div class="top"><a href="/">RADAR <b>JF</b>LÂNDIA</a></div>
<main>
{corpo.replace("<!--ZAP-->", f'<div class="botoes"><a class="btn zap" href="{zap}" target="_blank" rel="noopener">Compartilhar no WhatsApp</a></div>', 1)}
<div class="botoes"><a class="btn zap" href="{zap}" target="_blank" rel="noopener">Compartilhar no WhatsApp</a></div>
</main>
<footer>Radar JFlândia: Câmara e Prefeitura de Juiz de Fora com dados oficiais, atualizado todo dia. Sinal não é prova: confira sempre nos documentos oficiais.
Achou um erro? <a href="mailto:{EMAIL}">{EMAIL}</a>. <a href="/">Página inicial</a>.</footer>
{GOAT}
</body></html>"""


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
<div class="botoes"><a class="btn ver" href="/#/v/{v['id']}">Ver tudo sobre {e(v['apelido'])} no Radar</a><a class="btn ver" href="/#/placar">Montar o meu placar</a></div>"""
        msg = f"Veja o que {v['apelido']} fez na Câmara de Juiz de Fora: {n_br(c.get('total'))} propostas, custo do gabinete e posição no placar. Dados oficiais no Radar JFlândia."
        (SITE / caminho / "index.html").write_text(pagina(caminho, f"{v['apelido']}: o que fez na Câmara de Juiz de Fora | Radar JFlândia",
                                                           desc, URL + caminho + "card.jpg", corpo, msg), encoding="utf-8")
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
                                                           desc, URL + "compartilhar.jpg", corpo, msg), encoding="utf-8")
        urls.append(caminho)
    print(f"{len(urls)} páginas de empresas")
    return urls


def main():
    urls = [""] + vereadores() + empresas()
    hoje = date.today().isoformat()
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{URL}{u}</loc><lastmod>{hoje}</lastmod></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {URL}sitemap.xml\n", encoding="utf-8")
    print(f"sitemap com {len(urls)} endereços")


if __name__ == "__main__":
    main()
