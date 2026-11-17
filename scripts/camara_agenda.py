"""Agenda de audiências públicas da Câmara de Juiz de Fora.

Lê a página oficial https://www.camarajf.mg.gov.br/www/audiencias-publicas (que mostra só
as audiências do mês corrente), guarda o histórico em data/cache/agenda.json e gera:
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
    novos = coletar()
    for e in novos:
        guardados[e["id"]] = e
    eventos = sorted(guardados.values(), key=lambda e: (e["data"], e["hora"]))
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(eventos, ensure_ascii=False, indent=0), encoding="utf-8")
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps({
        "atualizado": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "eventos": eventos,
        "ordinarias": "Reuniões ordinárias de segunda a quinta às 17h30 e às sextas às 10h30, fora dos recessos (17 a 31 de janeiro e 16 de julho a 15 de agosto).",
        "fontes": [FONTE, "https://www.camarajf.mg.gov.br/www/agenda-de-reunioes"],
    }, ensure_ascii=False), encoding="utf-8")
    ICS.write_text(ics(eventos), encoding="utf-8")
    print(f"Agenda: {len(novos)} audiências na página oficial, {len(eventos)} no histórico")


if __name__ == "__main__":
    main()
