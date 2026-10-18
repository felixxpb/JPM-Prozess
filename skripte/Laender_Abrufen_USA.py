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
}


def fred_key():
    k = os.environ.get("FRED_API_KEY")
    if k:
        return k.strip()
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
    for sid, start in FRED.items():
        u = ("https://api.stlouisfed.org/fred/series/observations?series_id=%s&api_key=%s"
             "&file_type=json&observation_start=%s" % (sid, key, start))
        obs = json.loads(holen(u))["observations"]
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
    for name, fkt in (("fred", lade_fred), ("wikipedia", lade_wikipedia)):
        try:
            neu[name] = fkt()
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
