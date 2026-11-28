# -*- coding: utf-8 -*-
"""
Laender_Abrufen_AUS.py - Datenabruf fuer die Laenderanalyse Australien (Stand 2026-11-27, Oberthema 3 Zentralbank)

Holt (alles ohne Zugangsschluessel):
  - RBA-Statistiktabellen (CSV): A1 Bilanz, A2 Zinsbeschluesse, F1 Cash Rate taeglich, F2 Renditen,
    F5 Kreditzinsen, F11.1 Wechselkurse, D1 Kreditwachstum
  - RBA-Webseiten: Cash-Rate-Seite (Beschluesse mit Statement/Minutes-Links), Kalender (Sitzungstermine),
    Statement on Monetary Policy (Kurzfassung), Beschluss-Statement (Abstimmung, falls dort angegeben)
  - ABS Data API: Inflation (CPI, Jahresrate, monatlich), Arbeitslosenquote (Labour Force, monatlich)
  - BIS: Verschuldung der privaten Haushalte
WICHTIG: Die RBA-Webseite sperrt Skripte vom PC aus (403), laesst aber den GitHub-Server durch.
Dieses Skript ist daher nur auf dem Server voll testbar. Jeder Teil ist einzeln abgesichert: faellt eine
Quelle aus, bleibt der letzte gute Stand stehen. Die Struktur der RBA-Dateien wird ins Protokoll geschrieben.
Schreibt laender/daten/aus.js (window.AUS_DATEN = {...}).
Aufruf: python -X utf8 Laender_Abrufen_AUS.py   (Umgebungsvariable LAENDER_DATEN setzt den Zielordner)
"""
import json, re, os, sys, html, csv, io, datetime, time, urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
ZIEL = os.environ.get("LAENDER_DATEN") or os.path.normpath(os.path.join(HIER, "..", "laender", "daten"))
DATEI = os.path.join(ZIEL, "aus.js")
UA = {"User-Agent": "Mozilla/5.0 (JPM-Prozess Laenderanalyse)"}
RBA = "https://www.rba.gov.au"
MON = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
MONEN = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7, "august": 8,
         "september": 9, "october": 10, "november": 11, "december": 12}


def get(url, wiederholen=3):
    letzte = None
    for i in range(wiederholen):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8-sig", "replace")
        except Exception as e:
            letzte = e
            time.sleep(2 + i * 4)
    raise letzte


def text(seite):
    s = re.sub(r"(?s)<(script|style).*?</\1>", "", seite)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).replace("\xa0", " ").strip()


def datum(s):
    """'23-Jan-1990', '30/06/1969', '4 Nov 2026', '2026-11-04' -> 'JJJJ-MM-TT' oder None"""
    s = s.strip()
    m = re.fullmatch(r"(\d{1,2})[-/ ]([A-Za-z]{3})[a-z]*[-/ ](\d{4})", s)
    if m and m.group(2).lower() in MON:
        return "%s-%02d-%02d" % (m.group(3), MON[m.group(2).lower()], int(m.group(1)))
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        return "%s-%02d-%02d" % (m.group(3), int(m.group(2)), int(m.group(1)))
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    return s if m else None


# ---------------- RBA-Tabellen (CSV) ----------------
def rba_tabelle(name):
    """Liest eine RBA-CSV-Tabelle. Rueckgabe: {Series-ID: {"n": Titel, "r": [[Datum, Wert-oder-Text], ...]}}"""
    zeilen = list(csv.reader(io.StringIO(get("%s/statistics/tables/csv/%s-data.csv" % (RBA, name)))))
    titel = ids = None
    start = None
    for i, z in enumerate(zeilen):
        if z and z[0] == "Title": titel = z
        if z and z[0] == "Series ID":
            ids = z; start = i + 1; break
    if not ids: raise ValueError(name + ": Kopf nicht erkannt")
    print("TABELLE", name, "Spalten:", [(ids[j], titel[j][:40]) for j in range(1, min(len(ids), 30))], flush=True)
    out = {ids[j]: {"n": titel[j], "r": []} for j in range(1, len(ids))}
    for z in zeilen[start:]:
        if not z or not z[0]: continue
        d = datum(z[0])
        if not d: continue
        for j in range(1, min(len(z), len(ids))):
            v = z[j].strip()
            if v == "": continue
            try: out[ids[j]]["r"].append([d, float(v)])
            except ValueError: out[ids[j]]["r"].append([d, v])
    return out


