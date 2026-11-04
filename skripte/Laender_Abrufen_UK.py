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


# ---------------- BoE: Abstimmung im MPC (Protokoll) ----------------
ZAHL = {"One":1,"Two":2,"Three":3,"Four":4,"Five":5,"Six":6,"Seven":7,"Eight":8,"Nine":9}
MONNAME = ["january","february","march","april","may","june","july","august","september","october","november","december"]

def mpc_protokoll(heute):
    """Holt das neueste Protokoll 'Monetary Policy Summary and Minutes' und liest Beschluss und Stimmen aus."""
    d = datetime.date.fromisoformat(heute)
    jahr, mon = d.year, d.month
    seite = None
    for _ in range(14):
        url = "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/%d/%s-%d" % (jahr, MONNAME[mon - 1], jahr)
        try:
            t = get(url, 1)
            if "voted" in t and "Bank Rate" in t: seite = (url, t); break
        except Exception:
            pass
        mon -= 1
        if mon == 0: mon, jahr = 12, jahr - 1
    if not seite: raise ValueError("kein MPC-Protokoll gefunden")
    url, t = seite
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    z = [html.unescape(l.strip()).replace("\xa0", " ").replace("–", "-") for l in re.sub(r"<[^>]+>", "\n", t).splitlines() if l.strip()]
    satz = next((l for l in z if re.search(r"the Monetary Policy Committee \(MPC\) voted", l)), None)
    if not satz: raise ValueError("Beschlusssatz nicht gefunden")
    m = re.search(r"meeting ending on (\d{1,2}) ([A-Z][a-z]+) (20\d\d)", satz)
    sitzung = "%s-%02d-%02d" % (m.group(3), MONEN[m.group(2)], int(m.group(1))) if m and m.group(2) in MONEN else None
    gruppen = []
    for l in z:
        if re.match(r"\d+: ", l) and re.search(r"voted (in favour|against)", l):
            for g in re.finditer(r"(One|Two|Three|Four|Five|Six|Seven|Eight|Nine) members? \(([^)]+)\) voted (in favour|against)([^.]*)\.", l):
                namen = [re.sub(r"\s+", " ", x.strip()) for x in re.split(r",| and ", g.group(2)) if x.strip()]
                gruppen.append({"n": ZAHL[g.group(1)], "namen": namen, "art": g.group(3)})
            if gruppen: break
    if not gruppen:   # Fallback: 'preferred'-Absaetze der Begruendung
        for l in z:
            g = re.match(r"\d+: (One|Two|Three|Four|Five|Six|Seven|Eight|Nine) members? \(([^)]+)\) preferred([^.]*)\.", l)
            if g:
                gruppen.append({"n": ZAHL[g.group(1)], "namen": [x.strip() for x in re.split(r",| and ", g.group(2)) if x.strip()], "art": "preferred"})
    zus = next((l for l in z if re.search(r"MPC also voted", l)), "")
    return {"sitzung": sitzung, "satz": satz, "gruppen": gruppen, "zusatz": zus, "url": url}


