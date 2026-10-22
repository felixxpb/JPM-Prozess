#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Laender_Abrufen_USA.py  -  Datenabruf fuer die Laenderanalyse USA (Projekt JPM Prozess)

Was das Skript tut:
  1. FRED: holt die Verlaeufe der Kennzahlen fuer USA Oberthema 2 (und weitere folgen)
  2. Wikipedia ("Political party strength in U.S. states"): Staatsregierungen,
     Kongress-Sitzverteilung, Ergebnis der Praesidentschaftswahl 2024 je Staat
  3. Schreibt alles in EINE Datei:  <Ausgabeordner>/usa.js   (window.USA_DATEN = {...})

Sicherheitsprinzip: Faellt eine Quelle aus oder sehen die Daten unplausibel aus,
bleibt der zuletzt gute Block dieser Quelle in der Datei stehen, der Fehler wird in
"meta.fehler" vermerkt. Das Skript bricht nie die ganze Datei ab.

Aufruf lokal:      python -X utf8 Laender_Abrufen_USA.py
Aufruf GitHub:     gleich, mit Umgebungsvariablen
   FRED_API_KEY          (lokal alternativ aus zugangsdaten.txt, nie ausgeben!)
   LAENDER_DATEN         Ausgabeordner (Standard: ..\\laender\\daten relativ zum Skript)