def monatsende(r):
    m = {}
    for d, v in r:
        if isinstance(v, float): m[d[:7]] = [d, v]
    return [m[k] for k in sorted(m)]


def finde(tab, ids, teile=()):
    """Waehlt eine Reihe nach Series-ID, sonst nach Titel (alle 'teile' muessen im Titel stehen)."""
    for i in ids:
        if i in tab and tab[i]["r"]: return i, tab[i]
    for i, s in tab.items():
        if teile and all(t.lower() in s["n"].lower() for t in teile) and s["r"]: return i, s
    raise ValueError("Reihe nicht gefunden: " + "/".join(list(ids) + list(teile)))


def reihe(tab, ids, teile=(), ab="1990-01-01", monat=True):
    i, s = finde(tab, ids, teile)
    r = [[d, v] for d, v in s["r"] if isinstance(v, float) and d >= ab]
    if monat: r = monatsende(r)
    return {"id": i, "n": s["n"], "r": r}


# ---------------- Zinsbeschluesse (A2) ----------------
def beschluesse():
    t = rba_tabelle("a2")
    i, aend = finde(t, ["ARBAMPCCCR"], ["change", "cash rate target"])
    j, neu = finde(t, ["ARBAMPCNCRT"], ["new cash rate target"])
    out = []
    for d, v in neu["r"]:
        zahl = v
        if isinstance(v, str):  # vor Aug 1990: Spanne "17.00 to 17.50" -> Mitte
            z = re.findall(r"-?\d+\.\d+", v)
            if not z: continue
            zahl = sum(float(x) for x in z) / len(z)
        a = next((w for dd, w in aend["r"] if dd == d), None)
        if isinstance(a, str):
            z = re.findall(r"-?\d+\.\d+", a); a = sum(float(x) for x in z) / len(z) if z else None
        out.append([d, round(zahl, 2), a])
    if not out: raise ValueError("A2 leer")
    return out  # [Datum, neuer Zielsatz, Aenderung]


# ---------------- Cash-Rate-Seite: Beschluesse mit Statement-/Minutes-Links ----------------
def cashseite():
    s = get(RBA + "/statistics/cash-rate/")
    res = []
    for tr in re.findall(r"(?s)<tr[^>]*>(.*?)</tr>", s):
        zellen = re.findall(r"(?s)<t[dh][^>]*>(.*?)</t[dh]>", tr)
        if len(zellen) < 3: continue
        d = datum(text(zellen[0]))
        if not d: continue
        links = {}
        for h, t in re.findall(r'(?s)<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', tr):
            t = text(t).lower()
            if "statement" in t: links["statement"] = h
            elif "minutes" in t: links["minutes"] = h
        try:
            aend = float(text(zellen[1]).replace("+", ""))
            satz = float(text(zellen[2]))
        except ValueError:
            continue
        res.append({"d": d, "aend": aend, "satz": satz,
                    "statement": (RBA + links["statement"]) if links.get("statement", "").startswith("/") else links.get("statement"),
                    "minutes": (RBA + links["minutes"]) if links.get("minutes", "").startswith("/") else links.get("minutes")})
    if not res: raise ValueError("Cash-Rate-Seite: keine Zeilen erkannt")
    return sorted(res, key=lambda x: x["d"], reverse=True)[:40]


# ---------------- Sitzungstermine (Kalender) ----------------
def _sitzungen(t):
    res = []
    for m in re.finditer(r"Monetary Policy Board Meeting(?: Monetary Policy Decision)? (\d{1,2})(?: ([A-Z][a-z]+))?\s*[–-]\s*(\d{1,2}) ([A-Z][a-z]+) (20\d\d)", t):
        m2 = MONEN.get(m.group(4).lower()); m1 = MONEN.get((m.group(2) or m.group(4)).lower())
        if not m1 or not m2: continue
        jahr = int(m.group(5))
        res.append({"von": "%04d-%02d-%02d" % (jahr, m1, int(m.group(1))), "bis": "%04d-%02d-%02d" % (jahr, m2, int(m.group(3)))})
    return res


