"""Confere o site publicado: abre todas as páginas e anota erros."""
import subprocess, sys, os, re, time, json, hashlib, urllib.request

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "playwright"], check=True)
subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"], check=True,
               stdout=subprocess.DEVNULL)
subprocess.run(["bash", "tools/versao_anterior.sh"], check=False)
# versao_anterior escolhe a mais recente com gastos; é a publicada
RAIZ = "/tmp/anterior"
srv = subprocess.Popen([sys.executable, "-m", "http.server", "8800", "-d", RAIZ],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)

# 1) o site no ar é igual ao artefato?
for f in ["index.html", "app.js", "prefeitura.js", "estilo.css"]:
    try:
        req = urllib.request.Request(f"https://jflandia.com.br/{f}?v={time.time()}", headers={"User-Agent": "Mozilla/5.0"})
        no_ar = urllib.request.urlopen(req, timeout=30).read()
        local = open(f"{RAIZ}/{f}", "rb").read()
        print(f"AR {f}: {'igual' if no_ar == local else 'DIFERENTE'} ({len(no_ar)} bytes)")
    except Exception as e:
        print(f"AR {f}: ERRO {e}")

# 2) arquivos de dados: datas
for f in ["dados/resumo.json", "dados/executivo.json", "dados/atas.json", "dados/diarias.json", "dados/combustivel.json"]:
    try:
        d = json.load(open(f"{RAIZ}/{f}"))
        print("DADO", f, {k: d.get(k) for k in ("gerado", "gerado_em", "atualizado", "ultima_ata", "dados_ate") if isinstance(d, dict) and k in d})
    except Exception as e:
        print("DADO", f, "ERRO", e)

from playwright.sync_api import sync_playwright
vistos, fila, problemas = set(), ["#/"], []
def chave(h):
    h = re.sub(r"#/v/\d+.*", "#/v/N", h)
    h = re.sub(r"#/grupo/.*", "#/grupo/X", h)
    h = re.sub(r"#/prefeitura/s/.*", "#/prefeitura/s/X", h)
    h = re.sub(r"#/prefeitura/busca/.+", "#/prefeitura/busca/X", h)
    h = re.sub(r"#/busca/.+", "#/busca/X", h)
    h = re.sub(r"#/prefeita/\d+", "#/prefeita/N", h)
    h = re.sub(r"#/diarias/.+", "#/diarias/X", h)
    h = re.sub(r"#/combustivel/.+", "#/combustivel/X", h)
    h = re.sub(r"#/atas/.+", "#/atas/X", h)
    h = re.sub(r"#/defende/.+", "#/defende/X", h)
    h = re.sub(r"#/quente/.+", "#/quente/X", h)
    h = re.sub(r"#/votacoes/.+", "#/votacoes/X", h)
    h = re.sub(r"#/repetidos/.+", "#/repetidos/X", h)
    h = re.sub(r"#/obra/.+", "#/obra/X", h)
    h = re.sub(r"#/prefeitura/(\w+)/.+", r"#/prefeitura/\1/X", h)
    return h
padroes = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    for largura in (1280, 400):
        vistos.clear(); fila[:] = ["#/"]; padroes.clear()
        pg = b.new_page(viewport={"width": largura, "height": 900})
        erros = []
        pg.on("pageerror", lambda e: erros.append("JS: " + str(e)[:200]))
        pg.on("console", lambda m: erros.append("CONSOLE: " + m.text[:200]) if m.type == "error" else None)
        pg.on("response", lambda r: erros.append(f"HTTP {r.status}: {r.url[:150]}") if r.status >= 400 and "localhost" in r.url else None)
        n = 0
        while fila and n < 260:
            h = fila.pop(0)
            k = chave(h)
            if h in vistos or padroes.get(k, 0) >= 2:
                continue
            vistos.add(h); padroes[k] = padroes.get(k, 0) + 1; n += 1
            erros.clear()
            try:
                pg.goto(f"http://localhost:8800/{h}", wait_until="load", timeout=30000)
                pg.wait_for_timeout(1800)
                txt = pg.inner_text("#app") if pg.query_selector("#app") else pg.inner_text("body")
            except Exception as e:
                problemas.append((largura, h, "FALHA AO ABRIR " + str(e)[:150])); continue
            avisos = list(erros)
            for frase in ["Não foi possível", "Carregando", "undefined", "NaN", "null", "[object Object]", "Erro", "ainda estão sendo preparados", "Infinity"]:
                if re.search(r"(?<![\w])" + re.escape(frase) + r"(?![\w])", txt):
                    avisos.append(f"TEXTO '{frase}'")
            if len(txt.strip()) < 80:
                avisos.append("PÁGINA QUASE VAZIA")
            # largura estourada
            if largura == 400:
                w = pg.evaluate("document.documentElement.scrollWidth")
                if w > 410:
                    el = pg.evaluate("""(()=>{let m=null,mw=0;document.querySelectorAll('#app *').forEach(e=>{const r=e.getBoundingClientRect();if(r.right>mw&&r.width<2000){mw=r.right;m=e}});return m?(m.tagName+'.'+m.className).slice(0,80)+' '+Math.round(mw):''})()""")
                    avisos.append(f"LARGURA {w}px (mais largo: {el})")
            for a in avisos:
                problemas.append((largura, h, a))
            for href in pg.eval_on_selector_all("a[href^='#/']", "els=>els.map(e=>e.getAttribute('href'))"):
                href = href.split("?")[0]
                if href not in vistos and chave(href) not in [chave(x) for x in fila][:0] and padroes.get(chave(href), 0) < 2:
                    fila.append(href)
        print(f"== largura {largura}: {n} páginas abertas")
        pg.close()
    b.close()
srv.terminate()
print("== PROBLEMAS:", len(problemas))
vistos_p = set()
for l, h, a in problemas:
    key = (l, chave(h), a[:60])
    if key in vistos_p: continue
    vistos_p.add(key)
    print(f"P [{l}] {h} | {a}")
