import sys, random, time, json, requests
sys.path.insert(0, "scripts")
import prefeitura_creditos as pc
lista = pc.decretos_de_credito()
print("decretos", len(lista))
random.seed(7)
amostra = random.sample(lista, 30) + [a for a in lista if "extraordin" in pc.sa(a["texto"])][:4]
s = requests.Session(); ok = 0; ruins = []
for a in amostra:
    t = pc.texto_do_ato(s, a["id"]); d = pc.interpretar(t)
    sp = sum(v for _, v, _ in d["para"]); sd = sum(v for _, v, _ in d["de"])
    bate_p = d["valor"] and abs(sp - d["valor"]) < 1
    bate_d = (not d["de"]) or abs(sd - d["valor"]) < 1
    ok += bool(bate_p and bate_d)
    print(f"\n{a['id']} {a['data']} {d['tipo']} valor={d['valor']} para={sp:.2f} ({len(d['para'])}) de={sd:.2f} ({len(d['de'])}) fontes={d['fontes']} {'OK' if bate_p and bate_d else 'DIFERENTE'}")
    print("   para:", [(n, v) for n, v, _ in d["para"]][:5]); print("   de:", [(n, v) for n, v, _ in d["de"]][:5])
    if not (bate_p and bate_d): print("   TEXTO:", t[:2500])
    time.sleep(1)
print("\nCONFEREM", ok, "de", len(amostra))
print(json.dumps(pc.orcamento_por_funcao(2026), ensure_ascii=False)[:2500])