# ---------------- ONS: Warenkorb (CPI-Gewichte) und Raten je Position ----------------
MM23 = "https://www.ons.gov.uk/file?uri=/economy/inflationandpriceindices/datasets/consumerpriceindices/current/mm23.csv"
# Gruppen des Warenkorbs: [Schluessel, Name, Farbe, Text, [[ONS-Code, Name], ...]]
INFL_GRUPPEN = [
 ["nahr", "Nahrung und alkoholfreie Getränke", "hsl(28,70%,46%)", "Lebensmittel und alkoholfreie Getränke (ONS-Hauptgruppe 01).",
  [["01.1.1","Brot und Getreide"],["01.1.2","Fleisch"],["01.1.3","Fisch"],["01.1.4","Milch, Käse, Eier"],["01.1.5","Öle und Fette"],["01.1.6","Obst"],["01.1.7","Gemüse und Kartoffeln"],["01.1.8","Zucker, Marmelade, Schokolade, Süßwaren"],["01.1.9","Sonstige Nahrungsmittel"],["01.2","Alkoholfreie Getränke"]]],
 ["energie", "Energie und Wasser", "hsl(0,66%,46%)", "Strom, Gas, Brennstoffe, Wasser und Abwasser sowie Kraftstoffe. Auch der Strompreis wird häufig vom Gaspreis bestimmt.",
  [["04.5.1","Strom"],["04.5.2","Gas"],["04.5.3","Flüssige Brennstoffe (Heizöl)"],["04.5.4","Feste Brennstoffe"],["04.4","Wasser, Abwasser und sonstige Dienste rund ums Haus"],["07.2.2","Kraftstoffe und Schmiermittel"]]],
 ["wohnen", "Wohnen ohne Energie", "hsl(205,55%,42%)", "Tatsächliche Mieten und Instandhaltung der Wohnung. Die Kosten für selbstgenutztes Wohneigentum zählen nicht zum CPI, sondern nur zum CPIH.",
  [["04.1","Mieten"],["04.3","Instandhaltung und Reparaturen der Wohnung"]]],
 ["verkehr", "Verkehr ohne Kraftstoffe", "hsl(175,50%,36%)", "Fahrzeugkauf, Betrieb und Verkehrsdienste.",
  [["07.1.1A","Neuwagen"],["07.1.1B","Gebrauchtwagen"],["07.1.2/3","Motorräder und Fahrräder"],["07.2.1","Ersatzteile und Zubehör"],["07.2.3","Wartung und Reparaturen"],["07.2.4","Sonstige Dienste (Parken, Maut, Fahrstunden, Hauptuntersuchung)"],["07.3.1","Bahn"],["07.3.2/6","Straße und sonstige Verkehrsdienste"],["07.3.3","Flug"],["07.3.4","See- und Binnenschiff"]]],
 ["gast", "Gaststätten und Unterkunft", "hsl(340,50%,48%)", "Restaurants, Cafés, Kantinen und Hotels.",
  [["11.1.1","Restaurants und Cafés"],["11.1.2","Kantinen"],["11.2","Unterkunft"]]],
 ["freizeit", "Freizeit und Kultur", "hsl(265,42%,50%)", "Unterhaltungselektronik, Spielwaren, Haustiere, Sport, Kultur, Bücher und Pauschalreisen.",
  [["09.1","Bild-, Ton- und Datengeräte"],["09.2","Große Freizeitgüter"],["09.3","Sonstige Freizeitartikel, Garten, Haustiere"],["09.4","Freizeit- und Kulturdienste"],["09.5","Bücher, Zeitungen, Schreibwaren"],["09.6","Pauschalreisen"]]],
 ["haushalt", "Haushaltsführung", "hsl(45,65%,42%)", "Möbel, Haushaltsgeräte, Textilien und Haushaltsdienste.",
  [["05.1","Möbel und Teppiche"],["05.2","Haushaltstextilien"],["05.3","Haushaltsgeräte"],["05.4","Geschirr und Küchengeräte"],["05.5","Werkzeug und Gartengeräte"],["05.6","Haushaltsbedarf und -dienste"]]],
 ["kleidung", "Bekleidung und Schuhe", "hsl(310,40%,48%)", "Kleidung und Schuhe.",
  [["03.1","Kleidung"],["03.2","Schuhe"]]],
 ["alktab", "Alkohol und Tabak", "hsl(15,35%,40%)", "Alkoholische Getränke und Tabakwaren.",
  [["02.1","Alkoholische Getränke"],["02.2","Tabak"]]],
 ["gesundheit", "Gesundheit, Kommunikation, Bildung", "hsl(190,45%,38%)", "Medizinische Produkte und Dienste, Post und Telefon, Bildung.",
  [["06.1","Medikamente und medizinische Produkte"],["06.2","Ambulante Dienste"],["06.3","Krankenhausdienste"],["08.1","Post"],["08.2/3","Telefon und Internet"],["10","Bildung"]]],
 ["sonst", "Sonstige Waren und Dienste", "hsl(80,35%,38%)", "Körperpflege, persönliche Gegenstände, Sozialleistungen (zum Beispiel Kinderbetreuung), Versicherungen und Finanzdienste.",
  [["12.1","Körperpflege"],["12.3","Persönliche Gegenstände"],["12.4","Sozialschutz (Kinderbetreuung, Pflege)"],["12.5","Versicherungen"],["12.6","Finanzdienste"],["12.7","Sonstige Dienste"]]]
]
INFL_REIHEN = [["cpi","Inflation gesamt (CPI)","00"],["kern","Kerninflation (ohne Energie, Nahrung, Alkohol, Tabak)",None],["energie","Energie (Strom, Gas, Brennstoffe, Kraftstoffe)",None],["cpih","CPIH (inklusive Wohnkosten der Eigentümer)",None]]
INFL_TITEL = {"cpi":"CPI ANNUAL RATE 00", "kern":"CPI 12mth: Excluding Energy, food, alcoholic beverages & tobacco", "energie":"CPI 12mth: Energy (G)", "cpih":"CPIH ANNUAL RATE 00"}

