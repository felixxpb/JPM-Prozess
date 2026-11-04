# -*- coding: utf-8 -*-
"""
Laender_Abrufen_UK.py - Datenabruf fuer die Laenderanalyse Vereinigtes Koenigreich

Holt (alles ohne Zugangsschluessel):
  - Bank of England (Statistical Interactive Database): Bank Rate, Sonia, Gilt-Renditen, Pfundkurse
  - ONS: CPI-Jahresrate (D7G7), Arbeitslosenquote (MGSX)
  - UK Parliament (members-api): Sitzverteilung im Unterhaus, Regierungsaemter
  - Bank of England (Webseite): Zinsbeschluesse und Berichte (Ueberschriften mit Datum)
und erkennt NEUE FAKTEN automatisch (Vergleich mit dem Stand des letzten Abrufs):
  Premierminister/Schluesselaemter, Kabinettsumbildung, Aenderung der Sitzverteilung,
  neue Zinsbeschluesse und Berichte der Bank of England.
Schreibt laender/daten/uk.js (window.UK_DATEN = {...}).
Jeder Teil ist einzeln abgesichert: faellt eine Quelle aus, bleibt der letzte gute Stand stehen.

Stand der Beschreibung: 2026-11-04.
Aufruf: python -X utf8 Laender_Abrufen_UK.py
Umgebungsvariable LAENDER_DATEN setzt den Zielordner (wie bei Laender_Abrufen_USA.py).
"""
import json, re, os, sys, html, datetime, time, urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
ZIEL = os.environ.get("LAENDER_DATEN") or os.path.normpath(os.path.join(HIER, "..", "laender", "daten"))
DATEI = os.path.join(ZIEL, "uk.js")
UA = {"User-Agent": "Mozilla/5.0 (JPM-Prozess Laenderanalyse)"}
MON = {"JAN":1,"FEB":2,"MAR":3,"APR":4,"MAY":5,"JUN":6,"JUL":7,"AUG":8,"SEP":9,"OCT":10,"NOV":11,"DEC":12}
MONEN = {"January":1,"February":2,"March":3,"April":4,"May":5,"June":6,"July":7,"August":8,"September":9,"October":10,"November":11,"December":12}
SCHLUESSEL = [("Prime Minister", "Premierminister"), ("Chancellor of the Exchequer", "Schatzkanzler"),
              ("Foreign Secretary", "Außenminister"), ("Home Secretary", "Innenminister"),
              ("Secretary of State for Defence", "Verteidigungsminister"),
              ("Secretary of State for Health", "Gesundheitsminister")]

def get(url, wiederholen=3):
    letzte = None
    for i in range(wiederholen):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8", "replace")
        except Exception as e:
            letzte = e; time.sleep(2 + i * 3)
    raise letzte

# ---------------- Bank of England / ONS ----------------
BOE = ("https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes"
       "&Datefrom=01/Jan/1997&Dateto=now&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N&SeriesCodes=")

def boe(codes):
    zeilen = [z for z in get(BOE + ",".join(codes)).splitlines() if z.strip()]
    out = [[] for _ in codes]
    for z in zeilen[1:]:
        t = z.split(",")
        try: d = datetime.datetime.strptime(t[0], "%d %b %Y").strftime("%Y-%m-%d")
        except Exception: continue
        for i in range(len(codes)):
            if i + 1 < len(t) and t[i + 1].strip() not in ("", "n/a"):
                try: out[i].append([d, float(t[i + 1])])
                except ValueError: pass
    return out

def monatsende(r):
    m = {}
    for d, v in r: m[d[:7]] = [d, v]
    return [m[k] for k in sorted(m)]

def aenderungen(r):
    out, p = [], None
    for d, v in r:
        if v != p: out.append([d, v]); p = v
    out.append([r[-1][0], r[-1][1]])
    return out

def ons(pfad):
    txt = get("https://www.ons.gov.uk/generator?format=csv&uri=" + pfad)
    out = []
    for m in re.finditer(r'^"(\d{4}) ([A-Z]{3})","([-\d.]+)"', txt, re.M):
        j, mo, v = int(m.group(1)), MON[m.group(2)], float(m.group(3))
        if j >= 1997: out.append(["%04d-%02d-01" % (j, mo), v])
    if not out: raise ValueError("ONS-Reihe leer")
    return out

