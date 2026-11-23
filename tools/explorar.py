"""Exploração 4: roda o script do combustível nos arquivos publicados e mostra o resultado."""
import json, subprocess, sys, requests
from pathlib import Path
UA = {"User-Agent": "RadarJF/1.0 (robo de transparencia; https://github.com/alemantini/radar-jf)"}
d = Path("/tmp/pref"); d.mkdir(exist_ok=True)
for ano in (2025, 2026):
    (d / f"empenhos_{ano}.json").write_bytes(requests.get(f"https://jflandia.com.br/dados/prefeitura/empenhos_{ano}.json", headers=UA, timeout=120).content)
subprocess.run([sys.executable, "tools/combustivel_teste.py", str(d)], check=True)
j = json.loads((d / "combustivel.json").read_text())
for a, x in j["anos"].items():
    print("\n==", a, {k: x[k] for k in ("ate", "empenhado", "pago", "empenhos", "com_lubrificante")})
    print("tipos", x["tipos"]); print("secretarias", x["secretarias"]); print("fornecedores", x["fornecedores"])
    for m in x["maiores"][:12]: print("  ", m)
print("JSON_INICIO"); print(json.dumps(j, ensure_ascii=False)); print("JSON_FIM")