def ons_gesamt():
    import csv, io
    t = get(MM23, 2) if False else urllib.request.urlopen(urllib.request.Request(MM23, headers=UA), timeout=240).read().decode("utf-8-sig", "replace")
    return list(csv.reader(io.StringIO(t)))


PPI_URL = "https://www.ons.gov.uk/file?uri=/economy/inflationandpriceindices/datasets/producerpriceindexstatisticalbulletindataset/current/ppi.csv"
PPI_LINK = "https://www.ons.gov.uk/economy/inflationandpriceindices/datasets/producerpriceindexstatisticalbulletindataset"
def ppi_reihen():
    """Erzeugerpreise aus der ONS-Datei 'Producer price inflation time series'. Die alte Datei MM22 ist seit Februar 2025 eingestellt.
    Die Datei enthaelt nur Indizes, die Jahresraten werden hier berechnet (Output FSR2 = Fabrikabgabepreise im Inland ohne Steuern, Input FSQT = Einsatzpreise)."""
    import csv, io
    t = urllib.request.urlopen(urllib.request.Request(PPI_URL, headers=UA), timeout=240).read().decode("utf-8-sig", "replace")
    r = list(csv.reader(io.StringIO(t)))
    cd = r[1]
    zeilen = {row[0]: row for row in r if re.fullmatch(r"(19|20)\d\d [A-Z]{3}", row[0])}
    def yoy(code):
        j = cd.index(code); out = []
        for k in zeilen:
            vor = "%d %s" % (int(k[:4]) - 1, k[5:8])
            try: out.append(["%s-%02d-01" % (k[:4], MON[k[5:8]]), round((float(zeilen[k][j]) / float(zeilen[vor][j]) - 1) * 100, 1)])
            except (KeyError, ValueError, ZeroDivisionError): pass
        return [x for x in out if x[0] >= "2000-01-01"]
    return {"ppiout": {"n": "Erzeugerpreise Output (Fabrikabgabe)", "code": "FSR2", "link": PPI_LINK, "r": yoy("FSR2")},
            "ppiin": {"n": "Erzeugerpreise Input (Einsatzpreise)", "code": "FSQT", "link": PPI_LINK, "r": yoy("FSQT")}}