# ---------------- Parlament ----------------
def parlament(heute):
    sp = json.loads(get("https://members-api.parliament.uk/api/Parties/StateOfTheParties/Commons/" + heute))
    sitze = sorted([[i["value"]["party"]["name"], i["value"]["total"], i["value"]["party"]["backgroundColour"]] for i in sp["items"]], key=lambda s: -s[1])
    if sum(s[1] for s in sitze) < 600: raise ValueError("Sitzzahl unplausibel")
    gp = json.loads(get("https://members-api.parliament.uk/api/Posts/GovernmentPosts"))
    posten, gesehen = [], set()
    for i in gp:
        v = i.get("value", i); n = v.get("name")
        h = [((x.get("member") or {}).get("value") or {}).get("nameDisplayAs") for x in v.get("postHolders", [])]
        h = [x for x in h if x]
        if n and h and n not in gesehen: gesehen.add(n); posten.append([n, ", ".join(h)])
    if not posten: raise ValueError("keine Regierungsaemter")
    return sitze, posten

# ---------------- BoE-Webseite: Beschluesse und Berichte ----------------
def boe_berichte():
    t = get("https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    zeilen = [html.unescape(l.strip()) for l in re.sub(r"<[^>]+>", "\n", t).splitlines() if l.strip()]
    out = []
    for i, z in enumerate(zeilen[:-1]):
        m = re.fullmatch(r"(\d{1,2}) ([A-Z][a-z]+) (20\d\d)", z)
        if m and m.group(2) in MONEN:
            kopf = zeilen[i + 1]
            if kopf.endswith("...") and i + 2 < len(zeilen):
                kopf = zeilen[i + 2]     # gekuerzte Zeile: die volle Ueberschrift folgt direkt danach
            if re.search(r"Bank [Rr]ate|Monetary Policy Report|Monetary Policy Summary", kopf) and not kopf.endswith("..."):
                d = "%s-%02d-%02d" % (m.group(3), MONEN[m.group(2)], int(m.group(1)))
                out.append([d, kopf])
    # doppelte Eintraege (gekuerzt/ungekuerzt) entfernen
    seen, res = set(), []
    for d, k in out:
        if (d, k) not in seen: seen.add((d, k)); res.append([d, k])
    if not res: raise ValueError("keine Berichte erkannt")
    return res

def termine():
    t = get("https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    z = [html.unescape(l.strip()).replace("\xa0", " ") for l in re.sub(r"<[^>]+>", "\n", t).splitlines() if l.strip()]
    res = {}
    jahr = None
    for l in z:
        m = re.fullmatch(r"(20\d\d) confirmed dates", l)
        if m: jahr = int(m.group(1)); res[jahr] = []; continue
        m = re.fullmatch(r"Thursday (\d{1,2}) ([A-Z][a-z]+)", l.strip())
        if m and jahr and m.group(2) in MONEN:
            res[jahr].append("%04d-%02d-%02d" % (jahr, MONEN[m.group(2)], int(m.group(1))))
    return {str(k): v for k, v in res.items() if v}

# ---------------- Neue Fakten erkennen ----------------
def neue_ereignisse(alt, sitze, posten, berichte, heute):
    ev = []
    if not alt or "_zustand" not in alt:
        return ev   # erster Lauf: nur Ausgangsstand merken
    z = alt["_zustand"]
    neu = {n: h for n, h in posten}
    for teil, name in SCHLUESSEL:
        n_neu = next((h for n, h in neu.items() if n.startswith(teil)), None)
        n_alt = next((h for n, h in z.get("posten", {}).items() if n.startswith(teil)), None)
        if n_neu and n_alt and n_neu != n_alt:
            ev.append({"d": heute, "t": "Neuer " + name + ": " + n_neu, "x": "Bisher " + n_alt + ". Automatisch erkannt am " + heute + " aus dem Datenabruf des Parlaments, das Datum des Amtswechsels kann früher liegen.", "k": "pol", "auto": True, "q": "UK Parliament, Members API"})
    gew = [n for n, h in neu.items() if n in z.get("posten", {}) and z["posten"][n] != h]
    if len(gew) >= 3:
        ev.append({"d": heute, "t": "Kabinettsumbildung: " + str(len(gew)) + " Ämter mit neuen Amtsinhabern", "x": "Geänderte Ämter: " + "; ".join(gew[:8]) + ("; …" if len(gew) > 8 else "") + ". Automatisch erkannt am " + heute + ".", "k": "pol", "auto": True, "q": "UK Parliament, Members API"})
    sneu = {n: t for n, t, _ in sitze}
    unter = []
    for n in sorted(set(sneu) | set(z.get("sitze", {}))):
        a, b = z.get("sitze", {}).get(n, 0), sneu.get(n, 0)
        if a != b: unter.append("%s %d → %d" % (n, a, b))
    if unter:
        ev.append({"d": heute, "t": "Sitzverteilung im Unterhaus geändert", "x": "; ".join(unter) + ". Mögliche Ursachen: Nachwahl, Parteiwechsel, Austritt. Automatisch erkannt am " + heute + ".", "k": "pol", "auto": True, "q": "UK Parliament, State of the Parties"})
    gesehen = set(tuple(x) for x in z.get("berichte", []))
    for d, kopf in berichte:
        if (d, kopf) not in gesehen:
            ev.append({"d": d, "t": kopf, "x": "Neu auf der Seite der Bank of England veröffentlicht. Automatisch erkannt am " + heute + ".", "k": "boe", "auto": True, "q": "bankofengland.co.uk"})
    return ev

def holen(alt=None):
    heute = datetime.date.today().isoformat()
    daten, fehler = {}, {}
    def teil(name, f):
        try: f()
        except Exception as e: fehler[name] = str(e)[:120]; print("FEHLER", name, e)
    def a():
        daten["bankrate"] = aenderungen(boe(["IUDBEDR"])[0])
    def b():
        r = boe(["IUDBEDR"])[0]; daten["_letzteTageBank"] = r[-1][0]
        daten["sonia"] = monatsende(boe(["IUDSOIA"])[0])
    def c():
        g5, g10, g20 = boe(["IUDSNZC", "IUDMNZC", "IUDLNZC"])
        daten["gilt5"], daten["gilt10"], daten["gilt20"] = monatsende(g5), monatsende(g10), monatsende(g20)
    def d_():
        daten["gbpusd"] = monatsende(boe(["XUDLUSS"])[0]); daten["gbpeur"] = monatsende(boe(["XUDLERS"])[0])
    def e():
        daten["cpi"] = ons("/economy/inflationandpriceindices/timeseries/d7g7/mm23")
    def f():
        daten["alq"] = ons("/employmentandlabourmarket/peoplenotinwork/unemployment/timeseries/mgsx/lms")
    def g():
        daten["sitze"], daten["posten"] = parlament(heute)
    def h():
        daten["_berichte"] = boe_berichte()
    def i():
        daten["_termine"] = termine()
    for n, fn in [("bankrate", a), ("sonia", b), ("gilts", c), ("pfund", d_), ("cpi", e), ("alq", f), ("parlament", g), ("boe_berichte", h), ("boe_termine", i)]: teil(n, fn)
    # letzten guten Stand uebernehmen, wenn ein Teil ausgefallen ist
    if alt:
        for k in ("bankrate", "_letzteTageBank", "sonia", "gilt5", "gilt10", "gilt20", "gbpusd", "gbpeur", "cpi", "alq", "sitze", "posten", "_berichte", "_termine"):
            if k not in daten and k in alt: daten[k] = alt[k]
    ev_alt = list((alt or {}).get("ereignisse", []))
    ev_neu = neue_ereignisse(alt, daten.get("sitze", []), daten.get("posten", []), daten.get("_berichte", []), heute) if daten.get("sitze") else []
    schon = set((e["d"], e["t"]) for e in ev_alt)
    for e in ev_neu:
        if (e["d"], e["t"]) not in schon: ev_alt.append(e)
    daten["ereignisse"] = sorted(ev_alt, key=lambda e: e["d"])
    daten["_zustand"] = {"posten": {n: h for n, h in daten.get("posten", [])}, "sitze": {n: t for n, t, _ in daten.get("sitze", [])}, "berichte": daten.get("_berichte", [])}
    daten["_abruf"] = heute
    daten["_stand"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    daten["_fehler"] = fehler
    return daten

def alt_laden():
    try:
        t = open(DATEI, encoding="utf-8").read()
        return json.loads(t[t.index("{"):t.rindex("}") + 1])
    except Exception:
        return None

if __name__ == "__main__":
    os.makedirs(ZIEL, exist_ok=True)
    alt = alt_laden()
    d = holen(alt)
    ok = d.get("sitze") and d.get("bankrate")
    open(DATEI, "w", encoding="utf-8").write("window.UK_DATEN=" + json.dumps(d, separators=(",", ":"), ensure_ascii=False) + ";\n")
    print("uk.js geschrieben:", DATEI, "Ereignisse:", len(d["ereignisse"]), "Fehler:", d["_fehler"] or "keine")
    if not ok: sys.exit(1)