def termine():
    res = []
    for u in ("/schedules-events/calendar/?topics=mone", "/schedules-events/calendar/"):
        try:
            t = text(get(RBA + u))
            neu = _sitzungen(t)
            print("TERMINE", u, "Seitenlaenge", len(t), "Sitzungen", len(neu), flush=True)
            res += neu
        except Exception as e:
            print("TERMINE Fehler", u, e, flush=True)
    # Fallback: kommende Protokoll-Daten (Datei heisst nach dem ersten Sitzungstag)
    try:
        s = get(RBA + "/monetary-policy/rba-board-minutes/%d/" % datetime.date.today().year)
        for d in re.findall(r"/rba-board-minutes/20\d\d/(20\d\d-\d\d-\d\d)\.html", s):
            bis = datetime.date.fromisoformat(d)   # Dateiname = Beschlusstag (zweiter Sitzungstag)
            res.append({"von": (bis - datetime.timedelta(days=1)).isoformat(), "bis": d})
    except Exception as e:
        print("TERMINE Protokollliste Fehler", e, flush=True)
    seen, out = set(), []
    for x in sorted(res, key=lambda x: x["bis"]):
        if x["bis"] not in seen: seen.add(x["bis"]); out.append(x)
    print("TERMINE gefunden:", len(out), [x["bis"] for x in out][-8:], flush=True)
    if not out: raise ValueError("keine Sitzungstermine erkannt")
    return out


# ---------------- Abstimmung im Board (Statement des letzten Beschlusses) ----------------
def abstimmung(cash):
    """Sucht im Beschluss-Statement nach der Aufzeichnung der Stimmen. Findet sich keine, bleibt das Feld leer."""
    for b in cash[:2]:
        if not b.get("statement"): continue
        t = text(get(b["statement"]))
        sat = re.split(r"(?<=[a-z%)])\.\s+(?=[A-Z“])", t)
        i = next((k for k, x in enumerate(sat) if re.search(r"(?i)voted|by majority|unanimous|vote was", x)), None)
        print("STATEMENT", b["d"], b["statement"], "Laenge", len(t), "| Abstimmung:", sat[i][:300] if i is not None else "nicht gefunden", flush=True)
        if i is not None:
            teil = [sat[i]]
            for x in sat[i + 1:i + 4]:
                if re.search(r"(?i)voted|members? (?:voted|preferred)", x): teil.append(x)
                else: break
            satz = ". ".join(x.strip().rstrip(".") for x in teil) + "."
            zahl = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9}
            gruppen = [{"n": zahl[g.group(1).lower()], "text": g.group(2).strip()}
                       for g in re.finditer(r"(?i)(one|two|three|four|five|six|seven|eight|nine) members? voted to ((?:[^;.]|\.(?=\d))+)", satz)]
            return {"d": b["d"], "satz": satz, "url": b["statement"], "gruppen": gruppen}
    return None


# ---------------- Statement on Monetary Policy ----------------
def smp():
    s = get(RBA + "/publications/smp/")
    links = sorted(set(re.findall(r'href="(/publications/smp/20\d\d/[a-z]{3}/)"', s)),
                   key=lambda h: (int(re.search(r"/(20\d\d)/", h).group(1)), MON.get(re.search(r"/20\d\d/([a-z]{3})/", h).group(1), 0)), reverse=True)
    if not links: raise ValueError("kein SMP-Link")
    url = RBA + links[0]
    t = text(get(url))
    m = re.search(r"Statement on Monetary Policy [–-] ([A-Z][a-z]+ 20\d\d) In Brief (.{100,900}?) (?:Read Overview|What is going on)", t)
    return {"url": url, "titel": ("Statement on Monetary Policy – " + m.group(1)) if m else "Statement on Monetary Policy",
            "kurz": m.group(2) if m else t[:500], "ausgaben": links[:8]}


# ---------------- Rahmenwerk (Statement on the Conduct of Monetary Policy) und Board ----------------
def rahmen():
    """Holt den Wortlaut des geltenden Rahmenwerks (Juli 2025) und das Board; liefert wichtige Saetze woertlich."""
    t = text(get(RBA + "/monetary-policy/framework/stmt-conduct-mp-9-2025-07-10.html"))
    saetze = [x.strip() for x in re.split(r"(?<=[.])\s+", t) if 40 < len(x) < 420]
    wichtig = [x for x in saetze if re.search(r"(?i)(inflation|employment|per cent|vote|votes|quorum|members)", x)][:14]
    print("RAHMEN Saetze:", wichtig[:6], flush=True)
    board = {}
    try:
        b = text(get(RBA + "/about-rba/boards/monetary-policy-board/"))
        i = b.find("Members")
        board = {"auszug": b[i:i + 1800] if i >= 0 else b[:1800]}
        print("BOARD Auszug:", board["auszug"][:900], flush=True)
    except Exception as e:
        print("BOARD Fehler", e, flush=True)
    return {"saetze": wichtig, "board": board, "url": RBA + "/monetary-policy/framework/stmt-conduct-mp-9-2025-07-10.html"}


