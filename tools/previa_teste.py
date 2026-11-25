"""Prévia da página #/teste com os dados publicados: serve /tmp/previa e tira prints (celular)."""
import json, re, subprocess, sys, time
from playwright.sync_api import sync_playwright
RAIZ = sys.argv[1] if len(sys.argv) > 1 else "/tmp/previa"
SAIDA = "tools/prints-teste"
srv = subprocess.Popen([sys.executable, "-m", "http.server", "8765", "-d", RAIZ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)
RUIM = re.compile(r"\bundefined\b|\bNaN\b|\bnull\b|\[object")
rel = {"erros": [], "texto_ruim": [], "passos": []}
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        pg.on("pageerror", lambda e: rel["erros"].append(str(e)[:300]))
        def foto(nome):
            pg.wait_for_timeout(800)
            pg.screenshot(path=f"{SAIDA}/{nome}.png", full_page=True)
            t = pg.inner_text("#app")
            for m in RUIM.finditer(t):
                rel["texto_ruim"].append(f"{nome}: ...{t[max(0, m.start()-60):m.end()+20]}...")
            rel["passos"].append(nome)
        pg.goto("http://localhost:8765/#/", wait_until="networkidle"); foto("0-inicio")
        pg.goto("http://localhost:8765/#/teste/1", wait_until="networkidle"); pg.wait_for_timeout(2000); foto("1-parte1")
        pg.click("#tt-ver1"); foto("2-parte1-vazio")
        qs = pg.query_selector_all(".tt-q")
        for i, q in enumerate(qs):
            q.query_selector('button[data-r="%s"]' % ["sim", "nao", "pular"][i % 3]).click()
        pg.click("#tt-ver1"); foto("3-parte1-resultado")
        pg.click('#tt-partes a[data-p="2"]'); pg.wait_for_timeout(800); foto("4-parte2")
        pg.fill("#tt-bairro", "sao pedro")
        for t in ["Saúde", "Esgoto e drenagem"]:
            pg.click(f'.tt-temas button[data-t="{t}"]')
        pg.click("#tt-ver2"); foto("5-parte2-resultado")
        pg.fill("#tt-bairro", "Bairro Que Nao Existe")
        pg.click("#tt-ver2"); foto("6-parte2-sem-bairro")
        rel["resultado2"] = pg.inner_text("#tt-res2")[:1500]
        pg.goto("http://localhost:8765/#/teste/1", wait_until="networkidle"); pg.wait_for_timeout(1500)
        rel["resultado1_texto"] = ""
        b.close()
finally:
    srv.terminate()
json.dump(rel, open(f"{SAIDA}/relatorio.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(rel, ensure_ascii=False, indent=1))
