"""Agenda de audiências públicas da Câmara de Juiz de Fora.

Lê a página oficial https://www.camarajf.mg.gov.br/www/audiencias-publicas (que mostra só
as audiências do mês corrente) e a Ordem do Dia das reuniões (pauta do plenário, de hoje
e dos próximos dias já publicados), guarda o histórico em data/cache/ e gera:
  - site/dados/agenda.json (lido pela página #/agenda);
  - site/agenda.ics (calendário para assinar no celular ou no Google Agenda).
"""
import datetime as dt
import hashlib
import html
import json
import re
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "data" / "cache" / "agenda.json"
SAIDA = RAIZ / "site" / "dados" / "agenda.json"
ICS = RAIZ / "site" / "agenda.ics"
FONTE = "https://www.camarajf.mg.gov.br/www/audiencias-publicas"
H = {"User-Agent": "Mozilla/5.0 (RadarJF; robo de transparencia)"}

ENTRADA = re.compile(
    r"(?P<data>\d{2}/\d{2}/\d{4})\s*Tema da Audiência Pública:\s*(?P<tema>.*?)"
    r"(?:\s*Autoria:\s*(?P<autoria>.*?))?"
    r"(?:\s*Requerimento:\s*(?P<req>.*?))?"
    r"(?:\s*Horário:\s*(?P<hora>.*?))?"
    r"(?:\s*Local:\s*(?P<local>.*?))?"
    r"(?=\s*\d{2}/\d{2}/\d{4}\s*Tema da|\s*Audiências Públicas -|\s*AUDIÊNCIAS REALIZADAS|\s*-->|$)",
    re.S)


def texto(pagina):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", pagina, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t)


def hora_de(h):
    m = re.search(r"(\d{1,2})\s*h\s*(\d{2})?", h or "")
    return (int(m.group(1)), int(m.group(2) or 0)) if m else None


def coletar():
    r = requests.get(FONTE, headers=H, timeout=60)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    t = texto(r.text)
    ini = t.find("Audiências Públicas -")
    t = t[ini:] if ini >= 0 else t
    eventos = []
    for m in ENTRADA.finditer(t):
        d = dt.datetime.strptime(m["data"], "%d/%m/%Y").date()
        tema = (m["tema"] or "").strip(" .")
        if not tema:
            continue
        hm = hora_de(m["hora"])
        eventos.append({
            "id": hashlib.sha1(f"{d}|{tema[:80]}".encode()).hexdigest()[:12],
            "tipo": "Audiência pública",
            "data": d.isoformat(),
            "hora": f"{hm[0]:02d}:{hm[1]:02d}" if hm else "",
            "tema": tema,
            "autoria": (m["autoria"] or "").strip(" ."),
            "requerimento": (m["req"] or "").strip(" ."),
            "local": (m["local"] or "Plenário da Câmara Municipal de Juiz de Fora").strip(" ."),
            "fonte": FONTE,
        })
    return eventos


SAL = "https://www.camarajf.mg.gov.br/sal/"
CACHE_PAUTAS = RAIZ / "data" / "cache" / "pautas.json"
ITEM = re.compile(
    r"(?P<n>\d{1,3}) (?P<fase>[^:]{3,40}?) Proposição: (?P<prop>.*?) Processo: (?P<proc>\S+) Ementa: (?P<ementa>.*?)"
    r" Autoria: (?P<autoria>.*?)(?: Quórum: (?P<quorum>.*?))?(?: Pareceres: (?P<pareceres>.*?))?(?: Observação: (?P<obs>.*?))?"
    r"(?=Clique aqui| \d{1,3} [^:]{3,40}? Proposição:| Câmara Municipal de Juiz de Fora Rua|$)")
TEMAS = [  # palavras na ementa que marcam o assunto (procuradas sem acento e em minúsculas)
    ("Educação", r"escol|ensino|educa|pedagog|alun|estudant|creche|professor|cursinho|letiv|merenda"),
    ("Saúde", r"saude|hospital|\bubs\b|medic|ozonio|\bsus\b|vacina|doenc|oncolog|paciente"),
    ("Segurança", r"seguranca|policia|bandid|vigilancia|guarda municipal|depreda"),
    ("Pessoas idosas", r"idos"),
    ("Impostos e taxas", r"iptu|tribut|imposto|taxa\b"),
    ("Trabalho", r"trabalhador|terceirizad|servidor"),
    ("Homenagens", r"titulo de cidadao|cidadao benemerito|medalha|mocao|comenda|denomina(cao)? (de |a |o )?(rua|logradouro|via|praca|avenida|travessa|escola|unidade|ponte|viaduto|ginasio|quadra|centro|bairro)"),
]


