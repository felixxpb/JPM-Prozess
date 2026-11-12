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

def get(url, wiederholen=4):
    letzte = None
    for i in range(wiederholen):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8", "replace")
        except Exception as e:
            letzte = e; time.sleep((20 + i * 20) if "429" in str(e) else (2 + i * 3))
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
            for g in re.finditer(r"(?:^\d+: |\. )([A-Z][\w.]*(?: [A-Z][\w.]*)+) voted against", l):
                gruppen.append({"n": 1, "namen": [re.sub(r"\s+", " ", g.group(1).strip())], "art": "against"})
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
    try:
        tag = boe(["IUDSIZC", "IUDMIZC"])
        for k, n, code, daten in [("erw5", "Marktimplizite Inflation, 5 Jahre (Gilts, RPI-basiert)", "IUDSIZC", tag[0]), ("erw10", "Marktimplizite Inflation, 10 Jahre (Gilts, RPI-basiert)", "IUDMIZC", tag[1])]:
            mm = {}
            for d, v in daten:
                if d >= "2000-01-01": mm[d[:7] + "-01"] = round(v, 2)
            if not mm: raise ValueError("leer " + code)
            reihen[k] = {"n": n, "code": code, "r": [[a, b] for a, b in sorted(mm.items())], "qname": "Bank of England, Yield curves (Implied inflation spot curve, " + code + "), letzter Tageswert je Monat", "qurl": "https://www.bankofengland.co.uk/statistics/yield-curves", "qlabel": "Bank of England, Yield curves"}
    except Exception as e: print("FEHLER Erwartungen", e)
    for k, n, code in [("lohn", "Löhne gesamt (regelmäßiges Entgelt, 3-Monats-Durchschnitt)", "KAI9"), ("lohnpriv", "Löhne Privatwirtschaft (regelmäßiges Entgelt, 3-Monats-Durchschnitt)", "KAJ4")]:
        try: reihen[k] = {"n": n, "code": code, "qname": "ONS, Average weekly earnings (Reihe " + code + ", Datensatz LMS)", "qurl": "https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours/timeseries/%s/lms" % code.lower(), "qlabel": "ONS, Zeitreihe " + code, "r": [x for x in ons("/employmentandlabourmarket/peopleinwork/earningsandworkinghours/timeseries/%s/lms" % code.lower()) if x[0] >= "2001-01-01"]}
        except Exception as e: print("FEHLER Lohn", code, e)
    if not reihen.get("cpi") or not gruppen: raise ValueError("ONS-Warenkorb leer")
    agg = {}
    for key, pre in [("waren", "CPI WEIGHTS: Goods"), ("dienste", "CPI WEIGHTS: Services")]:
        j = next((j for j, x in enumerate(ti) if x.startswith(pre)), None)
        if j is not None and jahre[jahr][j].strip(): agg[key] = round(float(jahre[jahr][j]) / 10, 2)
    if len(agg) < 2: agg = None
    return {"gewichtsjahr": int(jahr), "agg": agg, "gruppen": gruppen, "rest": rest, "reihen": reihen, "stand": monate[-1][1], "quelle": MM23}



# ---------------- Arbeitsmarkt (ONS LMS, Nomis Census 2021, Produktivitaet) ----------------
LMS_URL = "https://www.ons.gov.uk/file?uri=/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/datasets/labourmarketstatistics/current/lms.csv"
LMS_LINK = "https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/datasets/labourmarketstatistics"
def datum_q(lbl):
    m = re.fullmatch(r"(\d{4}) ([A-Z]{3})", lbl)
    if m and m.group(2) in MON: return "%s-%02d-01" % (m.group(1), MON[m.group(2)])
    m = re.fullmatch(r"(\d{4}) Q([1-4])", lbl)
    if m: return "%s-%02d-01" % (m.group(1), int(m.group(2)) * 3)
    return None
