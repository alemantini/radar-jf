"""Conferência: combustível publicado."""
import requests
j = requests.get("https://jflandia.com.br/dados/prefeitura/combustivel.json", headers={"User-Agent": "RadarJF/1.0"}, timeout=60).json()
for a, x in j["anos"].items():
    print("CONF", a, round(x["pago"]), round(x["empenhado"]), [f[1] for f in x["fornecedores"]])
