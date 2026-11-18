import json, re, sys, collections, unicodedata, requests, time
sys.path.insert(0, "scripts")
from prefeitura_despesas import baixar, BASE, numero, data_iso, mes_num, tipo_credor, conserta
def sa(s): return "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn").lower()
CHUVA = re.compile(r"chuva|calamidad|emergenc|enchente|desabrig|desaloj|defesa civil|deslizament|aluguel social|auxilio.moradia|inundac|temporal|encosta|escorregament")
HOSP = re.compile(r"hospital|santa casa|maternidade|ascomcer|hps\b|pronto socorro|clinica|instituto oncolog|fundacao .*saude")
CRED = re.compile(r"financiament|operacao de credito|operacoes de credito|bdmg|bndes|caixa economica|emprestim")
for ano in (2025, 2026):
    reg = json.loads(baixar(f"{BASE}/arquivos/despesas_{str(ano)[-2:]}.json").decode("utf-8", "replace"))
    reg = reg if isinstance(reg, list) else next(v for v in reg.values() if isinstance(v, list))
    print(f"\n===== {ano}: {len(reg)} registros")
    print("CAMPOS:", list(reg[0].keys()))
    pj = next(x for x in reg if tipo_credor(x.get("cpf/cnpj"))[0] == "pj")
    print("EXEMPLO:", json.dumps(pj, ensure_ascii=False)[:1500])
    # valores distintos de campos categóricos
    for k in reg[0].keys():
        vals = collections.Counter(str(x.get(k))[:60] for x in reg[:20000])
        if 1 < len(vals) <= 40:
            print(f"  [{k}] {len(vals)} valores:", dict(vals.most_common(40)))
    # chuvas
    ch = [x for x in reg if CHUVA.search(sa(" ".join(str(x.get(k) or "") for k in x)))]
    print(f"\n--- CHUVAS {ano}: {len(ch)} empenhos, pago R$ {sum(numero(x.get('pago')) for x in ch):,.0f}, empenhado R$ {sum(numero(x.get('empenhado')) for x in ch):,.0f}")
    pal = collections.Counter()
    for x in ch:
        t = sa(" ".join(str(x.get(k) or "") for k in x))
        for m in CHUVA.finditer(t): pal[m.group(0)] += 1
    print("  palavras:", pal.most_common())
    porm = collections.defaultdict(float); porc = collections.defaultdict(lambda: [0.0, 0, ""]); poru = collections.defaultdict(float)
    for x in ch:
        p = numero(x.get("pago")); porm[mes_num(x.get("mes"))] += p; poru[str(x.get("unidade orcamentaria"))[:50]] += p
        t, c = tipo_credor(x.get("cpf/cnpj"))
        k = (c, conserta(x.get("nome do credor"))[:50]) if t == "pj" else ("PF", "pessoas fisicas")
        porc[k][0] += p; porc[k][1] += 1
    print("  por mes:", {m: round(v) for m, v in sorted(porm.items())})
    print("  por unidade:", sorted(((round(v), u) for u, v in poru.items()), reverse=True)[:12])
    print("  credores:", sorted(((round(v[0]), v[1], k[1]) for k, v in porc.items()), reverse=True)[:25])
    for x in sorted((x for x in ch if tipo_credor(x.get("cpf/cnpj"))[0] == "pj"), key=lambda x: -numero(x.get("empenhado")))[:15]:
        print("   EX:", data_iso(x.get("data do empenho")), round(numero(x.get("empenhado"))), conserta(x.get("nome do credor"))[:40], "|", re.sub(r"\s+", " ", conserta(x.get("historico")))[:220])
    # hospitais
    hs = collections.defaultdict(lambda: [0.0, collections.defaultdict(float), 0, set()])
    for x in reg:
        t, c = tipo_credor(x.get("cpf/cnpj"))
        if t != "pj": continue
        n = sa(conserta(x.get("nome do credor")))
        if HOSP.search(n):
            H = hs[(c, conserta(x.get("nome do credor"))[:60])]; p = numero(x.get("pago"))
            H[0] += p; H[1][mes_num(x.get("mes"))] += p; H[2] += 1; H[3].add(str(x.get("unidade orcamentaria"))[:40])
    print(f"\n--- HOSPITAIS {ano}: {len(hs)} credores")
    for (c, n), H in sorted(hs.items(), key=lambda kv: -kv[1][0])[:25]:
        print(f"   {round(H[0]):>12,} {n} [{c}] n={H[2]} meses={ {m: round(v) for m, v in sorted(H[1].items())} } uo={list(H[3])[:3]}")
    # credito
    cr = [x for x in reg if CRED.search(sa(" ".join(str(x.get(k) or "") for k in x)))]
    print(f"\n--- CREDITO {ano}: {len(cr)} empenhos, pago R$ {sum(numero(x.get('pago')) for x in cr):,.0f}")
    pal = collections.Counter()
    for x in cr:
        for m in CRED.finditer(sa(" ".join(str(x.get(k) or "") for k in x))): pal[m.group(0)] += 1
    print("  palavras:", pal.most_common())
    for x in sorted(cr, key=lambda x: -numero(x.get("empenhado")))[:15]:
        print("   EX:", data_iso(x.get("data do empenho")), round(numero(x.get("empenhado"))), conserta(x.get("nome do credor"))[:40], "|", str(x.get("unidade orcamentaria"))[:30], "|", re.sub(r"\s+", " ", conserta(x.get("historico")))[:200])
# Siconfi: operacoes de credito
API = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/"
for ano, per in ((2025, 6), (2026, 5), (2026, 4)):
    for dem, anexo, tipo in (("rreo", "RREO-Anexo 01", "RREO"), ):
        try:
            r = requests.get(API + dem, params={"an_exercicio": ano, "nr_periodo": per, "co_tipo_demonstrativo": tipo, "no_anexo": anexo, "id_ente": 3136702}, timeout=120)
            it = r.json().get("items", [])
        except Exception as e:
            print("siconfi erro", e); it = []
        print(f"\n--- SICONFI {anexo} {ano} p{per}: {len(it)} linhas")
        for x in it:
            if re.search(r"opera", sa(x.get("conta"))) and re.search(r"credito", sa(x.get("conta"))):
                print("   ", x.get("conta"), "|", x.get("coluna"), "|", x.get("valor"))
        time.sleep(1)
for ano in (2025, 2026):
    for per in (3, 2, 1):
        try:
            r = requests.get(API + "rgf", params={"an_exercicio": ano, "in_periodicidade": "Q", "nr_periodo": per, "co_tipo_demonstrativo": "RGF", "no_anexo": "RGF-Anexo 04", "co_esfera": "M", "co_poder": "E", "id_ente": 3136702}, timeout=120)
            it = r.json().get("items", [])
        except Exception as e:
            print("rgf erro", e); it = []
        if it:
            print(f"\n--- RGF Anexo 04 {ano} Q{per}: {len(it)} linhas")
            for x in it[:80]:
                print("   ", x.get("conta"), "|", x.get("coluna"), "|", x.get("valor"))
            break