AM_KPI = [
 ["emp", "Beschäftigungsquote (16 bis 64)", "LF24", "%", "besch"],
 ["alq", "Arbeitslosenquote (ab 16)", "MGSX", "%", "arbeitslos"],
 ["jugend", "Arbeitslosenquote 16 bis 24", "MGWY", "%", "arbeitslos"],
 ["entl", "Entlassungsrate (je 1.000 Beschäftigte)", "BEIR", "‰", "arbeitslos"],
 ["besch", "Beschäftigte (Tsd., ab 16)", "MGRZ", "Tsd.", "besch"],
 ["jobs", "Workforce Jobs (Tsd. Stellen)", "DYDC", "Tsd.", "besch"],
 ["stellen", "Offene Stellen (Tsd.)", "AP2Y", "Tsd.", "nachfrage"],
 ["jestelle", "Arbeitslose je offene Stelle", "JPC5", "", "nachfrage"],
 ["inakt", "Inaktivitätsquote (16 bis 64)", "LF2S", "%", "angebot"],
 ["krank", "Inaktiv wegen Langzeiterkrankung (Tsd., 16 bis 64)", "LF69", "Tsd.", "angebot"],
 ["lohn", "Löhne gesamt (regelmäßiges Entgelt, 3-Monats-Durchschnitt zum Vorjahr)", "KAI9", "%", "lohn"],
 ["lohnpriv", "Löhne Privatwirtschaft (3-Monats-Durchschnitt zum Vorjahr)", "KAJ4", "%", "lohn"],
 ["lohnoeff", "Löhne öffentlicher Sektor (3-Monats-Durchschnitt zum Vorjahr)", "KAJ7", "%", "lohn"],
 ["reallohn", "Reallöhne gesamt (3-Monats-Durchschnitt zum Vorjahr)", "A2FA", "%", "lohn"],
]
AM_BRANCHEN = [
 ["A", "Land- und Forstwirtschaft, Fischerei", "JWR5", "w"], ["B", "Bergbau", "JWR6", "w"], ["C", "Verarbeitendes Gewerbe", "JWR7", "w"],
 ["D", "Energieversorgung", "JWR8", "w"], ["E", "Wasser, Abwasser, Abfall", "JWR9", "w"], ["F", "Baugewerbe", "JWS2", "w"],
 ["G", "Handel und Kfz-Reparatur", "JWS3", "d"], ["H", "Verkehr und Lagerei", "JWS4", "d"], ["I", "Gastgewerbe", "JWS5", "d"],
 ["J", "Information und Kommunikation", "JWS6", "d"], ["K", "Finanz- und Versicherungsdienste", "JWS7", "d"], ["L", "Immobilien", "JWS8", "d"],
 ["M", "Freiberufliche, wissenschaftliche und technische Dienste", "JWS9", "d"], ["N", "Verwaltungs- und Unterstützungsdienste", "JWT2", "d"],
 ["O", "Öffentliche Verwaltung und Verteidigung", "JWT3", "o"], ["P", "Bildung", "JWT4", "o"], ["Q", "Gesundheits- und Sozialwesen", "JWT5", "o"],
 ["R", "Kunst, Unterhaltung, Erholung", "JWT6", "d"], ["S", "Sonstige Dienstleistungen", "JWT7", "d"], ["T", "Private Haushalte als Arbeitgeber", "KW78", "d"],
]
CENSUS_IND = {"1": "Land, Energie, Wasser (A, B, D, E)", "2": "Verarbeitendes Gewerbe (C)", "3": "Baugewerbe (F)", "4": "Handel und Gastgewerbe (G, I)",
              "5": "Verkehr und Kommunikation (H, J)", "6": "Finanzen, Immobilien, Unternehmensdienste (K bis N)", "7": "Verwaltung, Bildung, Gesundheit (O, P, Q)", "8": "Sonstige Dienste (R bis U)"}
NOMIS = "https://www.nomisweb.co.uk/api/v01/dataset/%s.data.csv?geography=2092957703&measures=20100&select=%s"

def lms_gesamt():
    import csv, io
    t = urllib.request.urlopen(urllib.request.Request(LMS_URL, headers=UA), timeout=300).read().decode("utf-8-sig", "replace")
    return list(csv.reader(io.StringIO(t)))

def nomis_csv(ds, sel):
    import csv, io
    return list(csv.DictReader(io.StringIO(get(NOMIS % (ds, sel)))))

def census():
    a = nomis_csv("NM_2162_1", "c2021_ind_9,c2021_ind_9_name,c2021_age_7,obs_value")
    b = nomis_csv("NM_2165_1", "c2021_ind_9,c2021_ind_9_name,c_sex,obs_value")
    alt, sex = {}, {}
    for r in a: alt.setdefault(r["C2021_IND_9"], {})[r["C2021_AGE_7"]] = int(float(r["OBS_VALUE"]))
    for r in b: sex.setdefault(r["C2021_IND_9"], {})[r["C_SEX"]] = int(float(r["OBS_VALUE"]))
    def zeile(k, n):
        x = alt[k]; sx = sex[k]
        return {"k": k, "n": n, "t": x["0"], "alter": [x[str(i)] for i in (2, 3, 4, 5, 6)], "m": sx["2"], "f": sx["1"]}  # Census 2021 bei Nomis: C_SEX 1 = Frauen, 2 = Maenner
    gesamt = zeile("0", "Alle Branchen")
    zeilen = [zeile(k, n) for k, n in CENSUS_IND.items()]
    if gesamt["t"] < 1e6 or len(zeilen) != 8: raise ValueError("Census unvollstaendig")
    return {"alter": ["16 bis 24", "25 bis 34", "35 bis 49", "50 bis 64", "65 und älter"], "gesamt": gesamt, "branchen": zeilen,
            "quelle": "ONS Census 2021 (England und Wales), Nomis-Tabellen RM062 (Branche nach Alter) und RM065 (Branche nach Geschlecht)",
            "link": "https://www.nomisweb.co.uk/census/2021"}

def arbeitsmarkt():
    r = lms_gesamt()
    cd = r[1]; idx = {c: j for j, c in enumerate(cd)}
    zeilen = [(datum_q(row[0]), row) for row in r[7:] if datum_q(row[0])]
    def reihe(code, ab="2000-01-01"):
        j = idx[code]; out = []
        for d, row in zeilen:
            if d < ab or j >= len(row) or row[j].strip() in ("", "-"): continue
            try: out.append([d, float(row[j])])
            except ValueError: pass
        if not out: raise ValueError("leer " + code)
        return out
    reihen = {}
    for k, n, code, einh, grp in AM_KPI:
        try: reihen[k] = {"n": n, "code": code, "u": einh, "g": grp, "r": reihe(code)}
        except Exception as e: print("FEHLER Arbeitsmarkt", code, e)
    branchen = []
    for k, n, code, grp in AM_BRANCHEN:
        branchen.append({"k": k, "n": n, "code": code, "g": grp, "r": reihe(code, "2005-01-01")})
    produktiv = None
    try:
        txt = get("https://www.ons.gov.uk/generator?format=csv&uri=/employmentandlabourmarket/peopleinwork/labourproductivity/timeseries/lzvb/prdy")
        pts = []
        for m in re.finditer(r'^"(\d{4}) Q([1-4])","([-\d.]+)"', txt, re.M): pts.append(["%s-%02d-01" % (m.group(1), int(m.group(2)) * 3), float(m.group(3))])
        yoy = []
        for i in range(4, len(pts)): yoy.append([pts[i][0], round((pts[i][1] / pts[i - 4][1] - 1) * 100, 1)])
        if pts: produktiv = {"index": pts, "yoy": yoy, "code": "LZVB", "n": "Produktivität: Output je Arbeitsstunde (Index 2023 = 100)"}
    except Exception as e: print("FEHLER Produktivitaet", e)
    census_d = None
    try: census_d = census()
    except Exception as e: print("FEHLER Census", e)
    if len(reihen) < 10 or not branchen: raise ValueError("Arbeitsmarkt unvollstaendig")
    return {"reihen": reihen, "branchen": branchen, "produktiv": produktiv, "census": census_d, "quelle": LMS_LINK,
            "stand": max(x["r"][-1][0] for x in reihen.values())}