def sem_acento(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def ler(url):
    r = requests.get(url, headers=H, timeout=60)
    r.raise_for_status()
    r.encoding = "iso-8859-1" if "charset=utf" not in r.headers.get("content-type", "").lower() else "utf-8"
    t = r.text
    if r.encoding == "iso-8859-1":
        try:
            t = r.content.decode("utf-8")
        except UnicodeDecodeError:
            pass
    return t


def pauta_do_dia(d):
    """Reuniões do dia d e os itens da Ordem do Dia de cada uma."""
    lista = ler(f"{SAL}listareuniao.php?diadata={d.day:02d}&mesdata={d.month:02d}&anodata={d.year}&btnprocura=Procurar")
    reunioes = []
    for cod, nome in re.findall(r'ordemdodia\.php\?cod=(\d+)[^>]*>(.*?)</a>', lista, flags=re.S):
        nome = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", nome))).strip()
        url = f"{SAL}ordemdodia.php?cod={cod}"
        t = texto(ler(url))
        itens = []
        for m in ITEM.finditer(t):
            ementa = m["ementa"].strip()
            chave = sem_acento(ementa + " " + m["prop"])
            temas = [n for n, rx in TEMAS if re.search(rx, chave)]
            obs = (m["obs"] or "").strip(" .")
            itens.append({
                "n": int(m["n"]), "fase": m["fase"].strip(), "proposicao": m["prop"].strip(),
                "ementa": ementa, "autoria": m["autoria"].strip(" ."), "quorum": (m["quorum"] or "").strip(" ."),
                "obs": obs, "vista": obs.upper().startswith("VISTA"), "temas": temas,
            })
        sexta = d.weekday() == 4
        reunioes.append({"data": d.isoformat(), "cod": cod, "nome": nome.replace(" reunião", " Reunião"),
                         "hora": "10:30" if sexta else "17:30", "url": url, "itens": itens})
    return reunioes


def pautas():
    """Pauta de hoje e dos próximos 6 dias (as que já foram publicadas), com histórico de 30 dias."""
    hoje = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).date()
    guardadas = {(p["data"], p["cod"]): p for p in json.loads(CACHE_PAUTAS.read_text(encoding="utf-8"))} if CACHE_PAUTAS.exists() else {}
    novas = 0
    for i in range(7):
        d = hoje + dt.timedelta(days=i)
        if d.weekday() >= 5:
            continue
        try:
            for p in pauta_do_dia(d):
                if p["itens"] or (p["data"], p["cod"]) not in guardadas:
                    guardadas[(p["data"], p["cod"])] = p
                    novas += 1
        except Exception as e:  # a Câmara às vezes fica fora do ar; mantém o que já tinha
            print("pauta", d, "falhou:", e)
    limite = (hoje - dt.timedelta(days=30)).isoformat()
    lista = sorted((p for p in guardadas.values() if p["data"] >= limite), key=lambda p: (p["data"], p["cod"]))
    CACHE_PAUTAS.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PAUTAS.write_text(json.dumps(lista, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"Pautas: {novas} reuniões lidas agora, {len(lista)} guardadas")
    return lista


def ics(eventos):
    agora = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    def esc(s):
        return str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    linhas = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Radar JFlandia//Agenda//PT-BR", "CALSCALE:GREGORIAN",
              "X-WR-CALNAME:Radar JFlândia: audiências públicas", "X-WR-TIMEZONE:America/Sao_Paulo",
              "BEGIN:VTIMEZONE", "TZID:America/Sao_Paulo", "BEGIN:STANDARD", "DTSTART:19700101T000000",
              "TZOFFSETFROM:-0300", "TZOFFSETTO:-0300", "TZNAME:-03", "END:STANDARD", "END:VTIMEZONE"]
    for e in eventos:
        d = e["data"].replace("-", "")
        if e["hora"]:
            h, mi = map(int, e["hora"].split(":"))
            fim = (dt.datetime(2000, 1, 1, h, mi) + dt.timedelta(hours=3)).strftime("%H%M")
            ini_l, fim_l = f"DTSTART;TZID=America/Sao_Paulo:{d}T{h:02d}{mi:02d}00", f"DTEND;TZID=America/Sao_Paulo:{d}T{fim}00"
        else:
            ini_l, fim_l = f"DTSTART;VALUE=DATE:{d}", ""
        desc = f"{e['tema']}" + (f"\\nAutoria: {e['autoria']}" if e["autoria"] else "") + \
               (f"\\nRequerimento: {e['requerimento']}" if e["requerimento"] else "") + \
               "\\nParticipe pelo WhatsApp da Câmara (32) 99183-0706 até 30 minutos após o início.\\nFonte: " + e["fonte"]
        linhas += ["BEGIN:VEVENT", f"UID:{e['id']}@jflandia.com.br", f"DTSTAMP:{agora}", ini_l] + ([fim_l] if fim_l else []) + [
            f"SUMMARY:{esc('Audiência pública: ' + e['tema'][:120])}", f"LOCATION:{esc(e['local'])}",
            f"DESCRIPTION:{desc.replace(',', chr(92) + ',').replace(';', chr(92) + ';')}", f"URL:{e['fonte']}", "END:VEVENT"]
    linhas.append("END:VCALENDAR")
    # linhas longas são aceitas pelos calendários comuns; quebra simples a 74 caracteres por segurança
    saida = []
    for l in linhas:
        while len(l.encode()) > 74:
            corte = 74
            while len(l[:corte].encode()) > 74:
                corte -= 1
            saida.append(l[:corte])
            l = " " + l[corte:]
        saida.append(l)
    return "\r\n".join(saida) + "\r\n"


def main():
    guardados = {e["id"]: e for e in json.loads(CACHE.read_text(encoding="utf-8"))} if CACHE.exists() else {}
    try:
        novos = coletar()
    except Exception as e:
        print("audiências falhou:", e)
        novos = []
    lista_pautas = pautas()
    for e in novos:
        guardados[e["id"]] = e
    eventos = sorted(guardados.values(), key=lambda e: (e["data"], e["hora"]))
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(eventos, ensure_ascii=False, indent=0), encoding="utf-8")
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps({
        "atualizado": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "eventos": eventos,
        "pautas": lista_pautas,
        "ordinarias": "Reuniões ordinárias de segunda a quinta às 17h30 e às sextas às 10h30, fora dos recessos (17 a 31 de janeiro e 16 de julho a 15 de agosto).",
        "fontes": [FONTE, "https://www.camarajf.mg.gov.br/www/agenda-de-reunioes"],
    }, ensure_ascii=False), encoding="utf-8")
    ICS.write_text(ics(eventos), encoding="utf-8")
    print(f"Agenda: {len(novos)} audiências na página oficial, {len(eventos)} no histórico")


if __name__ == "__main__":
    main()
