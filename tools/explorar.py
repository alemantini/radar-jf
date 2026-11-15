"""Exploração: folha da Câmara por gabinete (sem imprimir nomes)."""
import json, requests
UA = {"User-Agent": "RadarJF/1.0 (robo de transparencia; https://github.com/alemantini/radar-jf)"}
B = "https://www.camarajf.mg.gov.br/transparencia/lista_servidor.php"
for setor in ["91", "7", ""]:
    p = {"codcetil": "", "mesref": "10/2026", "mes": "10", "ano": "2026", "nome": "", "codsetor": setor, "codfuncao": ""}
    r = requests.get(B, params=p, headers=UA, timeout=120)
    print("== setor", setor, r.status_code, len(r.text), r.headers.get("content-type"))
    try:
        d = r.json()
    except Exception:
        print(r.text[:800]); continue
    print(type(d), (list(d.keys())[:20] if isinstance(d, dict) else len(d)))
    lst = d if isinstance(d, list) else next((v for v in d.values() if isinstance(v, list)), [])
    print("linhas:", len(lst))
    for x in lst[:3]:
        if isinstance(x, dict):
            print({k: (v if not any(t in k.lower() for t in ("nome", "cpf", "matric")) else "<omitido>") for k, v in x.items()})
        else:
            print(str(x)[:300])