# ---------------- Finanzsystem und Kredit (Bank of England, BIS) ----------------
FINANZ_BOE = [
 ["haush12", "Kredit an Haushalte (Wachstum zum Vorjahr)", "LPMBZ2K", 1, 1],
 ["hyp12", "Hypothekenbestand (Wachstum zum Vorjahr)", "LPMVTYI", 1, 1],
 ["konsum12", "Verbraucherkredit (Wachstum zum Vorjahr)", "LPMB4TC", 1, 1],
 ["unt12", "Kredit an Unternehmen (Wachstum zum Vorjahr)", "LPMVWNU", 1, 1],
 ["zins2", "Hypothekenzins, 2 Jahre fest, 75 % Beleihung", "IUMBV34", 1, 2],
 ["zins5", "Hypothekenzins, 5 Jahre fest, 75 % Beleihung", "IUMBV42", 1, 2],
 ["zins2_90", "Hypothekenzins, 2 Jahre fest, 90 % Beleihung", "IUMB482", 1, 2],
 ["privat", "Zins Privatkredit (5.000 £)", "IUMBX67", 1, 2],
 ["appr", "Genehmigungen für Hauskauf (Anzahl pro Monat)", "LPMVTVX", 1, 0],
 ["brutto", "Neue Hypothekenkredite brutto (Mrd. £ pro Monat)", "LPMVTVC", 0.001, 2],
 ["rueck", "Tilgungen von Hypothekenkrediten (Mrd. £ pro Monat)", "LPMB86L", 0.001, 2],
]
FINANZ_BESTAND = [["haush", "LPMBZ2A"], ["hyp", "LPMVTXK"], ["konsum", "LPMBI2O"]]
BIS_URL = "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_TC/2.0/Q.GB.%s.A.%s.770.A?format=csv&startPeriod=2000-Q1"

def bis_reihe(sektor, bew):
    import csv, io
    r = list(csv.DictReader(io.StringIO(get(BIS_URL % (sektor, bew)))))
    out = []
    for x in r:
        m = re.fullmatch(r"(\d{4})-Q([1-4])", x.get("TIME_PERIOD", ""))
        if m and x.get("OBS_VALUE"):
            out.append(["%s-%02d-01" % (m.group(1), (int(m.group(2)) - 1) * 3 + 1), round(float(x["OBS_VALUE"]), 1)])
    if not out: raise ValueError("BIS leer")
    return out

def finanz():
    reihen, fehler = {}, []
    for key, name, code, faktor, nd in FINANZ_BOE:
        try:
            r = [[d, round(v * faktor, nd)] for d, v in boe([code])[0] if d >= "2000-01-01"]
            if not r: raise ValueError("leer")
            reihen[key] = {"n": name, "code": code, "r": r}
        except Exception as e:
            fehler.append(key + ": " + str(e)[:60])
    try:
        bank = {d[:7]: v for d, v in monatsende(boe(["IUDBEDR"])[0])}
        z = reihen["zins2"]["r"]
        reihen["spread"] = {"n": "Aufschlag 2-Jahres-Hypothek auf die Bank Rate (Prozentpunkte)", "code": "IUMBV34 minus IUDBEDR",
                            "r": [[d, round(v - bank[d[:7]], 2)] for d, v in z if d[:7] in bank]}
    except Exception as e:
        fehler.append("spread: " + str(e)[:60])
    bestand = {}
    for key, code in FINANZ_BESTAND:
        try:
            r = boe([code])[0]; bestand[key] = [r[-1][0], round(r[-1][1] / 1000, 1)]
        except Exception as e:
            fehler.append(key + ": " + str(e)[:60])
    bis = {}
    for sek in ("H", "N", "G"):
        bis[sek] = {}
        for bew in ("M", "N"):
            try:
                bis[sek][bew] = bis_reihe(sek, bew)
            except Exception as e:
                if not (bew == "N" and sek != "G"): fehler.append("bis " + sek + bew + ": " + str(e)[:60])
    if not reihen.get("haush12") or not bis: raise ValueError("Finanzdaten unvollstaendig: " + "; ".join(fehler))
    return {"reihen": reihen, "bestand": bestand, "bis": bis, "fehler": fehler}