# ---------------- Mitglieder des Boards (Statutory Appointments) ----------------
def mitglieder():
    """Liest die Amtszeiten der Board-Mitglieder aus der RBA-Seite 'Statutory Appointments'."""
    t = text(get(RBA + "/about-rba/statutory-appointments.html"))
    k = t.find("Monetary Policy Board Name Position")
    t = t[k:] if k >= 0 else t
    k2 = t.find("Payments System Board")
    t = t[:k2] if k2 > 0 else t[:6000]
    heute = datetime.date.today().isoformat()
    ROLLEN = r"(Governor|Deputy Governor|Secretary to the Treasury|Monetary Policy Board Member|Member)"
    out = []
    for m in re.finditer(r"(\d{1,2} [A-Z][a-z]{2,8} 20\d\d) (\d{1,2} [A-Z][a-z]{2,8} 20\d\d)", t):
        vor = t[max(0, m.start() - 230):m.start()]
        r = list(re.finditer(ROLLEN + r"(?= |$)", vor))
        if not r: continue
        rolle = r[-1].group(1)
        worte = vor[:r[-1].start()].split()
        name = []
        while worte and len(name) < 4 and (re.fullmatch(r"[A-Z][a-zA-Z.’'-]+", worte[-1]) or worte[-1] in ("AM", "AO", "AC"))                 and worte[-1] not in ("Ends", "Act", "Position", "Name", "officio", "Ex", "Appointment", "Appointments", "Board", "Policy", "Monetary"):
            name.insert(0, worte.pop())
        if not name: continue
        von, bis = datum(m.group(1)), datum(m.group(2))
        out.append({"name": " ".join(name), "rolle": rolle if rolle != "Member" else "Monetary Policy Board Member", "von": von, "bis": bis, "aktuell": bool(bis and bis >= heute)})
    print("MITGLIEDER gefunden:", [(x["name"], x["rolle"], x["bis"]) for x in out], flush=True)
    if not out:
        print("STATUTORY Auszug:", t[:2500], flush=True)
        raise ValueError("keine Mitglieder erkannt")
    return out


# ---------------- ABS ----------------
def abs_csv(pfad):
    return list(csv.DictReader(io.StringIO(get("https://data.api.abs.gov.au/rest/data/" + pfad + "&format=csv"))))


def abs_reihe(pfad, ab="1998-01"):
    out = []
    for x in abs_csv(pfad):
        p = x.get("TIME_PERIOD", "")
        if re.fullmatch(r"\d{4}-\d{2}", p) and x.get("OBS_VALUE") not in (None, "") and p >= ab:
            out.append([p + "-01", round(float(x["OBS_VALUE"]), 2)])
    out.sort()
    if not out: raise ValueError("ABS leer: " + pfad)
    return out


def abs_cpi():
    return abs_reihe("ABS,CPI,2.0.0/3.10001.10.50.M?startPeriod=1998-01")


def oecd_cpi_q():
    """Inflation (Jahresrate, quartalsweise) seit 1990 aus der OECD (lange Reihe fuer den Zeitstrahl)."""
    u = ("https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0/"
         "AUS.Q.N.CPI.PA._T.N.GY?startPeriod=1990-Q1&format=csvfile")
    out = []
    for x in csv.DictReader(io.StringIO(get(u))):
        m = re.fullmatch(r"(\d{4})-Q([1-4])", x.get("TIME_PERIOD", ""))
        if m and x.get("OBS_VALUE"):
            out.append(["%s-%02d-01" % (m.group(1), (int(m.group(2)) - 1) * 3 + 1), round(float(x["OBS_VALUE"]), 2)])
    out.sort()
    if not out: raise ValueError("OECD CPI leer")
    return out


def abs_alq():
    return abs_reihe("ABS,LF,1.0.0/M13.3.1599.20.AUS.M?startPeriod=1978-02", "1978-02")


# ---------------- BIS: Haushaltsverschuldung ----------------
BIS_URL = "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_TC/2.0/Q.AU.%s.A.%s.770.A?format=csv&startPeriod=1990-Q1"


def bis_reihe(sektor, bew):
    r = list(csv.DictReader(io.StringIO(get(BIS_URL % (sektor, bew)))))
    out = []
    for x in r:
        m = re.fullmatch(r"(\d{4})-Q([1-4])", x.get("TIME_PERIOD", ""))
        if m and x.get("OBS_VALUE"):
            out.append(["%s-%02d-01" % (m.group(1), (int(m.group(2)) - 1) * 3 + 1), round(float(x["OBS_VALUE"]), 1)])
    if not out: raise ValueError("BIS leer")
    return out