def inflation():
    r = ons_gesamt()
    ti, cd = r[0], r[1]
    jahre = {row[0]: row for row in r[7:] if re.fullmatch(r"\d{4}", row[0])}
    monate = [(i, row[0]) for i, row in enumerate(r) if re.fullmatch(r"(19|20)\d\d [A-Z]{3}", row[0])]
    jahr = max(jahre)
    gew, rate = {}, {}
    for j, x in enumerate(ti):
        m = re.match(r"CPI WEIGHTS ([\d./A-Z]+) ?:? ?", x)
        if m and jahre[jahr][j]: gew[m.group(1)] = float(jahre[jahr][j])
        m = re.match(r"(?:CPI )?ANNUAL RATE ([\d./A-Z]+) ?:? ?", x)
        if m and "CPIH" not in x[:6]: rate.setdefault(m.group(1), j)
    def reihe(j, ab=2015):
        out = []
        for i, mo in monate:
            if int(mo[:4]) < ab: continue
            v = r[i][j] if j < len(r[i]) else ""
            if v.strip() not in ("", "-"):
                try: out.append(["%s-%02d-01" % (mo[:4], MON[mo[5:8]]), round(float(v), 2)])
                except ValueError: pass
        return out
    gruppen, positionen = [], {}
    for key, name, farbe, text, teile in INFL_GRUPPEN:
        liste = []
        for code, dn in teile:
            if code not in gew: continue
            serie = reihe(rate[code]) if code in rate else (reihe(rate[code.split("/")[0]]) if code.split("/")[0] in rate else [])
            liste.append({"c": code, "n": dn, "w": round(gew[code] / 10, 3), "r": serie})
        gruppen.append({"k": key, "n": name, "f": farbe, "t": text, "w": round(sum(x["w"] for x in liste), 3), "teile": liste})
    rest = round(100 - sum(g["w"] for g in gruppen), 2)
    reihen = {}
    for k, n, _ in INFL_REIHEN:
        suche = INFL_TITEL[k]
        j = next((j for j, x in enumerate(ti) if x.startswith(suche)), None)
        if j is not None: reihen[k] = {"n": n, "code": cd[j], "r": reihe(j, 2000)}
    try: reihen.update(ppi_reihen())
    except Exception as e: print("FEHLER PPI", e)
    if not reihen.get("cpi") or not gruppen: raise ValueError("ONS-Warenkorb leer")
    return {"gewichtsjahr": int(jahr), "gruppen": gruppen, "rest": rest, "reihen": reihen, "stand": monate[-1][1], "quelle": MM23}

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
    def j():
        daten["mpc"] = mpc_protokoll(heute)
    for n, fn in [("mpc", j), ("inflation", k_), ("bankrate", a), ("sonia", b), ("gilts", c), ("pfund", d_), ("cpi", e), ("alq", f), ("parlament", g), ("boe_berichte", h), ("boe_termine", i)]: teil(n, fn)
    # letzten guten Stand uebernehmen, wenn ein Teil ausgefallen ist
    if alt:
        for k in ("bankrate", "_letzteTageBank", "sonia", "gilt5", "gilt10", "gilt20", "gbpusd", "gbpeur", "cpi", "alq", "sitze", "posten", "_berichte", "_termine", "mpc", "inflation"):
            if k not in daten and k in alt: daten[k] = alt[k]
    ev_alt = list((alt or {}).get("ereignisse", []))
    ev_neu = neue_ereignisse(alt, daten.get("sitze", []), daten.get("posten", []), daten.get("_berichte", []), heute) if daten.get("sitze") else []
    schon = set((e["d"], e["t"]) for e in ev_alt)
    for e in ev_neu:
        if (e["d"], e["t"]) not in schon: ev_alt.append(e)
    daten["ereignisse"] = sorted(ev_alt, key=lambda e: e["d"])
    daten["_zustand"] = {"posten": {n: h for n, h in daten.get("posten", [])}, "sitze": {n: t for n, t, _ in daten.get("sitze", [])}, "berichte": daten.get("_berichte", []), "mpc": (daten.get("mpc") or {}).get("sitzung")}
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