# ---------------- Wirtschaft und Infrastruktur (ONS, DESNZ) ----------------
ONS_BASIS = "https://www.ons.gov.uk"
# [Schluessel, Name, Pfad (Thema/timeseries/code/datensatz), Einheit, Gruppe]
WI_REIHEN = [
 ["bip_q", "BIP-Wachstum zum Vorquartal", "/economy/grossdomesticproductgdp/timeseries/ihyq/qna", "%", "wachstum"],
 ["bip_niveau", "BIP (preisbereinigt, Mio. £)", "/economy/grossdomesticproductgdp/timeseries/abmi/qna", "Mio. £", "wachstum"],
 ["gva_monat", "BIP monatlich (Index, preisbereinigt)", "/economy/grossdomesticproductgdp/timeseries/ecy2/mgdp", "Index", "wachstum"],
 ["dienst", "Index der Dienstleistungen", "/economy/economicoutputandproductivity/output/timeseries/s2ku/ios1", "Index", "wachstum"],
 ["prod", "Industrieproduktion (Index)", "/economy/economicoutputandproductivity/output/timeseries/k222/diop", "Index", "wachstum"],
 ["bizinv", "Unternehmensinvestitionen (preisbereinigt, Mio. £)", "/economy/grossdomesticproductgdp/timeseries/npel/ukea", "Mio. £", "invest"],
 ["anlage", "Bruttoanlageinvestitionen gesamt (preisbereinigt, Mio. £)", "/economy/grossdomesticproductgdp/timeseries/npqt/qna", "Mio. £", "invest"],
 ["psnd", "Nettoschulden des öffentlichen Sektors (% des BIP)", "/economy/governmentpublicsectorandtaxes/publicsectorfinance/timeseries/hf6x/pusf", "%", "staat"],
 ["psnb", "Nettokreditaufnahme des öffentlichen Sektors (Mio. £ pro Monat, positiv = Defizit)", "/economy/governmentpublicsectorandtaxes/publicsectorfinance/timeseries/j5ii/pusf", "Mio. £", "staat"],
 ["waren", "Handelsbilanz Waren (Mio. £ pro Monat)", "/economy/nationalaccounts/balanceofpayments/timeseries/boki/mret", "Mio. £", "aussen"],
 ["dienste", "Handelsbilanz Dienstleistungen (Mio. £ pro Quartal)", "/economy/nationalaccounts/balanceofpayments/timeseries/ikbd/ukea", "Mio. £", "aussen"],
 ["handel", "Handelsbilanz gesamt (Mio. £ pro Quartal)", "/economy/nationalaccounts/balanceofpayments/timeseries/ikbj/ukea", "Mio. £", "aussen"],
 ["leistung", "Leistungsbilanz (Mio. £ pro Quartal)", "/economy/nationalaccounts/balanceofpayments/timeseries/hbop/ukea", "Mio. £", "aussen"],
 ["leistung_bip", "Leistungsbilanz (% des BIP)", "/economy/nationalaccounts/balanceofpayments/timeseries/aa6h/ukea", "%", "aussen"],
]
LLA_JSON = ONS_BASIS + "/economy/grossdomesticproductgdp/datasets/ukgdpolowlevelaggregates/current/data"
ET_API = "https://www.gov.uk/api/content/government/statistics/electricity-section-5-energy-trends"
WI_BRANCHEN = [["A","Land- und Forstwirtschaft, Fischerei","d"],["B","Bergbau","g"],["C","Verarbeitendes Gewerbe","g"],["D","Energieversorgung","g"],
 ["E","Wasser, Abwasser, Abfall","g"],["F","Baugewerbe","g"],["G","Handel und Kfz-Reparatur","d"],["H","Verkehr und Lagerei","d"],["I","Gastgewerbe","d"],
 ["J","Information und Kommunikation","d"],["K","Finanz- und Versicherungsdienste","d"],["L","Immobilien","d"],["M","Freiberufliche, wissenschaftliche und technische Dienste","d"],
 ["N","Verwaltungs- und Unterstützungsdienste","d"],["O","Öffentliche Verwaltung und Verteidigung","s"],["P","Bildung","s"],["Q","Gesundheits- und Sozialwesen","s"],
 ["R","Kunst, Unterhaltung, Erholung","d"],["S","Sonstige Dienstleistungen","d"],["T","Private Haushalte als Arbeitgeber","d"]]

def ons_pfad(pfad):
    """Liest eine ONS-Zeitreihe (Monat, Quartal oder Jahr) und gibt sie nach Zeitraum geordnet zurueck."""
    txt = get(ONS_BASIS + "/generator?format=csv&uri=" + pfad)
    time.sleep(2)
    out, monat = [], []
    for m in re.finditer(r'^"([^"]+)","(-?[\d.]+)"', txt, re.M):
        d = datum_q(m.group(1))
        if not d or d < "1997-01-01": continue
        out.append([d, float(m.group(2))])
        if re.fullmatch(r"\d{4} [A-Z]{3}", m.group(1)): monat.append([d, float(m.group(2))])
    if monat: out = monat  # Monatsreihen: Quartalszeilen derselben Datei weglassen
    if not out: raise ValueError("ONS-Reihe leer " + pfad)
    return sorted(out)

def jahresrate(r, schritt):
    return [[r[i][0], round((r[i][1] / r[i - schritt][1] - 1) * 100, 1)] for i in range(schritt, len(r))]


def bytes_holen(url, versuche=5):
    letzte = None
    for i in range(versuche):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180).read()
        except Exception as e:
            letzte = e; time.sleep((25 + i * 25) if "429" in str(e) else (3 + i * 4))
    raise letzte

