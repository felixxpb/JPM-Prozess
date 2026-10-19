#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weltkarte_Bauen.py  -  erzeugt laender/welt-karte.js (Weltkarte als SVG-Pfade)

Quelle: world-atlas (Natural Earth, gemeinfrei), countries-110m.json
Projektion: Natural Earth (Savric), ohne Antarktis.
Das Skript muss nur einmal laufen. Die erzeugte Datei liegt im Repository (laender/welt-karte.js)
und aendert sich nicht von selbst.
Aufruf:  python -X utf8 Weltkarte_Bauen.py
"""
import json, math, os, urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
ZIEL = os.path.join(HIER, "..", "laender", "welt-karte.js")
URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json"


def projiziere(lon, lat):
    lam, phi = math.radians(lon), math.radians(lat)
    p2, p4 = phi * phi, phi ** 4
    x = lam * (0.8707 - 0.131979 * p2 + p4 * (-0.013791 + p4 * (0.003971 * p2 - 0.001529 * p4)))
    y = phi * (1.007226 + p2 * (0.015085 + p4 * (-0.044475 + 0.028874 * p2 - 0.005916 * p4)))
    return x, -y


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "TradingBrainLaenderanalyse/1.0"})
    topo = json.loads(urllib.request.urlopen(req, timeout=60).read())
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    bogen = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        bogen.append(pts)

    def ring(indices):
        pts = []
        for i in indices:
            a = bogen[i] if i >= 0 else bogen[~i][::-1]
            pts.extend(a if not pts else a[1:])
        # Laengen entwickeln: Ringe ueber die Datumsgrenze (Russland, USA/Alaska, Fidschi) bleiben zusammenhaengend
        out = [pts[0]]
        for lon, lat in pts[1:]:
            vor = out[-1][0]
            while lon - vor > 180:
                lon -= 360
            while lon - vor < -180:
                lon += 360
            out.append((lon, lat))
        return out

    geoms = topo["objects"]["countries"]["geometries"]
    # Grenzen der Projektion bestimmen (ohne Antarktis)
    alle = []
    for g in geoms:
        if g.get("id") == "010":
            continue
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        for poly in polys:
            for r in poly:
                alle.extend(projiziere(*p) for p in ring(r))
    lats = [p[1] for g in geoms if g.get("id") != "010" for poly in (g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]) for r in poly for p in ring(r)]
    minx = projiziere(-180, 0)[0]; maxx = projiziere(180, 0)[0]
    miny = projiziere(0, max(lats))[1]; maxy = projiziere(0, min(lats))[1]
    skal = 1000.0 / (maxx - minx)
    hoehe = (maxy - miny) * skal

    def abb(lon, lat):
        x, y = projiziere(lon, lat)
        return round((x - minx) * skal, 1), round((y - miny) * skal, 1)

    laender, punkte = [], {}
    for g in geoms:
        iso = g.get("id")
        if iso == "010":
            continue
        name = (g.get("properties") or {}).get("name", "")
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        d = []
        groesster = (0, None)
        for poly in polys:
            for k, r in enumerate(poly):
                rr = ring(r)
                kopien = [0]
                if min(p[0] for p in rr) < -180:
                    kopien.append(360)
                if max(p[0] for p in rr) > 180:
                    kopien.append(-360)
                pts = [abb(*p) for p in rr]
                if len(pts) < 3:
                    continue
                for off in kopien:
                    pp = pts if off == 0 else [abb(p[0] + off, p[1]) for p in rr]
                    d.append("M" + "L".join("%s,%s" % q for q in pp) + "Z")
                if k == 0:
                    a = abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))) / 2
                    if a > groesster[0]:
                        cx = sum(p[0] for p in pts) / len(pts)
                        cy = sum(p[1] for p in pts) / len(pts)
                        groesster = (a, [round(cx, 1), round(cy, 1)])
        if not d:
            continue
        laender.append({"id": iso, "n": name, "d": "".join(d)})
        if groesster[1]:
            punkte[iso] = groesster[1]
    # USA: Punkt in der Mitte der Staaten, nicht der Schwerpunkt mit Alaska
    punkte["840"] = list(abb(-98.0, 39.0))
    out = {"b": 1000, "h": round(hoehe, 1), "laender": laender, "punkte": punkte}
    with open(ZIEL, "w", encoding="utf-8") as f:
        f.write("window.WELT=" + json.dumps(out, separators=(",", ":"), ensure_ascii=False) + ";\n")
    print("geschrieben:", os.path.abspath(ZIEL), os.path.getsize(ZIEL), "Bytes,", len(laender), "Laender, Hoehe", round(hoehe, 1))


if __name__ == "__main__":
    main()
