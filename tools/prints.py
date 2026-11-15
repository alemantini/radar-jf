"""Tira prints do site publicado (celular) para conferência."""
import sys
from playwright.sync_api import sync_playwright
BASE = "https://alemantini.github.io/radar-jf/?v=conferir"
PAGS = sys.argv[1:] or ["#/placar", "#/prefeitura/placar", "#/v/24"]
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    for i, h in enumerate(PAGS):
        pg.goto(BASE + h, wait_until="networkidle")
        pg.wait_for_timeout(2500)
        pg.screenshot(path=f"tools/prints/{i}.png", full_page=True)
        print(h, "ok")
    print("erros JS:", erros)
    b.close()
