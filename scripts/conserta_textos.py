"""Conserta acentos quebrados nos textos de todos os arquivos do site.

Os arquivos da Prefeitura às vezes trazem texto em UTF-8 lido como se fosse
Windows-1252 ("AQUISIÃ§Ã£O" no lugar de "AQUISIÇÃO"). Este passo percorre
site/dados/**/*.json e troca só os trechos quebrados, mantendo o resto igual.
Quando a letra quebrada está numa palavra em maiúsculas, ela volta em maiúscula.
"""
import json
import pathlib
import re
import sys

PASTA = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "site/dados")


def _car(b):
    try:
        return bytes([b]).decode("cp1252")
    except UnicodeDecodeError:
        return bytes([b]).decode("latin-1")


CONT = "".join(re.escape(_car(b)) for b in range(0x80, 0xC0))
LEAD2 = "".join(re.escape(_car(b)) for b in range(0xC2, 0xE0))
LEAD3 = "".join(re.escape(_car(b)) for b in range(0xE0, 0xF0))
PADRAO = re.compile(f"[{LEAD3}][{CONT}][{CONT}]|[{LEAD2}][{CONT}]")


def _bytes(s):
    out = b""
    for ch in s:
        try:
            out += ch.encode("cp1252")
        except UnicodeEncodeError:
            out += ch.encode("latin-1")
    return out


def conserta(t):
    if not isinstance(t, str) or not PADRAO.search(t):
        return t
    out, pos = [], 0
    for m in PADRAO.finditer(t):
        out.append(t[pos:m.start()])
        pos = m.end()
        try:
            novo = _bytes(m.group(0)).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            out.append(m.group(0))
            continue
        antes = next((c for c in reversed("".join(out)) if c.isalpha()), "")
        depois = next((c for c in t[pos:] if c.isalpha() and not PADRAO.match(t, t.index(c, pos))), "")
        vizinhos = [c for c in (antes, depois) if c]
        if vizinhos and all(c.isupper() for c in vizinhos):
            novo = novo.upper()
        out.append(novo)
    out.append(t[pos:])
    return "".join(out)


def percorre(x, cont):
    if isinstance(x, str):
        y = conserta(x)
        if y != x:
            cont[0] += 1
        return y
    if isinstance(x, list):
        return [percorre(v, cont) for v in x]
    if isinstance(x, dict):
        return {conserta(k): percorre(v, cont) for k, v in x.items()}
    return x


def main():
    total = 0
    for arq in sorted(PASTA.rglob("*.json")):
        try:
            dados = json.loads(arq.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError):
            continue
        cont = [0]
        novo = percorre(dados, cont)
        if cont[0]:
            arq.write_text(json.dumps(novo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            print(f"{arq}: {cont[0]} textos consertados")
            total += cont[0]
    print("Total de textos consertados:", total)


if __name__ == "__main__":
    main()
