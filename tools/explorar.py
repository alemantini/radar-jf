import subprocess, json, re, sys
subprocess.run(["bash","tools/versao_anterior.sh"],check=False)
B=json.load(open('/tmp/anterior/dados/prefeitura/empenhos_2026.json')); i=B['campos'].index('historico')
ruim=lambda s: re.search('[ÃÂ][\u0080-¿ŒœŠšŸŽžƒˆ˜–-™]',s)
print("ANTES com acento quebrado:",sum(1 for e in B['empenhos'] if ruim(str(e[i]))))
subprocess.run([sys.executable,"scripts/conserta_textos.py","/tmp/anterior/dados"],check=True)
B=json.load(open('/tmp/anterior/dados/prefeitura/empenhos_2026.json'))
print("DEPOIS com acento quebrado:",sum(1 for e in B['empenhos'] if ruim(str(e[i]))))
n=0
for e in B['empenhos']:
    h=str(e[i])
    if 'ODONTOL' in h and n<4: print("EX",h[:150]); n+=1
k=0
for e in B['empenhos']:
    h=str(e[i])
    if ruim(h) and k<8: print("RESTA",h[:150]); k+=1
