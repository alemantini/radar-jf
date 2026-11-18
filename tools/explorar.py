import json, re, sys, collections, unicodedata, requests, time
def sa(s): return "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn").lower()
CHUVA = re.compile(r"chuva|calamidad|emergenc|enchente|desabrig|desaloj|defesa civil|deslizament|aluguel social|auxilio.moradia|inundac|temporal|encosta|escorregament|fumecap|cobrade|17\.?693")
HOSP = re.compile(r"hospital|santa casa|maternidade|ascomcer|\bhps\b|pronto.socorro|monte sinai|albert sabin|hu-ufjf|ebserh|casa de saude|fundacao")
CRED = re.compile(r"financiament|operacao de credito|operacoes de credito|bdmg|bndes|caixa economica|emprestim|cidade alta")
R = json.load(open("/tmp/anterior/dados/prefeitura/resumo.json"))
print("fonte atualizada", R.get("fonte_atualizada_em"), "anos", list(R["anos"]))
for ano in ("2025", "2026"):
    B = json.load(open(f"/tmp/anterior/dados/prefeitura/empenhos_{ano}.json"))
    S, E, C = B["secretarias"], B["elementos"], B["credores"]
    reg = B["empenhos"]
    print(f"\n===== {ano}: {len(reg)} empenhos; campos {B['campos']}")
    print("  secretarias:", S[:60])
    def cred(x): return ("PF", "pessoas fisicas") if x[2] < 0 else tuple(C[x[2]])
    def txt(x): return sa(" ".join([S[x[1]], E[x[3]], cred(x)[1], x[6] or ""]))
    ch = [x for x in reg if CHUVA.search(txt(x))]
    print(f"\n--- CHUVAS {ano}: {len(ch)} empenhos, empenhado {sum(x[4] for x in ch):,.0f}, pago {sum(x[5] for x in ch):,.0f}")
    pal = collections.Counter(m.group(0) for x in ch for m in CHUVA.finditer(txt(x))); print("  palavras:", pal.most_common())
    porm = collections.defaultdict(float); poru = collections.defaultdict(float); pore = collections.defaultdict(float); porc = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for x in ch:
        porm[x[0][:7]] += x[5]; poru[S[x[1]]] += x[5]; pore[E[x[3]]] += x[5]
        c = porc[cred(x)]; c[0] += x[4]; c[1] += x[5]; c[2] += 1
    print("  por mes (pago):", {m: round(v) for m, v in sorted(porm.items())})
    print("  por secretaria:", sorted(((round(v), u) for u, v in poru.items()), reverse=True)[:12])
    print("  por elemento:", sorted(((round(v), u) for u, v in pore.items()), reverse=True)[:12])
    print("  credores (emp, pago, n):"); [print("    ", round(v[0]), round(v[1]), v[2], k) for k, v in sorted(porc.items(), key=lambda kv: -kv[1][0])[:30]]
    for x in sorted(ch, key=lambda x: -x[4])[:25]:
        print("   EX:", x[0], round(x[4]), round(x[5]), cred(x)[1][:35], "|", S[x[1]][:30], "|", (x[6] or "")[:170])
    hs = collections.defaultdict(lambda: [0.0, 0.0, collections.defaultdict(float), 0, collections.Counter()])
    for x in reg:
        if x[2] < 0: continue
        c = tuple(C[x[2]])
        if HOSP.search(sa(c[1])):
            H = hs[c]; H[0] += x[4]; H[1] += x[5]; H[2][x[0][:7]] += x[5]; H[3] += 1; H[4][S[x[1]][:30]] += 1
    print(f"\n--- HOSPITAIS {ano}: {len(hs)} credores")
    for c, H in sorted(hs.items(), key=lambda kv: -kv[1][1])[:30]:
        print(f"   pago {round(H[1]):>12,} emp {round(H[0]):>12,} n={H[3]} {c[1][:55]} [{c[0]}] {dict(H[4].most_common(2))}")
        print(f"        meses: { {m: round(v) for m, v in sorted(H[2].items())} }")
    cr = [x for x in reg if CRED.search(txt(x))]
    print(f"\n--- CREDITO {ano}: {len(cr)} empenhos, emp {sum(x[4] for x in cr):,.0f} pago {sum(x[5] for x in cr):,.0f}")
    print("  palavras:", collections.Counter(m.group(0) for x in cr for m in CRED.finditer(txt(x))).most_common())
    for x in sorted(cr, key=lambda x: -x[4])[:25]:
        print("   EX:", x[0], round(x[4]), round(x[5]), cred(x)[1][:35], "|", S[x[1]][:30], "|", E[x[3]][:30], "|", (x[6] or "")[:170])
API = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/"
for ano, per in ((2025, 6), (2026, 5), (2026, 4)):
    try:
        it = requests.get(API + "rreo", params={"an_exercicio": ano, "nr_periodo": per, "co_tipo_demonstrativo": "RREO", "no_anexo": "RREO-Anexo 01", "id_ente": 3136702}, timeout=120).json().get("items", [])
    except Exception as e:
        print("siconfi erro", e); it = []
    print(f"\n--- SICONFI RREO-Anexo 01 {ano} b{per}: {len(it)} linhas")
    for x in it:
        if "opera" in sa(x.get("conta")) and "credito" in sa(x.get("conta")):
            print("   ", x.get("conta"), "|", x.get("coluna"), "|", x.get("valor"))
    time.sleep(1)
for ano in (2026, 2025):
    for per in (3, 2, 1):
        try:
            it = requests.get(API + "rgf", params={"an_exercicio": ano, "in_periodicidade": "Q", "nr_periodo": per, "co_tipo_demonstrativo": "RGF", "no_anexo": "RGF-Anexo 04", "co_esfera": "M", "co_poder": "E", "id_ente": 3136702}, timeout=120).json().get("items", [])
        except Exception as e:
            print("rgf erro", e); it = []
        if it:
            print(f"\n--- RGF Anexo 04 {ano} Q{per}: {len(it)} linhas")
            for x in it: print("   ", x.get("conta"), "|", x.get("coluna"), "|", x.get("valor"))
            break
        time.sleep(1)