def xlsx_zeilen(daten, blatt):
    """Minimaler xlsx-Leser ohne Zusatzpaket: gibt die Zeilen eines Blatts als Listen (Text oder Zahl) zurueck."""
    import zipfile, io
    import xml.etree.ElementTree as ET
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    z = zipfile.ZipFile(io.BytesIO(daten))
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", ns):
            ss.append("".join(t.text or "" for t in si.iter("{%s}t" % ns["m"])))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rid = [s.get("{%s}id" % ns["r"]) for s in wb.find("m:sheets", ns) if s.get("name") == blatt][0]
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    ziel = [r.get("Target") for r in rels if r.get("Id") == rid][0]
    pfad = ziel.lstrip("/") if ziel.startswith("/") else "xl/" + ziel
    def spalte(ref):
        n = 0
        for c in re.match(r"[A-Z]+", ref).group(0): n = n * 26 + ord(c) - 64
        return n - 1
    rows = []
    for row in ET.fromstring(z.read(pfad)).find("m:sheetData", ns):
        r = {}
        for c in row:
            v = c.find("m:v", ns); t = c.get("t")
            if t == "inlineStr": wert = "".join(x.text or "" for x in c.iter("{%s}t" % ns["m"]))
            elif v is None or v.text is None: continue
            elif t == "s": wert = ss[int(v.text)]
            elif t in ("str", "b", "e"): wert = v.text
            else:
                try: wert = float(v.text)
                except ValueError: wert = v.text
            r[spalte(c.get("r"))] = wert
        n = int(row.get("r")) - 1
        while len(rows) < n: rows.append([])
        rows.append([r.get(i) for i in range(max(r) + 1)] if r else [])
    return rows

def branchen_gewichte():
    j = json.loads(get(LLA_JSON))
    datei = j["downloads"][0]["file"]
    b = bytes_holen(ONS_BASIS + "/file?uri=/economy/grossdomesticproductgdp/datasets/ukgdpolowlevelaggregates/current/" + datei)
    rows = xlsx_zeilen(b, "4")
    head = rows[4]; jahr = {}
    for r in rows[6:]:
        if isinstance(r[0], (int, float)): jahr[int(r[0])] = r
    letzte = max(jahr)
    w = jahr[letzte]
    pos = {}
    for i, h in enumerate(head):
        m = re.match(r"^([A-T])\s*\n", str(h or ""))
        if m and m.group(1) not in pos: pos[m.group(1)] = i
    out = []
    for k, n, g in WI_BRANCHEN:
        out.append({"k": k, "n": n, "g": g, "v": round(float(w[pos[k]]) / 10, 1)})
    summe = round(sum(x["v"] for x in out), 1)
    if not (99 <= summe <= 101): raise ValueError("Branchengewichte Summe " + str(summe))
    return {"r": out, "summe": summe, "datei": datei, "quelle": "ONS, UK GDP(O) low level aggregates, Blatt 4 (Gewichte der Wertschöpfung, laufende Preise)"}

def strommix():
    j = json.loads(get(ET_API))
    url = [a["url"] for a in j["details"]["attachments"] if "ET 5.1" in a.get("title", "")][0]
    b = bytes_holen(url)
    rows = xlsx_zeilen(b, "Main Table")
    start = [i for i, r in enumerate(rows) if r and r[0] and str(r[0]).startswith("Shares of electricity generated by fuel")][0]
    kopf = rows[start + 1]
    jahre = [(i, str(c)) for i, c in enumerate(kopf) if c and re.fullmatch(r"\d{4}", str(c))]
    gesucht = {"Coal": "Kohle", "Oil": "Öl", "Gas": "Gas", "Nuclear": "Kernkraft", "Hydro (natural flow)": "Wasserkraft", "Total wind [note 9]": "Wind",
               "Solar": "Solar", "Bioenergy [note 10]": "Biomasse", "Other fuels [note 10]": "Sonstige"}
    reihen = []
    for r in rows[start + 2:start + 18]:
        if len(r) > 1 and r[1] in gesucht:
            reihen.append({"n": gesucht[r[1]], "r": [[int(y), round(float(r[i]), 1)] for i, y in jahre if i < len(r) and isinstance(r[i], (int, float))]})
    if len(reihen) < 7: raise ValueError("Strommix unvollstaendig")
    return {"reihen": reihen, "url": url, "quelle": "DESNZ, Energy Trends Tabelle 5.1 (Anteile an der Stromerzeugung nach Brennstoff, Jahresdaten)"}

def wirtschaft():
    reihen, fehler = {}, []
    for key, name, pfad, einh, grp in WI_REIHEN:
        try:
            r = ons_pfad(pfad)
            if key == "psnb": r = [[d, -v] for d, v in r]  # ONS-Vorzeichen: Minus = Kreditaufnahme; hier positiv = Defizit
            reihen[key] = {"n": name, "u": einh, "g": grp, "code": pfad.split("/")[-2].upper(), "qurl": ONS_BASIS + pfad, "r": [x for x in r if x[0] >= "2000-01-01"]}
        except Exception as e:
            fehler.append(key + ": " + str(e)[:70]); print("FEHLER Wirtschaft", key, e)
    try:
        n = ons_pfad("/economy/grossdomesticproductgdp/timeseries/abmi/qna")
        reihen["bip_j"] = {"n": "BIP-Wachstum zum Vorjahr (aus dem Niveau gerechnet)", "u": "%", "g": "wachstum", "code": "ABMI, gerechnet",
                           "qurl": ONS_BASIS + "/economy/grossdomesticproductgdp/timeseries/abmi/qna", "r": [x for x in jahresrate(n, 4) if x[0] >= "2000-01-01"]}
        if "bizinv" in reihen:
            b = ons_pfad("/economy/grossdomesticproductgdp/timeseries/npel/ukea")
            reihen["bizinv_j"] = {"n": "Unternehmensinvestitionen (Wachstum zum Vorjahr, gerechnet)", "u": "%", "g": "invest", "code": "NPEL, gerechnet",
                                  "qurl": ONS_BASIS + "/economy/grossdomesticproductgdp/timeseries/npel/ukea", "r": [x for x in jahresrate(b, 4) if x[0] >= "2000-01-01"]}
    except Exception as e:
        fehler.append("bip_j: " + str(e)[:70])
    kuchen = mix = None
    try: kuchen = branchen_gewichte()
    except Exception as e: fehler.append("branchen: " + str(e)[:80]); print("FEHLER Branchen", e)
    try: mix = strommix()
    except Exception as e: fehler.append("strommix: " + str(e)[:80]); print("FEHLER Strommix", e)
    if len(reihen) < 10 or not kuchen: raise ValueError("Wirtschaft unvollstaendig: " + "; ".join(fehler))
    return {"reihen": reihen, "kuchen": kuchen, "strommix": mix, "fehler": fehler,
            "stand": max(x["r"][-1][0] for x in reihen.values())}


