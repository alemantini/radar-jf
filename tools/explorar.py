"""Conferência: histórico do placar fiscal publicado."""
import json, requests
d = requests.get("https://jflandia.com.br/dados/prefeitura/indices.json", headers={"User-Agent": "RadarJF/1.0"}, timeout=120).json()
print("COLETADO", d.get("coletado_em"))
for h in d.get("historico") or []: print("HIST", json.dumps(h, ensure_ascii=False))
print("PESSOAL", d.get("pessoal"))
