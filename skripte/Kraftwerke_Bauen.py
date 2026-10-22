#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kraftwerke_Bauen.py  -  Kraftwerksverzeichnis fuer die Energiekarte (Projekt JPM Prozess)

Holt die neueste monatliche Generatorliste der EIA (Form EIA-860M, Excel, frei verfuegbar), fasst sie je Kraftwerk zusammen
und schreibt  ../laender/daten/kraftwerke.js  (window.KRAFTWERKE = {...}).

Aufruf:  python -X utf8 Kraftwerke_Bauen.py            (nur Python-Standardbibliothek)
Empfohlen: einmal im Monat oder bei Bedarf. Die Datei ist statisch (aendert sich nur, wenn dieses Skript laeuft).
"""
import datetime, io, json, os, re, sys, urllib.request, zipfile

HIER = os.path.dirname(os.path.abspath(__file__))
AUSGABE = os.environ.get("LAENDER_DATEN") or os.path.join(HIER, "..", "laender", "daten")
UA = "Mozilla/5.0 (TradingBrainLaenderanalyse; fbrinkmann78@gmail.com)"
MONATE = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
MIN_MW = 100.0   # Kraftwerke ab dieser Nettoleistung (Sommer) kommen auf die Karte

KAT = {  # Energiequellen-Code -> Kategorie
    "NG": "gas", "BIT": "kohle", "SUB": "kohle", "LIG": "kohle", "ANT": "kohle", "RC": "kohle", "WC": "kohle",
    "NUC": "atom", "WND": "wind", "SUN": "sonne", "WAT": "wasser", "GEO": "bio",
    "WDS": "bio", "LFG": "bio", "OBG": "bio", "OBS": "bio", "BLQ": "bio", "AB": "bio", "MSW": "bio", "WH": "gas",
    "DFO": "oel", "RFO": "oel", "PC": "oel", "JF": "oel", "KER": "oel", "WO": "oel",
}


def holen_bin(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=180).read()


def neueste_datei():
    heute = datetime.date.today()
    for k in range(0, 8):
        m = heute.month - 1 - k
        j = heute.year + m // 12
        m = m % 12
        name = "%s_generator%d.xlsx" % (MONATE[m], j)
        url = "https://www.eia.gov/electricity/data/eia860m/xls/" + name
        try:
            b = holen_bin(url)
            if b[:2] == b"PK":
                return name, b
        except Exception:
            pass
    raise RuntimeError("Keine EIA-860M-Datei gefunden")


def zeilen(blatt_xml, ss):
    for r in re.findall(r"<row [^>]*>(.*?)</row>", blatt_xml, flags=re.S):
        out = {}
        for m in re.finditer(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)', r, flags=re.S):
            col, attr, inner = m.groups()
            if inner is None:
                continue
            v = re.search(r"<v>(.*?)</v>", inner, flags=re.S)
            if not v:
                continue
            v = v.group(1)
            if 't="s"' in attr:
                v = ss[int(v)]
            out[col] = v
        yield out


def main():
    name, b = neueste_datei()
    z = zipfile.ZipFile(io.BytesIO(b))
    ss = [re.sub(r"<[^>]+>", "", x) for x in re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode("utf8"), flags=re.S)]
    ss = [s.replace("&amp;", "&").replace("&apos;", "'").replace("&quot;", '"') for s in ss]
    blatt = z.read("xl/worksheets/sheet1.xml").decode("utf8")   # Operating
    kopf, plants = None, {}
    for r in zeilen(blatt, ss):
        if kopf is None:
            if r.get("A") == "Entity ID":
                kopf = {v: k for k, v in r.items()}
            continue
        try:
            pid = r[kopf["Plant ID"]]
            mw = float(r[kopf["Net Summer Capacity (MW)"]])
            lat, lon = float(r[kopf["Latitude"]]), float(r[kopf["Longitude"]])
        except Exception:
            continue
        status = r.get(kopf["Status"], "")
        if status.startswith("(OP)") is False and not status.startswith("(SB)"):
            pass
        tech = r.get(kopf["Technology"], "")
        code = r.get(kopf["Energy Source Code"], "")
        if "Batter" in tech:
            kat = "speicher"
        elif "Pumped" in tech:
            kat = "wasser"
        else:
            kat = KAT.get(code)
        if not kat:
            continue
        p = plants.setdefault(pid, {"lat": lat, "lon": lon, "name": r.get(kopf["Plant Name"], ""), "st": r.get(kopf["Plant State"], ""),
                                    "ent": r.get(kopf["Entity Name"], ""), "kat": {}, "jahr": 9999})
        p["kat"][kat] = p["kat"].get(kat, 0.0) + mw
        try:
            p["jahr"] = min(p["jahr"], int(r.get(kopf["Operating Year"], "9999")))
        except Exception:
            pass
    liste = []
    for p in plants.values():
        gesamt = sum(p["kat"].values())
        if gesamt < MIN_MW:
            continue
        kat = max(p["kat"], key=p["kat"].get)
        liste.append([round(p["lat"], 4), round(p["lon"], 4), kat, round(gesamt, 1), p["name"][:40], p["st"], p["ent"][:36]])
    liste.sort(key=lambda x: -x[3])
    if len(liste) < 500:
        raise RuntimeError("Zu wenige Kraftwerke: %d" % len(liste))
    summen = {}
    for x in liste:
        summen[x[2]] = summen.get(x[2], 0) + x[3]
    os.makedirs(AUSGABE, exist_ok=True)
    pfad = os.path.join(AUSGABE, "kraftwerke.js")
    with open(pfad, "w", encoding="utf-8") as f:
        f.write("window.KRAFTWERKE=" + json.dumps({"stand": name, "ab_mw": MIN_MW, "anzahl": len(liste), "mw_je_kat": {k: round(v) for k, v in summen.items()},
                                                    "quelle": "https://www.eia.gov/electricity/data/eia860m/", "liste": liste},
                                                   separators=(",", ":"), ensure_ascii=False) + ";\n")
    print("OK", name, len(liste), "Kraftwerke ab", MIN_MW, "MW ->", pfad, os.path.getsize(pfad), "Bytes")
    print({k: round(v) for k, v in sorted(summen.items(), key=lambda x: -x[1])})


if __name__ == "__main__":
    sys.exit(main())