# ---------------- Handel und Beziehungen (HMRC uktradeinfo, ONS) ----------------
HMRC = "https://api.uktradeinfo.com/"
HM_PAUSE = 4  # Sekunden zwischen Anfragen (die Schnittstelle sperrt sonst mit 403)
HM_KEINLAND = ("Low Value Non EU", "Not Collected", "Unallocated", "Stores", "Provisions", "Miscellaneous", "Confidential", "Unknown", "EU Not Allocated", "Non EU Not Allocated")

def hmrc(pfad, **q):
    import urllib.parse
    url = HMRC + pfad + ("?" + urllib.parse.urlencode(q) if q else "")
    letzte = None
    for i in range(6):
        try:
            time.sleep(HM_PAUSE)
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180).read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            letzte = e
            if e.code in (403, 429): time.sleep(30 * (i + 1)); continue
            raise
        except Exception as e:
            letzte = e; time.sleep(5 + i * 5)
    raise letzte

def hm_monate(ende, n):
    """Liste der MonthIds: n Monate bis einschliesslich ende (z. B. 202609)."""
    j, m = ende // 100, ende % 100
    out = []
    for _ in range(n):
        out.append(j * 100 + m); m -= 1
        if m == 0: j -= 1; m = 12
    return sorted(out)

def hm_gruppe(monate, flows, gruppen, extra=""):
    """Summe des Warenwerts (GBP) je Gruppe ueber Monate und Verkehrsrichtungen."""
    f = "MonthId ge %d and MonthId le %d and (%s)%s" % (monate[0], monate[-1], " or ".join("FlowTypeId eq %d" % x for x in flows), extra)
    r = hmrc("OTS", **{"$apply": "filter(%s)/groupby((%s),aggregate(Value with sum as V))" % (f, gruppen), "$top": 5000})
    return r["value"]

def sdiv(sid):
    """SITC-Abteilung (2 Stellen) aus der CommoditySitcId: 5-stellige Codes (97101 = Gold) -> 97, 2-stellige gelten selbst."""
    if sid >= 10000: return sid // 1000
    if 0 <= sid < 100: return sid
    return None

