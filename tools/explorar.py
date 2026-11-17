"""Exploração 3: estrutura das audiências e da agenda da Câmara."""
import re, requests, html
H = {"User-Agent": "Mozilla/5.0 RadarJF"}
r = requests.get("https://www.camarajf.mg.gov.br/www/audiencias-publicas", headers=H, timeout=40)
i = r.text.find("Audiências Públicas - ")
if i < 0: i = r.text.find("AUDIÊNCIAS PÚBLICAS</")
print("HTML AUD:", r.text[i-1500:i+5000])
r = requests.get("https://www.camarajf.mg.gov.br/www/agenda-de-reunioes", headers=H, timeout=40)
j = r.text.find("Calendário de Reuniões")
print("HTML AGENDA:", r.text[j:j+4000])
print("tem <table:", r.text.count("<table"), "img:", r.text.count("<img"), "data:image:", r.text.count("data:image"))
