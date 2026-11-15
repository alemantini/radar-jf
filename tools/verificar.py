"""Confere o site publicado: abre cada página (celular), segue os links internos
e aponta erros de JavaScript, arquivos que não carregam e páginas vazias."""
import re
import sys
import urllib.request
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://jflandia.com.br/"
RUIM = re.compile(r"Não foi possível|ainda (está|não foi|não)|sendo feita|Carregando|undefined|NaN|null|\[object", re.I)
INICIAIS = ["", "#/camara", "#/placar", "#/busca", "#/repetidos", "#/sobre", "#/apoie", "#/prefeitura",
            "#/prefeitura/alertas", "#/prefeitura/impostometro", "#/prefeitura/placar", "#/prefeitura/comissionados",
            "#/prefeitura/emendas", "#/prefeitura/fornecedores", "#/prefeitura/busca"]
LIMITE = 140

problemas = []


def checa_http():
    for u in ["http://jflandia.com.br/", "https://www.jflandia.com.br/", "https://alemantini.github.io/radar-jf/",
              BASE + "manifest.webmanifest", BASE + "sw.js", BASE + "icone-192.png", BASE + "dados/resumo.json"]:
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "RadarJF-verificacao"}), timeout=30)
            print(f"HTTP {r.status} {u} -> {r.geturl()}")
            if not r.geturl().startswith("https://jflandia.com.br/"):
                problemas.append(f"{u} terminou em {r.geturl()}")
        except Exception as e:
            problemas.append(f"{u}: {e}")
            print(f"HTTP ERRO {u}: {e}")


def main():
    checa_http()
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 390, "height": 844})
        erros, falhas = [], []
        pg.on("pageerror", lambda e: erros.append(str(e)[:200]))
        pg.on("response", lambda r: r.status >= 400 and "jflandia" in r.url and falhas.append(f"{r.status} {r.url}"))
        fila, vistos = list(INICIAIS), set()
        while fila and len(vistos) < LIMITE:
            h = fila.pop(0)
            if h in vistos:
                continue
            vistos.add(h)
            erros.clear(); falhas.clear()
            try:
                pg.goto(BASE + "?v=verif" + h, wait_until="networkidle", timeout=60000)
            except Exception as e:
                problemas.append(f"{h or 'inicio'}: não abriu ({e})")
                continue
            pg.wait_for_timeout(1500)
            txt = pg.inner_text("#app")
            ruins = sorted(set(m.group(0) for m in RUIM.finditer(txt)))
            linhas = len(txt.strip().splitlines())
            status = []
            if erros: status.append("JS: " + " | ".join(erros))
            if falhas: status.append("arquivos: " + ", ".join(sorted(set(falhas))))
            if ruins: status.append("texto suspeito: " + ", ".join(ruins))
            if linhas < 4: status.append(f"página quase vazia ({linhas} linhas)")
            print(f"{'PROBLEMA' if status else 'ok'}  {h or '#/ (início)'}  [{linhas} linhas] {' ; '.join(status)}")
            if status:
                problemas.append(f"{h or 'início'}: {' ; '.join(status)}")
            links = pg.eval_on_selector_all("a[href^='#/']", "els => els.map(e => e.getAttribute('href'))")
            for l in links:
                base_l = l
                # um exemplo de cada tipo de página com parâmetro basta
                tipo = re.sub(r"/[^/]+$", "/*", l) if l.count("/") >= 3 else l
                if l not in vistos and l not in fila and not any(re.sub(r"/[^/]+$", "/*", x) == tipo and x != l for x in vistos | set(fila) if x.count("/") >= 3) :
                    fila.append(base_l)
        b.close()
    print(f"\nPáginas abertas: {len(vistos)}")
    print(f"PROBLEMAS ({len(problemas)}):")
    for x in problemas:
        print(" -", x)


if __name__ == "__main__":
    main()