def sitc1(sid):
    d = sdiv(sid)
    return str(d // 10) if d is not None else "?"

def hm_sitc():
    out = {}
    for x in hmrc("SITC", **{"$top": 1000})["value"]:
        out[x["CommoditySitcId"]] = (str(x["Sitc1Code"] or "").strip(), str(x["Sitc1Desc"] or "").strip(), str(x["SitcCode"] or "").strip())
    return out

SITC1_DE = {"0": "Nahrungsmittel und lebende Tiere", "1": "Getränke und Tabak", "2": "Rohstoffe (ohne Brennstoffe)", "3": "Brennstoffe und Energie",
            "4": "Tierische und pflanzliche Öle und Fette", "5": "Chemische Erzeugnisse (inkl. Pharma)", "6": "Bearbeitete Waren (Metalle, Textilien u. a.)",
            "7": "Maschinen und Fahrzeuge", "8": "Verschiedene Fertigwaren", "9": "Sonstiges"}

def ons_reihe_q(pfad, ab="2000-01-01"):
    return [x for x in ons_pfad(pfad) if x[0] >= ab]

HA_ONS = [
 ["dienst_exp", "Dienstleistungsexporte (Mio. £ pro Quartal)", "/economy/nationalaccounts/balanceofpayments/timeseries/ikbb/ukea", "Mio. £"],
 ["dienst_imp", "Dienstleistungsimporte (Mio. £ pro Quartal)", "/economy/nationalaccounts/balanceofpayments/timeseries/ikbc/ukea", "Mio. £"],
 ["dienst_saldo", "Handelsbilanz Dienstleistungen (Mio. £ pro Quartal)", "/economy/nationalaccounts/balanceofpayments/timeseries/ikbd/ukea", "Mio. £"],
 ["waren_saldo_q", "Handelsbilanz gesamt (Mio. £ pro Quartal)", "/economy/nationalaccounts/balanceofpayments/timeseries/ikbj/ukea", "Mio. £"],
 ["primaer", "Primäreinkommen, Saldo (Mio. £ pro Quartal)", "/economy/nationalaccounts/balanceofpayments/timeseries/hmbp/ukea", "Mio. £"],
 ["sekundaer", "Sekundäreinkommen, Saldo (Mio. £ pro Quartal)", "/economy/nationalaccounts/balanceofpayments/timeseries/ikbp/ukea", "Mio. £"],
 ["leistung", "Leistungsbilanz (Mio. £ pro Quartal)", "/economy/nationalaccounts/balanceofpayments/timeseries/hbop/ukea", "Mio. £"],
 ["finanz_netto", "Kapitalbilanz: Nettokapitalströme (Mio. £ pro Quartal)", "/economy/nationalaccounts/balanceofpayments/timeseries/hbnt/ukea", "Mio. £"],
 ["wertpapier", "Wertpapieranlagen: Nettoströme (Mio. £ pro Quartal)", "/economy/nationalaccounts/balanceofpayments/timeseries/hhzd/ukea", "Mio. £"],
 ["fdi_zu", "Direktinvestitionen aus dem Ausland: Beteiligungskapital (Mio. £ pro Quartal)", "/economy/nationalaccounts/balanceofpayments/timeseries/hjyr/ukea", "Mio. £"],
]
EU_CODES = {"AT","BE","BG","HR","CY","CZ","DK","EE","FI","FR","DE","GR","HU","IE","IT","LV","LT","LU","MT","NL","PL","PT","RO","SK","SI","ES","SE"}
TIS_JSON = ONS_BASIS + "/businessindustryandtrade/internationaltrade/datasets/uktradeinservicesservicetypebypartnercountrynonseasonallyadjusted/current/data"
TIS_TYPEN = {"1":"Verarbeitung für andere","2":"Wartung und Reparatur","3":"Transport","4":"Reisen","5":"Bau","6":"Versicherung und Pensionen","7":"Finanzdienstleistungen","8":"Geistiges Eigentum (Lizenzen)",
             "9":"Telekommunikation, IT und Information","10":"Sonstige Unternehmensdienste","11":"Persönliche, Kultur und Erholung","12":"Staatliche Leistungen"}

def dienste_nach_art():
    j = json.loads(get(TIS_JSON))
    datei = j["downloads"][0]["file"]
    b = bytes_holen(ONS_BASIS + "/file?uri=/businessindustryandtrade/internationaltrade/datasets/uktradeinservicesservicetypebypartnercountrynonseasonallyadjusted/current/" + datei)
    blatt = None
    import zipfile, io
    namen = re.findall(r'<sheet [^>]*name="([^"]+)"', zipfile.ZipFile(io.BytesIO(b)).read("xl/workbook.xml").decode())
    jahr = [n for n in namen if re.fullmatch(r"Sheet \d+\. \d{4}", n)]
    if not jahr: raise ValueError("Jahresblatt fehlt")
    blatt = sorted(jahr, key=lambda n: n.split(". ")[1])[-1]
    rows = xlsx_zeilen(b, blatt)
    def tabelle(start_text):
        i0 = next(i for i, r in enumerate(rows) if r and r[0] and str(r[0]).startswith(start_text))
        kopf = rows[i0 + 1]
        spalten = {}
        for j2, h in enumerate(kopf):
            m = re.match(r"^(\d+): ", str(h or ""))
            if m: spalten[m.group(1)] = j2
        out = []
        for r in rows[i0 + 2:]:
            if not r or not r[0] or str(r[0]).startswith("Table"): break
            if len(r) < 3: continue
            def zahl(k):
                v = r[spalten[k]] if k in spalten and spalten[k] < len(r) else None
                return float(v) if isinstance(v, (int, float)) else None
            out.append({"c": str(r[0]), "n": str(r[1]), "t": zahl("0"), "a": {k: zahl(k) for k in TIS_TYPEN}})
        return out
    exp = tabelle("Table 2A"); imp = tabelle("Table 2B")
    if len(exp) < 30 or len(imp) < 30: raise ValueError("Dienstleistungstabellen zu klein")
    return {"jahr": blatt.split(". ")[1], "exp": exp, "imp": imp, "typen": TIS_TYPEN, "datei": datei,
            "quelle": "ONS, UK trade in services: service type by partner country, non-seasonally adjusted (Jahresblatt " + blatt.split(". ")[1] + ", Mio. £)"}

def handel():
    fehler = []
    # --- Waren: Partner, Produkte (HMRC, 12 Monate, in GBP) ---
    ende = None
    heute = datetime.date.today()
    j, m = heute.year, heute.month
    for _ in range(8):
        mid = j * 100 + m
        if hmrc("OTS", **{"$filter": "MonthId eq %d and FlowTypeId eq 2" % mid, "$top": 1})["value"]: ende = mid; break
        m -= 1
        if m == 0: j -= 1; m = 12
    if not ende: raise ValueError("HMRC: kein Monat gefunden")
    fenster = hm_monate(ende, 12)
    f0 = fenster[0]
    vor = hm_monate((f0 // 100 - 1) * 100 + 12 if f0 % 100 == 1 else f0 - 1, 12)
    laender = {x["CountryId"]: {"c": (x["CountryCodeAlpha"] or "").strip(), "n": (x["CountryName"] or "").strip(), "eu": (x["Area1a"] or "").strip() == "European Union"} for x in hmrc("Country", **{"$top": 1000})["value"]}
    gold_ids = [97]
    gold_f = " and CommoditySitcId ne 97 and (CommoditySitcId lt 97000 or CommoditySitcId ge 98000)"
    gold_nur = " and (CommoditySitcId eq 97 or (CommoditySitcId ge 97000 and CommoditySitcId lt 98000))"
    def summe(monate, flows, gruppe="CountryId", gold=False):
        out = {}
        for x in hm_gruppe(monate, flows, gruppe, gold_nur if gold else gold_f): out[x[gruppe]] = x["V"]
        return out
    partner = {}; goldsum = {}
    for rich, flows in (("imp", [1, 3]), ("exp", [2, 4])):
        try:
            jetzt, davor = summe(fenster, flows), summe(vor, flows)
            gj, gv = summe(fenster, flows, "CountryId", True), summe(vor, flows, "CountryId", True)
            goldsum[rich] = [round(sum(gj.values()) / 1e6), round(sum(gv.values()) / 1e6)]
            lst = []
            for cid, v in jetzt.items():
                L = laender.get(cid)
                if not L or L["n"] in HM_KEINLAND or L["n"].startswith(("Low Value", "Confidential")) or v <= 0: continue
                lst.append({"c": L["c"], "n": L["n"], "eu": L["eu"], "v": round(v / 1e6), "vj": round(davor.get(cid, 0) / 1e6), "g": round(gj.get(cid, 0) / 1e6), "gv": round(gv.get(cid, 0) / 1e6)})
            lst.sort(key=lambda x: -x["v"])
            partner[rich] = lst
        except Exception as e:
            fehler.append("partner " + rich + ": " + str(e)[:80]); print("FEHLER Handel Partner", rich, e)
    produkte = {}
    for rich, flows in (("imp", [1, 3]), ("exp", [2, 4])):
        try:
            jetzt, davor = summe(fenster, flows, "CommoditySitcId"), summe(vor, flows, "CommoditySitcId")
            agg, agg0 = {}, {}
            for sid, v in jetzt.items():
                k = sitc1(sid)
                if k in SITC1_DE: agg[k] = agg.get(k, 0) + v
            for sid, v in davor.items():
                k = sitc1(sid)
                if k in SITC1_DE: agg0[k] = agg0.get(k, 0) + v
            produkte[rich] = [{"k": k, "n": SITC1_DE[k], "v": round(v / 1e6), "vj": round(agg0.get(k, 0) / 1e6)} for k, v in sorted(agg.items(), key=lambda kv: -kv[1])]
        except Exception as e:
            fehler.append("produkte " + rich + ": " + str(e)[:80]); print("FEHLER Handel Produkte", rich, e)
    # --- Partner x Produktgruppe fuer die wichtigsten Partner (fuer die Karte) ---
    karte = {}
    cid_von = {(L["c"], L["n"]): cid for cid, L in laender.items()}
    for rich, flows in (("imp", [1, 3]), ("exp", [2, 4])):
        for p in (partner.get(rich) or [])[:14]:
            try:
                cid = cid_von[(p["c"], p["n"])]
                f = "MonthId ge %d and MonthId le %d and CountryId eq %d and (%s)%s" % (fenster[0], fenster[-1], cid, " or ".join("FlowTypeId eq %d" % x for x in flows), gold_f)
                rr = hmrc("OTS", **{"$apply": "filter(%s)/groupby((CommoditySitcId),aggregate(Value with sum as V))" % f, "$top": 5000})["value"]
                agg = {}
                for x in rr:
                    k = sitc1(x["CommoditySitcId"])
                    if k in SITC1_DE: agg[k] = agg.get(k, 0) + x["V"]
                karte.setdefault(rich, {})[p["c"] + "|" + p["n"]] = {k: round(v / 1e6) for k, v in agg.items() if v > 0}
            except Exception as e:
                fehler.append("karte " + rich + " " + p["n"] + ": " + str(e)[:60])
    # --- Monatsreihe Gesamt-Warenhandel (36 Monate) ---
    monatlich = {}
    try:
        m36 = hm_monate(ende, 36)
        for rich, flows in (("imp", [1, 3]), ("exp", [2, 4])):
            r = hm_gruppe(m36, flows, "MonthId", gold_f)
            monatlich[rich] = [["%04d-%02d-01" % (x["MonthId"] // 100, x["MonthId"] % 100), round(x["V"] / 1e9, 2)] for x in sorted(r, key=lambda y: y["MonthId"])]
    except Exception as e:
        fehler.append("monatlich: " + str(e)[:80])
    # --- ONS: Dienstleistungen, Zahlungsbilanz ---
    reihen = {}
    for key, name, pfad, einh in HA_ONS:
        try:
            reihen[key] = {"n": name, "u": einh, "code": pfad.split("/")[-2].upper(), "qurl": ONS_BASIS + pfad, "r": ons_reihe_q(pfad)}
        except Exception as e:
            fehler.append(key + ": " + str(e)[:70]); print("FEHLER Handel ONS", key, e)
    tis = None
    try: tis = dienste_nach_art()
    except Exception as e: fehler.append("dienste_art: " + str(e)[:80]); print("FEHLER Dienste nach Art", e)
    if not partner.get("imp") or not partner.get("exp") or len(reihen) < 6: raise ValueError("Handel unvollstaendig: " + "; ".join(fehler))
    return {"von": "%04d-%02d" % (fenster[0] // 100, fenster[0] % 100), "bis": "%04d-%02d" % (ende // 100, ende % 100), "partner": partner, "gold": goldsum, "produkte": produkte, "karte": karte,
            "monatlich": monatlich, "reihen": reihen, "dienste": tis, "eu_codes": sorted(EU_CODES), "fehler": fehler,
            "quelle": "HMRC, UK overseas trade in goods statistics (uktradeinfo, Warenwert in Pfund, 12 Monate bis " + "%04d-%02d" % (ende // 100, ende % 100) + ")",
            "stand": "%04d-%02d-01" % (ende // 100, ende % 100)}

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
    def k_():
        daten["inflation"] = inflation()
    def f_():
        daten["finanz"] = finanz()
    def am_():
        daten["arbeitsmarkt"] = arbeitsmarkt()
    def wi_():
        daten["wirtschaft"] = wirtschaft()
    def ha_():
        daten["handel"] = handel()
    for n, fn in [("mpc", j), ("inflation", k_), ("finanz", f_), ("arbeitsmarkt", am_), ("wirtschaft", wi_), ("handel", ha_), ("bankrate", a), ("sonia", b), ("gilts", c), ("pfund", d_), ("cpi", e), ("alq", f), ("parlament", g), ("boe_berichte", h), ("boe_termine", i)]: teil(n, fn)
    # letzten guten Stand uebernehmen, wenn ein Teil ausgefallen ist
    if alt:
        for k in ("bankrate", "_letzteTageBank", "sonia", "gilt5", "gilt10", "gilt20", "gbpusd", "gbpeur", "cpi", "alq", "sitze", "posten", "_berichte", "_termine", "mpc", "inflation", "finanz", "wirtschaft", "handel", "arbeitsmarkt"):
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