# ---------------- Zusammenbau ----------------
def zentralbank(fehler):
    zb = {}

    def teil(name, f):
        try: zb[name] = f()
        except Exception as e:
            fehler[name] = str(e)[:140]; print("FEHLER", name, e, flush=True)

    def cash_tag():
        t = rba_tabelle("f1")
        return reihe(t, ["FIRMMCRTD"], ["cash rate target"])
    def bilanz():
        t = rba_tabelle("a1")
        return {"aktiva": reihe(t, ["ARBAATAW"], ["total assets"], "2013-01-01", False),
                "wertpapiere": reihe(t, ["ARBAAASTW"], ["australian dollar securities"], "2013-01-01", False),
                "banknoten": reihe(t, ["ARBALNOIW"], ["notes on issue"], "2013-01-01", False),
                "es": reihe(t, ["ARBALESBW"], ["exchange settlement"], "2013-01-01", False),
                "regierung": reihe(t, ["ARBALDOGIAGW"], ["australian government deposits"], "2013-01-01", False)}
    def kredit():
        t = rba_tabelle("d1")
        return {"haus12": reihe(t, ["DGFACH12"], ["housing", "12-month"], "1990-01-01", False),
                "eigen12": reihe(t, ["DGFACOH12"], ["owner-occupier", "12-month"], "1990-01-01", False),
                "invest12": reihe(t, ["DGFACIH12"], ["investor", "12-month"], "1990-01-01", False)}
    def kreditzins():
        t = rba_tabelle("f5")
        return {"var_eigen": reihe(t, [], ["housing loans", "banks", "variable", "standard", "owner-occupier"], "1990-01-01", False)}
    def aud():
        neu = reihe(rba_tabelle("f11.1"), ["FXRUSD"], ["a$1=usd"], "1990-01-01")
        try:
            alt = reihe(rba_tabelle("f11"), ["FXRUSD"], ["a$1=usd"], "1990-01-01")
            m = {d[:7]: [d, v] for d, v in alt["r"]}
            for d, v in neu["r"]: m[d[:7]] = [d, v]
            neu["r"] = [m[k] for k in sorted(m)]
        except Exception as e:
            print("AUD Altreihe (F11) nicht verfuegbar:", e, flush=True)
        return neu
    def rendite():
        t = rba_tabelle("f2")
        return reihe(t, ["FCMYGBAG10D"], ["10 year"], "1990-01-01", True)
    def haushalt_bis():
        return {"H": bis_reihe("H", "M"), "N": bis_reihe("N", "M")}

    for n, f in [("beschluesse", beschluesse), ("cash_tag", cash_tag), ("bilanz", bilanz), ("kredit", kredit),
                 ("kreditzins", kreditzins), ("aud", aud), ("rendite", rendite),
                 ("cashseite", cashseite), ("rahmen", rahmen), ("mitglieder", mitglieder), ("termine", termine), ("smp", smp), ("cpi", abs_cpi), ("cpi_q", oecd_cpi_q), ("alq", abs_alq),
                 ("schulden_bis", haushalt_bis)]:
        teil(n, f)
    try: zb["abstimmung"] = abstimmung(zb.get("cashseite") or [])
    except Exception as e: fehler["abstimmung"] = str(e)[:140]; print("FEHLER abstimmung", e, flush=True)
    return zb


def holen(alt=None):
    fehler = {}
    zb = zentralbank(fehler)
    if alt:
        for k, v in (alt.get("zb") or {}).items():
            if zb.get(k) in (None, [], {}): zb[k] = v
    daten = {"zb": zb, "_abruf": datetime.date.today().isoformat(),
             "_stand": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "_fehler": fehler}
    return daten


def alt_laden():
    try:
        t = open(DATEI, encoding="utf-8").read()
        return json.loads(t[t.index("{"):t.rindex("}") + 1])
    except Exception:
        return None


if __name__ == "__main__":
    os.makedirs(ZIEL, exist_ok=True)
    d = holen(alt_laden())
    open(DATEI, "w", encoding="utf-8").write("window.AUS_DATEN=" + json.dumps(d, separators=(",", ":"), ensure_ascii=False) + ";\n")
    print("aus.js geschrieben:", DATEI, "Fehler:", d["_fehler"] or "keine")
    if not d["zb"].get("beschluesse"): sys.exit(1)