Nur Python-Standardbibliothek, keine Installation noetig.
"""
import json, os, re, sys, html, urllib.request, urllib.parse, datetime

HIER = os.path.dirname(os.path.abspath(__file__))
AUSGABE = os.environ.get("LAENDER_DATEN") or os.path.join(HIER, "..", "laender", "daten")
DATEI = os.path.join(AUSGABE, "usa.js")
UA = "TradingBrainLaenderanalyse/1.0 (fbrinkmann78@gmail.com)"

# FRED-Reihen: Name -> Startdatum des Verlaufs
FRED = {
    "NFCI": "2022-01-01", "WALCL": "2022-01-01",
    "DGS10": "2024-10-01", "DGS2": "2024-10-01", "DGS30": "2024-10-01", "T10Y2Y": "2024-10-01",
    "GFDEBTN": "2015-01-01", "GFDEGDQ188S": "2015-01-01",
    "DRTSCILM": "2015-01-01", "DRTSCLCC": "2015-01-01",
    "BAMLH0A0HYM2": "2024-10-01", "BAMLC0A0CM": "2024-10-01",
    # Oberthema 3 (Fed)
    "DFEDTARU": "2024-10-01", "DFEDTARL": "2024-10-01", "DFF": "2024-10-01", "IORB": "2024-10-01",
    "UNRATE": "2022-01-01",
    # Oberthema 6 (Inflation): Erwartungen (Michigan 1 Jahr, Breakeven 5J/10J, 5J-in-5J)
    "MICH": "2022-01-01", "T5YIE": "2024-10-01", "T10YIE": "2024-10-01", "T5YIFR": "2024-10-01",
    # Oberthema 7 (Arbeitsmarkt): Beschaeftigte nach Branche (CES, in Tausend, ab 2019 fuer den Vergleich mit Feb 2020)
    "PAYEMS": "2019-01-01", "USPRIV": "2019-01-01", "USGOOD": "2019-01-01", "USGOVT": "2019-01-01",
    "USMINE": "2019-01-01", "USCONS": "2019-01-01", "MANEMP": "2019-01-01", "DMANEMP": "2019-01-01", "NDMANEMP": "2019-01-01",
    "USTPU": "2019-01-01", "USWTRADE": "2019-01-01", "USTRADE": "2019-01-01", "CES4300000001": "2019-01-01", "CES4422000001": "2019-01-01",
    "USINFO": "2019-01-01", "USFIRE": "2019-01-01", "USPBS": "2019-01-01", "USEHS": "2019-01-01",
    "CES6561000001": "2019-01-01", "CES6562000001": "2019-01-01", "USLAH": "2019-01-01", "USSERV": "2019-01-01",
    "CES9091000001": "2019-01-01", "CES9092000001": "2019-01-01", "CES9093000001": "2019-01-01",
    # Arbeitslosigkeit, Angebot, Nachfrage nach Arbeit
    "U6RATE": "2022-01-01", "CIVPART": "2022-01-01", "LNS11300060": "2022-01-01", "LNS12300060": "2022-01-01", "LNS13025703": "2022-01-01",
    "JTSJOL": "2022-01-01", "JTSQUR": "2022-01-01", "JTSHIR": "2022-01-01", "JTSLDL": "2022-01-01",
    "ICSA": "2024-10-01", "CCSA": "2024-10-01",
    # Oberthema 4 (Wirtschaft und Infrastruktur)
    "A191RL1Q225SBEA": "2015-01-01", "GDPC1": "2015-01-01",
    "GDP": "2015-01-01", "PCEC": "2015-01-01", "GPDI": "2015-01-01", "GCE": "2015-01-01", "NETEXP": "2015-01-01",
    "INDPRO": "2022-01-01", "TCU": "2022-01-01",
    "A679RC1Q027SBEA": "2015-01-01",
    "MCOILWTICO": "2022-01-01", "MHHNGSP": "2022-01-01", "IPG2211S": "2022-01-01",
    "TLPBLCONS": "2022-01-01", "TLPWRCONS": "2022-01-01", "TLHWYCONS": "2022-01-01",
    "IEABC": "2015-01-01", "BOPGSTB": "2022-01-01",
    # Branchenanteile an der Wertschoepfung (BEA, in % des BIP, vierteljaehrlich)
    "VAPGDPSPI": "2015-01-01", "VAPGDPGPI": "2015-01-01", "VAPGDPG": "2015-01-01",
    "VAPGDPFIRL": "2015-01-01", "VAPGDPPBS": "2015-01-01", "VAPGDPMA": "2015-01-01",
    "VAPGDPESHS": "2015-01-01", "VAPGDPW": "2015-01-01", "VAPGDPI": "2015-01-01",
    "VAPGDPR": "2015-01-01", "VAPGDPC": "2015-01-01", "VAPGDPT": "2015-01-01",
    "VAPGDPM": "2015-01-01", "VAPGDPU": "2015-01-01", "VAPGDPAFH": "2015-01-01",
    "BOPTEXP": "2022-01-01", "BOPTIMP": "2022-01-01", "DTWEXBGS": "2024-10-01",
    "FDHBFIN": "2015-01-01",   # Bundesschulden im Besitz von Auslaendern (Mrd. USD)
    "VAPGDPAERAF": "2015-01-01", "VAPGDPOSEG": "2015-01-01", "VAPGDPF": "2015-01-01", "VAPGDPSL": "2015-01-01",
    # Oberthema 8 (Sentiment und Verbraucherverhalten)
    "UMCSENT": "2018-01-01",
    "PCEDG": "2019-01-01", "PCEND": "2019-01-01", "PCES": "2019-01-01", "PCEC96": "2019-01-01", "RSAFS": "2019-01-01",
    "PSAVERT": "2019-01-01", "TOTALSL": "2019-01-01", "REVOLSL": "2019-01-01", "DRCCLACBS": "2015-01-01", "TDSP": "2015-01-01",
    "DSPIC96": "2019-01-01", "TNWBSHNO": "2015-01-01",
    # Konsumkuchen: Konsumausgaben nach Verwendungszweck (BEA, Mrd. USD, vierteljaehrlich, auf Jahresrate)
    "DHLCRC1Q027SBEA": "2015-01-01", "DHUTRC1Q027SBEA": "2015-01-01", "DTRSRC1Q027SBEA": "2015-01-01",
    "DMOTRC1Q027SBEA": "2015-01-01", "DFXARC1Q027SBEA": "2015-01-01", "DFSARC1Q027SBEA": "2015-01-01",
    "DCLORC1Q027SBEA": "2015-01-01", "DREQRC1Q027SBEA": "2015-01-01", "DRCARC1Q027SBEA": "2015-01-01",
    "DGOERC1Q027SBEA": "2015-01-01", "DNRGRC1Q027SBEA": "2015-01-01", "DOTSRC1Q027SBEA": "2015-01-01",
    # Oberthema 9 (Umwelt und Klima): Energiepreise
    "APU000072610": "2019-01-01", "GASREGW": "2022-01-01", "DHOILNYH": "2024-10-01",
}
# Reihen mit Umrechnung: Name -> (FRED-Reihe, Umrechnung, Start). pc1 = Veraenderung zum Vorjahr in Prozent
FRED_UMGERECHNET = {
    "PCEPILFE_YOY": ("PCEPILFE", "pc1", "2022-01-01"),
    "PCEPI_YOY": ("PCEPI", "pc1", "2022-01-01"),
    "OPHNFB_YOY": ("OPHNFB", "pc1", "2018-01-01"),
    # Oberthema 6 (Inflation)
    "CPIAUCSL_YOY": ("CPIAUCSL", "pc1", "2022-01-01"),
    "CPILFESL_YOY": ("CPILFESL", "pc1", "2022-01-01"),
    "PPIFIS_YOY": ("PPIFIS", "pc1", "2022-01-01"),
    "PPIFES_YOY": ("PPIFES", "pc1", "2022-01-01"),
    "CUSR0000SAH1_YOY": ("CUSR0000SAH1", "pc1", "2022-01-01"),     # Wohnen (Shelter-nahe Reihe: Housing)
    "CPIENGSL_YOY": ("CPIENGSL", "pc1", "2022-01-01"),              # Energie
    "CPIUFDSL_YOY": ("CPIUFDSL", "pc1", "2022-01-01"),              # Nahrungsmittel
    "CES0500000003_YOY": ("CES0500000003", "pc1", "2022-01-01"),    # Stundenlohn privater Sektor
    "PAYEMS_CHG": ("PAYEMS", "chg", "2022-01-01"),                   # Beschaeftigtenaenderung zum Vormonat (Tausend)
    "ECIWAG_YOY": ("ECIWAG", "pc1", "2022-01-01"),                   # Employment Cost Index Loehne, zum Vorjahr
    # Oberthema 8 (Verbraucher): Veraenderung zum Vorjahr
    "PCEC96_YOY": ("PCEC96", "pc1", "2022-01-01"),
    "RSAFS_YOY": ("RSAFS", "pc1", "2022-01-01"),
    "DSPIC96_YOY": ("DSPIC96", "pc1", "2022-01-01"),
    "TOTALSL_YOY": ("TOTALSL", "pc1", "2022-01-01"),
    # Oberthema 9: Preisindizes Strom und Benzin, zum Vorjahr
    "CPI_STROM_YOY": ("CUSR0000SEHF01", "pc1", "2022-01-01"),
    "CPI_BENZIN_YOY": ("CUSR0000SETB01", "pc1", "2022-01-01"),
}


def fred_key():
    k = os.environ.get("FRED_API_KEY")
    if k and k.strip():
        # Robust gegen Tippfehler beim Eintragen (Leerzeichen, "FRED_API_KEY=" davor, Anfuehrungszeichen):
        # ein FRED-Schluessel besteht aus genau 32 Kleinbuchstaben/Ziffern.
        m = re.search(r"[a-z0-9]{32}", k.strip().lower())
        if not m:
            raise ValueError("FRED_API_KEY (Secret) hat kein gueltiges Format: Laenge %d statt 32 Zeichen" % len(k.strip()))
        return m.group(0)
    # Lokal: Schluessel aus dem Dashboard-Ordner des Trading Brain (liegt NICHT im Repository)
    pfad = os.path.join(HIER, "..", "..", "05_Dashboard", "02_Datenskripte", "zugangsdaten.txt")
    m = re.search(r"FRED_API_KEY=(\S+)", open(pfad, encoding="utf-8").read())
    return m.group(1)


def holen(url, versuche=3):
    letzter = None
    for _ in range(versuche):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
        except Exception as e:  # noqa
            letzter = e
    raise letzter


def lade_fred():
    key = fred_key()
    out = {}
    alle = {s: (s, None, st) for s, st in FRED.items()}
    alle.update(FRED_UMGERECHNET)
    for sid, (reihe, units, start) in alle.items():
        u = ("https://api.stlouisfed.org/fred/series/observations?series_id=%s&api_key=%s"
             "&file_type=json&observation_start=%s" % (reihe, key, start))
        if units:
            u += "&units=" + units
        try:
            obs = json.loads(holen(u))["observations"]
        except Exception as e:  # noqa
            raise ValueError("FRED-Reihe %s: %s" % (sid, e))
        pts = [[o["date"], float(o["value"])] for o in obs if o["value"] not in (".", "")]
        if len(pts) > 600:  # lange Tagesreihen ausduennen, letzter Punkt bleibt
            pts = pts[::2] + ([pts[-1]] if (len(pts) - 1) % 2 else [])
        if len(pts) < 5:
            raise ValueError("zu wenige Punkte fuer " + sid)
        out[sid] = pts
    return out


# ---------------------------------------------------------------- Wikipedia
STAATEN = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY",
}


def zelle_text(z):
    z = re.sub(r"<sup.*?</sup>", "", z, flags=re.S)
    z = re.sub(r"<[^>]+>", "", z)
    return html.unescape(z).replace("\xa0", " ").strip()


def partei(t):
    """Aus einem Zellentext die Partei ableiten: R, D oder X (sonstige/Koalition)."""
    t = t.lower()
    if t.startswith("republican"):
        return "R"
    if t.startswith("democrat") or t.startswith("dfl"):
        return "D"
    return "X"


def lade_wikipedia():
    u = ("https://en.wikipedia.org/w/api.php?action=parse&page=Political_party_strength_in_U.S._states"
         "&prop=text&format=json&formatversion=2")
    h = json.loads(holen(u))["parse"]["text"]
    # die Tabelle mit "State Senate" in der Kopfzeile suchen
    tabs = re.findall(r"<table.*?</table>", h, flags=re.S)
    tab = next(t for t in tabs if "State Senate" in t and "Governor" in t and "Alabama" in t)
    staaten = {}
    for tr in re.findall(r"<tr.*?</tr>", tab, flags=re.S):
        zellen = [zelle_text(z) for z in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S)]
        if not zellen or zellen[0] not in STAATEN:
            continue
        if len(zellen) == 7:  # Nebraska: nur eine Kammer, Zelle wird fuer Senat und Haus verwendet
            zellen = zellen[:4] + zellen[3:]
        if len(zellen) < 8:
            continue
        a = STAATEN[zellen[0]]
        staaten[a] = {
            "pres24": partei(zellen[1]), "gov": partei(zellen[2]),
            "senat": zellen[3], "haus": zellen[4],
            "ussen": [partei(zellen[5]), partei(zellen[6])], "ushaus": zellen[7],
        }
        staaten[a]["senat_p"] = partei(zellen[3])
        staaten[a]["haus_p"] = partei(zellen[4])
    # Plausibilitaet
    if len(staaten) != 50:
        raise ValueError("Wikipedia: %d statt 50 Staaten" % len(staaten))
    reg = {}
    z = {"R": 0, "D": 0, "G": 0}
    for a, s in staaten.items():
        if s["gov"] == s["senat_p"] == s["haus_p"] and s["gov"] in ("R", "D"):
            reg[a] = s["gov"]
        else:
            reg[a] = "G"
        z[reg[a]] += 1
    # Nebraska hat ein parteiloses Parlament, wird von Wikipedia teils als "Nonpartisan/de facto" gefuehrt
    if "NE" in staaten and reg["NE"] == "G" and staaten["NE"]["gov"] == "R":
        reg["NE"] = "R"; z["G"] -= 1; z["R"] += 1
    if not (15 <= z["R"] <= 32 and 10 <= z["D"] <= 26 and z["R"] + z["D"] + z["G"] == 50):
        raise ValueError("Trifecta-Zahlen unplausibel: %s" % z)
    # Kongress
    sen = {"R": 0, "D": 0, "X": 0}
    for s in staaten.values():
        for p in s["ussen"]:
            sen[p] += 1
    haus = {"R": 0, "D": 0, "X": 0}
    for s in staaten.values():
        m = re.match(r"(Republican|Democratic|Democrat|Tied)\s+(\d+)\D+(\d+)", s["ushaus"])
        if m:
            erste, zweite = int(m.group(2)), int(m.group(3))
            if m.group(1) == "Republican":
                haus["R"] += erste; haus["D"] += zweite
            elif m.group(1) == "Tied":
                haus["R"] += erste; haus["D"] += zweite
            else:
                haus["D"] += erste; haus["R"] += zweite
    if sum(sen.values()) != 100 or not (400 <= sum(haus.values()) <= 435):
        raise ValueError("Kongress unplausibel: Senat %s, Haus %s" % (sen, haus))
    return {"staaten": staaten, "reg": reg, "zaehlung": z, "senat": sen, "haus": haus}


# ---------------------------------------------------------------- Fed (federalreserve.gov)
FED = "https://www.federalreserve.gov"
MONATE = {m: i + 1 for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July",
                                         "August", "September", "October", "November", "December"])}


def fed_text(url):
    h = holen(url)
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    t = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)))
    return h, t


def lade_fed():
    jahr = datetime.date.today().year
    # 1. Mitglieder des FOMC
    _, t = fed_text(FED + "/monetarypolicy/fomc.htm")
    a = t.index("Committee Members")
    b = t.index("Alternate Members", a)
    seg = t[a + len("Committee Members"):b]
    teile = re.findall(r"([A-Z][A-Za-z\.\' ]+?) , ([A-Za-z ]+?)(?:, (Chairman|Vice Chair))?(?= [A-Z][A-Za-z\.\']+ (?:[A-Z]\. )?[A-Z][A-Za-z\']+ ,|\s*$)", seg.strip() + " ")
    mitglieder = [{"name": n.strip(), "ort": o.strip(), "rolle": r} for n, o, r in teile]
    rest = t[b + len("Alternate Members"):]
    rest = rest[:rest.index("Rotation")]
    alt = [{"name": n.strip(), "ort": o.strip()} for n, o in re.findall(r"([A-Z][A-Za-z\.\' ]+?) , ([^,]+?)(?= [A-Z][a-z]+ (?:[A-Z]\. )?[A-Z][a-z]+ ,|\s*$)", rest.strip() + " ")]
    board = [m for m in mitglieder if m["ort"] == "Board of Governors"]
    chair = next((m["name"] for m in board if m["rolle"] == "Chairman"), None)
    if len(mitglieder) != 12 or len(board) != 7 or not chair:
        raise ValueError("FOMC-Mitglieder unplausibel: %d Mitglieder, %d Board, Vorsitz %s" % (len(mitglieder), len(board), chair))
    # 2. Sitzungskalender
    kh, kt = fed_text(FED + "/monetarypolicy/fomccalendars.htm")
    a = kt.index("%d FOMC Meetings" % jahr)
    b = kt.index("FOMC Meetings", a + 20)
    blk = kt[a:b]
    sitz = []
    muster = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December) (\d+)-(\d+)(\*?)(.*?)(?=(?:January|February|March|April|May|June|July|August|September|October|November|December) \d+-\d+|\* Meeting|$)")
    for m in muster.finditer(blk):
        mon = MONATE[m.group(1)]
        d1, d2 = int(m.group(2)), int(m.group(3))
        ende = datetime.date(jahr, mon, d2)
        mr = re.search(r"Released (\w+) (\d+), (\d{4})", m.group(5))
        minutes = None
        if mr:
            minutes = datetime.date(int(mr.group(3)), MONATE[mr.group(1)], int(mr.group(2))).isoformat()
        sitz.append({"von": datetime.date(jahr, mon, d1).isoformat(), "bis": ende.isoformat(), "sep": bool(m.group(4)),
                     "minutes": minutes or (ende + datetime.timedelta(days=21)).isoformat(), "minutes_geschaetzt": not minutes,
                     "statement": "monetary%s%02d%02da.htm" % (jahr, mon, d2) in kh})
    if len(sitz) != 8:
        raise ValueError("FOMC-Kalender: %d statt 8 Sitzungen" % len(sitz))
    # 3. Letzte Sitzung mit Mitteilung: Beschluss und Abstimmung
    letzte = [s for s in sitz if s["statement"]][-1]
    datei = "monetary%s%sa.htm" % (letzte["bis"][:4], letzte["bis"][5:7] + letzte["bis"][8:10])
    _, st = fed_text(FED + "/newsevents/pressreleases/" + datei)
    v = re.search(r"by a (\d+)\s*[–-]\s*(\d+) vote", st)
    if not v:
        raise ValueError("Abstimmung in der Mitteilung nicht gefunden")
    beschluss = re.search(r"The Committee decided to ([^.]+)\.", st)
    gegen = re.search(r"Voting against[^:]*: (.+?)\. ", st)
    return {"mitglieder": mitglieder, "vorsitz": chair,
            "sitzungen": sitz,
            "abstimmung": {"datum": letzte["bis"], "ja": int(v.group(1)), "nein": int(v.group(2)),
                           "beschluss": beschluss.group(1) if beschluss else "",
                           "gegen": gegen.group(1)[:200] if gegen else "", "quelle": FED + "/newsevents/pressreleases/" + datei}}


# ---------------------------------------------------------------- EIA (Short-Term Energy Outlook, Tabellen als PDF)
EIA_TAB = "https://www.eia.gov/outlooks/steo/tables/pdf/%stab.pdf"


def eia_tabelle(name):
    import io
    try:
        import pypdf
    except ImportError:
        raise ValueError("Programmteil pypdf fehlt (pip install pypdf)")
    req = urllib.request.Request(EIA_TAB % name, headers={"User-Agent": UA})
    daten = urllib.request.urlopen(req, timeout=60).read()
    return "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(io.BytesIO(daten)).pages)


def eia_zahlen(zeile):
    return [float(x.replace(",", "")) for x in re.findall(r"-?\d[\d,]*\.?\d*", zeile.split("...")[-1] if "..." in zeile else zeile)]


def eia_zeile(text, muster, ab=0):
    """Findet die Zeile (oder die Folgezeile) mit den Jahreswerten 2025/2026/2027 (die letzten drei Zahlen)."""
    zeilen = text.split("\n")
    for i in range(ab, len(zeilen)):
        if re.search(muster, zeilen[i]):
            for j in (i, i + 1):
                z = eia_zahlen(zeilen[j]) if j < len(zeilen) else []
                if len(z) >= 12:
                    return z[-3:], i
            raise ValueError("EIA-Zeile ohne Zahlen: " + muster)
    raise ValueError("EIA-Zeile nicht gefunden: " + muster)


def lade_eia():
    t1, t4, t5, t7 = (eia_tabelle(n) for n in ("1", "4a", "5a", "7a"))
    m = re.search(r"Short-Term Energy Outlook\s*-\s*(\w+) (\d{4})", t1)
    ausgabe = (m.group(1) + " " + m.group(2)) if m else ""
    kopf = re.search(r"(\d{4}) (\d{4}) (\d{4})\s*$", t1.split("\n")[0].strip())
    j0 = int(kopf.group(1)) if kopf else None
    if not j0:
        raise ValueError("EIA: Jahreskopf nicht gefunden")
    w = {}
    w["rohoel_prod"], _ = eia_zeile(t1, r"^Crude Oil Production")
    w["wti"], _ = eia_zeile(t1, r"^Crude Oil West Texas")
    w["henry_hub"], _ = eia_zeile(t1, r"^Natural Gas Henry Hub")
    w["gas_prod"], _ = eia_zeile(t1, r"^Dry Natural Gas Production")
    w["rohoel_netto_import"], _ = eia_zeile(t4, r"^Crude oil net imports")
    w["produkte_netto_import"], _ = eia_zeile(t4, r"^Petroleum product net imports")
    w["erdoel_netto_import"], _ = eia_zeile(t4, r"^Total petroleum and other liquid fuels net imports")
    w["lng_export"], _ = eia_zeile(t5, r"^LNG gross exports")
    w["strom_gesamt"], i = eia_zeile(t7, r"^Total consumption")
    w["strom_haushalte"], _ = eia_zeile(t7, r"^Residential sector", i)
    w["strom_gewerbe"], _ = eia_zeile(t7, r"^Commercial sector", i)
    w["strom_industrie"], _ = eia_zeile(t7, r"^Industrial sector", i)
    w["strom_erzeugung"], _ = eia_zeile(t7, r"^Electricity generation")
    if not (3500 < w["strom_gesamt"][0] < 5500 and 10 < w["rohoel_prod"][0] < 20 and -10 < w["erdoel_netto_import"][0] < 10):
        raise ValueError("EIA-Werte unplausibel: %s" % w["strom_gesamt"])
    return {"ausgabe": ausgabe, "jahre": [j0, j0 + 1, j0 + 2], "werte": w, "quelle": "https://www.eia.gov/outlooks/steo/"}


# ---------------------------------------------------------------- Handel: Federal Register (Zeitstrahl, Sanktionen)
FR_API = "https://www.federalregister.gov/api/v1/documents.json"
FR_FELDER = "&fields[]=title&fields[]=publication_date&fields[]=html_url&fields[]=type&fields[]=document_number&fields[]=agencies"
TYP_DE = {"Presidential Document": "Präsidialdokument", "Notice": "Mitteilung", "Rule": "Regelung",
          "Proposed Rule": "Regelentwurf"}
# Titel, die nichts mit Handelspolitik zu tun haben, werden aussortiert
FR_AUSSCHLUSS = re.compile(r"Foreign-Trade Zone|National .* (Day|Week|Month)|Agency Information Collection|Sugar|Antidumping|"
                           r"Countervailing|Sunset Review|Low-Value|Application for|Scope Ruling|Administrative Review|Initiation of", re.I)
FR_HANDEL = re.compile(r"tariff|duties|duty|section 232|section 301|section 122|section 338|import|trade|reciprocal|"
                       r"agreement|USMCA|China|Canada|Mexico|IEEPA|refund|exclusion|export control", re.I)


def fr_abfrage(bedingungen, seite_groesse=40):
    u = FR_API + "?" + bedingungen + "&order=newest&per_page=%d" % seite_groesse + FR_FELDER
    return json.loads(holen(u)).get("results", [])


def lade_handel():
    seit = "conditions[publication_date][gte]=%d-01-01" % datetime.date.today().year
    quellen = [
        ("Präsidialdokumente (Zölle)", "conditions[type][]=PRESDOCU&conditions[term]=tariffs&" + seit),
        ("Präsidialdokumente (Handel)", "conditions[type][]=PRESDOCU&conditions[term]=trade&" + seit),
        ("USTR", "conditions[agencies][]=trade-representative-office-of-united-states&" + seit),
        ("Handelsministerium (Section 232)", "conditions[term]=%22section+232%22&conditions[agencies][]=commerce-department&" + seit),
        ("Zoll (IEEPA-Erstattungen)", "conditions[term]=IEEPA&conditions[agencies][]=u-s-customs-and-border-protection&" + seit),
    ]
    ereignisse, gesehen = [], set()
    for name, cond in quellen:
        for x in fr_abfrage(cond):
            titel = x["title"].strip()
            if FR_AUSSCHLUSS.search(titel) or not FR_HANDEL.search(titel):
                continue
            schluessel = (x["publication_date"], re.sub(r"\W+", "", titel.lower())[:60])
            if schluessel in gesehen:
                continue
            gesehen.add(schluessel)
            ereignisse.append({"d": x["publication_date"], "titel": titel[:220], "typ": TYP_DE.get(x["type"], x["type"]),
                               "url": x["html_url"], "nr": x["document_number"],
                               "stelle": ", ".join(a.get("name", "") for a in x.get("agencies", [])[:2])[:120]})
    ereignisse.sort(key=lambda e: e["d"], reverse=True)
    if not ereignisse:
        raise ValueError("Federal Register: keine Treffer fuer Handelspolitik")
    # Sanktionen (OFAC), die letzten Meldungen
    sank = []
    for x in fr_abfrage("conditions[agencies][]=foreign-assets-control-office", 12):
        sank.append({"d": x["publication_date"], "titel": x["title"].strip()[:200], "typ": TYP_DE.get(x["type"], x["type"]),
                     "url": x["html_url"], "nr": x["document_number"]})
    return {"zeitstrahl": ereignisse[:45], "sanktionen": sank, "quelle": "https://www.federalregister.gov"}


# ---------------------------------------------------------------- Zolleinnahmen (US-Finanzministerium, Monthly Treasury Statement)
def lade_zoll():
    import ssl
    u = ("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/mts/mts_table_4?filter="
         + urllib.parse.quote("classification_desc:eq:Customs Duties") + "&sort=-record_date&page[size]=48")
    ctx = ssl._create_unverified_context() if os.environ.get("LAENDER_LOKAL_SSL_EGAL") else None
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    j = json.loads(urllib.request.urlopen(req, timeout=60, context=ctx).read().decode("utf-8"))
    zeilen = j.get("data", [])
    punkte = [[z["record_date"], round(float(z["current_month_gross_rcpt_amt"]) / 1e6, 1)] for z in zeilen
              if z.get("current_month_gross_rcpt_amt") not in (None, "", "null")]
    punkte.sort()
    if len(punkte) < 6:
        raise ValueError("Zolleinnahmen: zu wenige Monate")
    fy = [round(float(z["current_fytd_gross_rcpt_amt"]) / 1e6, 1) for z in zeilen[:1]]
    return {"monate": punkte, "fytd": fy[0] if fy else None, "einheit": "Mio. USD", "quelle": "https://fiscaldata.treasury.gov/datasets/monthly-treasury-statement/"}


# ---------------------------------------------------------------- US Census Bureau (Warenhandel nach Land und Produktgruppe)
CENSUS = "https://api.census.gov/data/timeseries/intltrade/"
# Produktgruppen der Lieferketten-Karte: Liste aus (Stufe, Zolltarifnummer, Vorzeichen)
CENSUS_GRUPPEN = {
    "auto": [("HS2", "87", 1)],
    "elektronik": [("HS4", c, 1) for c in ("8471", "8473", "8517", "8541", "8542")],
    "energie": [("HS2", "27", 1)],
    "pharma": [("HS2", "30", 1)],
    "agrar": [("HS2", c, 1) for c in ("02", "08", "10", "12")],
    "rohstoffe": [("HS4", c, 1) for c in ("2805", "2846", "8505", "2611", "2612", "8112")],
    "maschinen": [("HS2", "84", 1), ("HS4", "8471", -1), ("HS4", "8473", -1)],
}


def census_key():
    k = os.environ.get("CENSUS_API_KEY")
    if k and k.strip():
        m = re.search(r"[0-9a-f]{40}", k.strip().lower())
        if not m:
            raise ValueError("CENSUS_API_KEY (Secret) hat kein gueltiges Format (40 Zeichen erwartet)")
        return m.group(0)
    try:
        pfad = os.path.join(HIER, "..", "..", "05_Dashboard", "02_Datenskripte", "zugangsdaten.txt")
        m = re.search(r"CENSUS_API_KEY=([0-9a-fA-F]{40})", open(pfad, encoding="utf-8").read())
        if m:
            return m.group(1).lower()
    except Exception:  # noqa
        pass
    raise ValueError("kein Census-Schluessel hinterlegt (Secret CENSUS_API_KEY fehlt)")


def census_abfrage(key, richtung, stufe, code, zeit, hafen=False):
    """Holt Wert gesamt, per Schiff (VES) und per Flugzeug (AIR), je Land (hafen=False) oder je Hafen (hafen=True).
    Rueckgabe: {Schluessel: (Name, mo, yr, schiff_mo, schiff_yr, luft_mo, luft_yr)}  (Werte in USD)"""
    if richtung == "imp":
        tot, kc, pfad = "GEN_VAL", "I_COMMODITY", "imports/"
    else:
        tot, kc, pfad = "ALL_VAL", "E_COMMODITY", "exports/"
    pfad += "porths" if hafen else "hs"
    sk = "PORT" if hafen else "CTY_CODE"
    sn = "PORT_NAME" if hafen else "CTY_NAME"
    felder = "%s,%s,%s,%s_MO,%s_YR,VES_VAL_MO,VES_VAL_YR,AIR_VAL_MO,AIR_VAL_YR" % (sk, sn, kc, tot, tot)
    u = "%s%s?get=%s&COMM_LVL=%s&%s=%s&time=%s&key=%s" % (CENSUS, pfad, felder, stufe, kc, code, zeit, key)
    letzter = None
    for _ in range(3):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA})
            roh = urllib.request.urlopen(req, timeout=120).read().decode("utf-8")
            if not roh.strip():
                return None
            zeilen = json.loads(roh)
            kopf = zeilen[0]
            ix = [kopf.index(n) for n in (sk, sn, tot + "_MO", tot + "_YR", "VES_VAL_MO", "VES_VAL_YR", "AIR_VAL_MO", "AIR_VAL_YR")]
            out = {}
            for z in zeilen[1:]:
                out[z[ix[0]]] = (z[ix[1]],) + tuple(float(z[i] or 0) for i in ix[2:])
            return out
        except Exception as e:  # noqa
            letzter = str(e).replace(key, "***")
    raise ValueError("Census %s %s %s: %s" % (richtung, stufe, code, letzter))


def census_summiere(cache, codes, ri, key, zeit, hafen):
    """Summiert die Zolltarifnummern einer Produktgruppe (mit Vorzeichen). Rueckgabe (gesamt, {id: [name, 6 Werte]})"""
    summe, gesamt = {}, [0.0] * 6
    for stufe, code, vz in codes:
        k = (ri, stufe, code, hafen)
        if k not in cache:
            cache[k] = census_abfrage(key, ri, stufe, code, zeit, hafen) or {}
        for cc, v in cache[k].items():
            if cc == "-":
                for i in range(6):
                    gesamt[i] += vz * v[1 + i]
            elif hafen or (cc.isdigit() and int(cc) >= 1000):
                s = summe.setdefault(cc, [v[0]] + [0.0] * 6)
                for i in range(6):
                    s[1 + i] += vz * v[1 + i]
    return gesamt, summe


def m(v):
    return round(v / 1e6, 1)


def lade_census():
    key = census_key()
    heute = datetime.date.today()
    zeit = None
    for monate_zurueck in range(1, 6):  # der letzte verfuegbare Monat (Veroeffentlichung etwa 5 Wochen nach Monatsende)
        mm = heute.month - monate_zurueck
        j = heute.year
        while mm < 1:
            mm += 12
            j -= 1
        z = "%d-%02d" % (j, mm)
        if census_abfrage(key, "imp", "HS2", "87", z):
            zeit = z
            break
    if not zeit:
        raise ValueError("Census: kein verfuegbarer Monat gefunden")
    cache, gruppen, haefen, haefen_fehler = {}, {}, {}, None
    for gid, codes in CENSUS_GRUPPEN.items():
        gruppen[gid], haefen[gid] = {}, {}
        for ri in ("imp", "exp"):
            gesamt, summe = census_summiere(cache, codes, ri, key, zeit, False)
            top = sorted(summe.values(), key=lambda s: s[2], reverse=True)[:12]
            gruppen[gid][ri] = {
                "gesamt": {"mo": m(gesamt[0]), "ytd": m(gesamt[1]), "sm": m(gesamt[2]), "sy": m(gesamt[3]), "lm": m(gesamt[4]), "ly": m(gesamt[5])},
                "laender": [{"n": s[0], "mo": m(s[1]), "ytd": m(s[2]), "sm": m(s[3]), "sy": m(s[4]), "lm": m(s[5]), "ly": m(s[6])} for s in top if s[2] > 0]}
    if not gruppen["auto"]["imp"]["laender"] or gruppen["auto"]["imp"]["gesamt"]["ytd"] <= 0:
        raise ValueError("Census-Werte unplausibel")
    # Haefen und Flughaefen (nur Zusatz: faellt er aus, bleiben die Laenderdaten erhalten)
    try:
        for gid, codes in CENSUS_GRUPPEN.items():
            for ri in ("imp", "exp"):
                gesamt, summe = census_summiere(cache, codes, ri, key, zeit, True)
                top = sorted(summe.values(), key=lambda s: s[4], reverse=True)[:12]
                haefen[gid][ri] = {
                    "gesamt": {"sm": m(gesamt[2]), "sy": m(gesamt[3])},
                    "liste": [{"n": s[0], "sm": m(s[3]), "sy": m(s[4]), "ty": m(s[2]), "ly": m(s[6])} for s in top if s[4] > 0]}
        if not haefen["auto"]["imp"]["liste"]:
            raise ValueError("Hafen-Werte unplausibel")
    except Exception as e:  # noqa
        haefen, haefen_fehler = None, str(e).replace(key, "***")[:200]
    out = {"zeit": zeit, "einheit": "Mio. USD", "gruppen": gruppen, "haefen": haefen, "quelle": "https://www.census.gov/foreign-trade/index.html"}
    if haefen_fehler:
        out["haefen_fehler"] = haefen_fehler
    return out


# ---------------------------------------------------------------- Umwelt und Klima (Oberthema 9)
def tabelle_zeilen(html_text, nr, sep=""):
    tabs = re.findall(r"<table.*?</table>", html_text, flags=re.S)
    rows = re.findall(r"<tr.*?</tr>", tabs[nr], flags=re.S)
    return [[html.unescape(re.sub(r"<[^>]+>", sep, c)).replace("\xa0", " ").strip()
             for c in re.findall(r"<t[hd].*?</t[hd]>", r, flags=re.S)] for r in rows]


def zahl_us(t):
    try:
        return float(t.replace(",", ""))
    except Exception:
        return None


MONATE = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6, "July": 7, "August": 8,
          "Sept": 9, "September": 9, "October": 10, "November": 11, "December": 12}


def epm_tabelle(t):
    """Electric Power Monthly: Jahreswerte, Monatswerte und die letzten 12 Monate je Spalte."""
    h = holen("https://www.eia.gov/electricity/monthly/epm_table_grapher.php?t=" + t)
    z = tabelle_zeilen(h, 1)
    kopf = next(r for r in z if r and r[0] == "Period")
    jahre, monate, r12, jahr = {}, {}, None, None
    abschnitt = ""
    for r in z:
        if not r or r[0] == "Period":
            continue
        if len(r) == 1:
            abschnitt = r[0]
            m = re.match(r"Year\s*(\d{4})", r[0])
            jahr = int(m.group(1)) if m else None
            continue
        werte = {kopf[i]: zahl_us(r[i]) for i in range(1, min(len(kopf), len(r)))}
        if abschnitt.startswith("Annual") and re.fullmatch(r"\d{4}", r[0]):
            jahre[int(r[0])] = werte
        elif abschnitt.startswith("Year") and r[0] in MONATE and jahr:
            monate["%d-%02d-01" % (jahr, MONATE[r[0]])] = werte
        elif abschnitt.startswith("Rolling"):
            r12 = (r[0], werte)
    return jahre, monate, r12


def lade_strommix():
    j1, m1, r1 = epm_tabelle("epmt_1_1")
    j2, m2, r2 = epm_tabelle("epmt_1_1_a")

    def teile(a, b):
        """a aus Tabelle 1.1, b aus Tabelle 1.1.A -> Strommix in Tsd. MWh"""
        if not a or not b:
            return None
        v = lambda d, k: d.get(k) or 0.0
        bio = (v(b, "Wood andWood-DerivedFuels") + v(b, "LandfillGas") + v(b, "BiogenicMunicipalSolid Waste")
               + v(b, "Other Waste Biomass") + v(b, "Geothermal"))
        return {"gas": v(a, "NaturalGas"), "kohle": v(a, "Coal"), "atom": v(a, "Nuclear"),
                "wind": v(b, "Wind"), "solar": v(a, "Estimated Total Solar"), "wasser": v(a, "HydroelectricConventional"),
                "bio": bio, "oel": v(a, "PetroleumLiquids") + v(a, "PetroleumCoke"),
                "rest": v(a, "OtherFossilGas") + v(a, "HydroelectricPumpedStorage") + v(a, "Other")}
    jahre = {str(y): teile(j1.get(y), j2.get(y)) for y in sorted(j1) if y in j2}
    monate = {d: teile(m1[d], m2.get(d)) for d in sorted(m1) if d in m2}
    r12 = None
    if r1 and r2 and r1[0] == r2[0]:
        r12 = {"ende": r1[0], "werte": teile(r1[1], r2[1])}
    if not jahre or not monate or not r12 or not all(jahre.values()) or not r12["werte"]:
        raise ValueError("EPM: Tabellen unvollstaendig")
    ges = sum(r12["werte"].values())
    if not (3.5e6 < ges < 5.5e6):
        raise ValueError("EPM: Gesamterzeugung unplausibel: %s" % ges)
    return {"jahre": jahre, "monate": monate, "r12": r12, "letzter_monat": max(monate), "einheit": "Tsd. MWh",
            "quelle": "https://www.eia.gov/electricity/monthly/epm_table_grapher.php?t=epmt_1_1"}


def lade_co2():
    t = holen("https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.csv")
    pts = []
    for zl in t.splitlines():
        if zl.startswith("#") or not zl.strip() or zl.startswith("year"):
            continue
        c = zl.split(",")
        try:
            y, m, avg = int(c[0]), int(c[1]), float(c[3])
        except Exception:
            continue
        if avg > 0 and y >= 2015:
            pts.append(["%d-%02d-01" % (y, m), avg])
    if len(pts) < 60 or not (380 < pts[-1][1] < 500):
        raise ValueError("CO2 unplausibel")
    return {"monat": pts, "quelle": "https://gml.noaa.gov/ccgg/trends/"}


def lade_duerre():
    ende = datetime.date.today()
    u = ("https://usdmdataservices.unl.edu/api/USStatistics/GetDroughtSeverityStatisticsByAreaPercent?aoi=us"
         "&startdate=1/1/2020&enddate=%d/%d/%d&statisticsType=1" % (ende.month, ende.day, ende.year))
    zeilen = holen(u).strip().splitlines()
    kopf = zeilen[0].split(",")
    reihen = {k: [] for k in ("D0", "D1", "D2", "D3")}
    for zl in zeilen[1:]:
        d = dict(zip(kopf, zl.split(",")))
        if d.get("AreaOfInterest", "CONUS") != "CONUS":
            continue
        try:
            dat = "%s-%s-%s" % (d["MapDate"][:4], d["MapDate"][4:6], d["MapDate"][6:8])
            for k in reihen:
                reihen[k].append([dat, float(d[k])])
        except Exception:
            continue
    for k in reihen:
        reihen[k].sort()
    if len(reihen["D1"]) < 50:
        raise ValueError("Duerre-Daten zu kurz")
    return {"reihen": reihen, "quelle": "https://droughtmonitor.unl.edu/"}


def lade_gistemp():
    t = holen("https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv")
    monat, jahr = [], []
    for zl in t.splitlines():
        c = zl.split(",")
        if not c or not re.fullmatch(r"\d{4}", c[0]):
            continue
        y = int(c[0])
        for m in range(1, 13):
            try:
                v = float(c[m])
            except Exception:
                continue
            if y >= 2015:
                monat.append(["%d-%02d-01" % (y, m), v])
        try:
            if y >= 1980:
                jahr.append(["%d-01-01" % y, float(c[13])])
        except Exception:
            pass
    if len(monat) < 60:
        raise ValueError("GISTEMP zu kurz")
    return {"monat": monat, "jahr": jahr, "quelle": "https://data.giss.nasa.gov/gistemp/"}


def lade_laden(alt):
    z = tabelle_zeilen(holen("https://afdc.energy.gov/stations/states"), 0, " ")
    row = next(r for r in z if r and r[0] == "Total")
    m = re.match(r"([\d,]+)\s*\|\s*([\d,]+)\s+([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)", row[4])
    if not m:
        raise ValueError("AFDC: Format geaendert: " + row[4][:60])
    st, ports, l1, l2, dc = (int(x.replace(",", "")) for x in m.groups())
    if not (100000 < ports < 1000000):
        raise ValueError("AFDC: unplausibel")
    heute = datetime.date.today().isoformat()
    hist = list((alt or {}).get("hist") or [])
    if not hist or hist[-1][0][:7] != heute[:7]:
        hist.append([heute, ports, dc])
    else:
        hist[-1] = [heute, ports, dc]
    return {"stand": heute, "standorte": st, "ports": ports, "l2": l2, "dcfast": dc, "hist": hist[-60:],
            "quelle": "https://afdc.energy.gov/stations/states"}


def lade_raffinerien():
    """Raffinerien mit Lage und Kapazitaet (FEMA-Dienst auf Basis der EIA-Raffineriedaten)."""
    u = ("https://gis.fema.gov/arcgis/rest/services/Partner/Petroleum_Refinery_Status/FeatureServer/0/query?"
         "where=1%3D1&outFields=company,corp,site,barrels_per_day,status,st_abr,period_,latitude,longitude&f=json&returnGeometry=false&resultRecordCount=500")
    f = json.loads(holen(u)).get("features", [])
    out = []
    for x in f:
        a = x["attributes"]
        if a.get("latitude") is None or a.get("longitude") is None or not a.get("barrels_per_day"):
            continue
        out.append([round(a["latitude"], 4), round(a["longitude"], 4), int(a["barrels_per_day"]),
                    (a.get("company") or "").title()[:40], (a.get("site") or "").title()[:30], a.get("st_abr") or "",
                    a.get("status") or "", a.get("period_") or ""])
    if len(out) < 50:
        raise ValueError("Raffinerien: zu wenige (%d)" % len(out))
    return {"liste": out, "quelle": "https://www.eia.gov/petroleum/refinerycapacity/ (EIA-820, ueber FEMA-Dienst)"}


def lade_stuerme():
    t = json.loads(holen("https://www.nhc.noaa.gov/CurrentStorms.json"))
    out = []
    for s in t.get("activeStorms", []):
        out.append({"id": s.get("id"), "name": s.get("name"), "klasse": s.get("classification"), "wind_kn": s.get("intensity"),
                    "druck": s.get("pressure"), "lat": s.get("latitudeNumeric"), "lon": s.get("longitudeNumeric"),
                    "richtung": s.get("movementDir"), "tempo": s.get("movementSpeed"), "update": s.get("lastUpdate"),
                    "url": (s.get("publicAdvisory") or {}).get("url")})
    return {"liste": out, "quelle": "https://www.nhc.noaa.gov/"}


FR_ABFRAGEN = [
    ("EPA", "environmental-protection-agency", "greenhouse gas OR emissions OR endangerment OR climate"),
    ("Energieministerium", "energy-department", "liquefied natural gas OR energy efficiency OR clean energy OR electric"),
    ("Finanzministerium", "treasury-department", "energy credit OR clean electricity OR clean vehicle OR clean fuel"),
    ("Innenministerium", "interior-department", "wind OR solar OR oil and gas leasing OR offshore"),
]


def lade_regelungen():
    treffer = {}
    fehler = []
    for name, agentur, term in FR_ABFRAGEN:
        u = ("https://www.federalregister.gov/api/v1/documents.json?conditions%5Bagencies%5D%5B%5D=" + agentur
             + "&conditions%5Bterm%5D=" + urllib.parse.quote_plus(term)
             + "&conditions%5Btype%5D%5B%5D=RULE&conditions%5Btype%5D%5B%5D=PRORULE&order=newest&per_page=8"
             + "&fields%5B%5D=title&fields%5B%5D=publication_date&fields%5B%5D=type&fields%5B%5D=html_url&fields%5B%5D=document_number")
        try:
            for d in json.loads(holen(u)).get("results", []):
                treffer[d["document_number"]] = {"d": d["publication_date"], "t": d["title"], "a": name,
                                                  "art": "Regel" if d["type"] == "Rule" else "Entwurf", "u": d["html_url"]}
        except Exception as e:  # noqa
            fehler.append(name + ": " + str(e)[:60])
    liste = sorted(treffer.values(), key=lambda x: x["d"], reverse=True)[:16]
    if not liste:
        raise ValueError("Federal Register: keine Treffer " + "; ".join(fehler))
    return {"liste": liste, "quelle": "https://www.federalregister.gov/", "fehler": fehler}


def lade_umwelt(alt=None):
    out, fehler = {}, {}
    alt = alt or {}
    for name, fkt in (("strommix", lade_strommix), ("co2", lade_co2), ("duerre", lade_duerre), ("gistemp", lade_gistemp),
                      ("laden", lambda: lade_laden(alt.get("laden"))), ("raffinerien", lade_raffinerien),
                      ("stuerme", lade_stuerme), ("regelungen", lade_regelungen)):
        try:
            out[name] = fkt()
        except Exception as e:  # noqa
            out[name] = alt.get(name)
            fehler[name] = str(e)[:150]
    if fehler:
        out["fehler"] = fehler
    if not any(out.get(k) for k in ("strommix", "co2", "duerre", "gistemp")):
        raise ValueError("Umwelt: keine Quelle erreichbar " + str(fehler))
    return out


def lade_alt():
    try:
        t = open(DATEI, encoding="utf-8").read()
        return json.loads(t[t.index("{"): t.rindex("}") + 1])
    except Exception:
        return {}


def main():
    alt = lade_alt()
    neu = {"meta": {"erstellt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                    "fehler": {}, "stand": dict(alt.get("meta", {}).get("stand", {}))}}
    heute = datetime.date.today().isoformat()
    for name, fkt in (("fred", lade_fred), ("wikipedia", lade_wikipedia), ("fed", lade_fed), ("eia", lade_eia), ("handel", lade_handel), ("zoll", lade_zoll), ("census", lade_census), ("umwelt", None)):
        try:
            neu[name] = fkt() if fkt else lade_umwelt(alt.get("umwelt"))
            neu["meta"]["stand"][name] = heute
            print("OK", name)
        except Exception as e:  # noqa
            neu[name] = alt.get(name)
            neu["meta"]["fehler"][name] = str(e)[:200]
            print("FEHLER", name, str(e)[:200])
    os.makedirs(AUSGABE, exist_ok=True)
    with open(DATEI, "w", encoding="utf-8") as f:
        f.write("window.USA_DATEN=" + json.dumps(neu, separators=(",", ":"), ensure_ascii=False) + ";\n")
    print("geschrieben:", os.path.abspath(DATEI), os.path.getsize(DATEI), "Bytes")
    return 0 if not neu["meta"]["fehler"] else 1


if __name__ == "__main__":
    sys.exit(main())
