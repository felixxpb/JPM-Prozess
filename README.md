---
titel: JPM Prozess (neue Website)
typ: projekt-readme
angelegt: 2026-10-18
status: lokal fertig, GitHub-Einrichtung durch Felix offen
---

# 11_JPM_Prozess: die neue Website

Eigene Website, unabhängig vom alten Makro-Dashboard (`05_Dashboard`, Repository `Makro-Dashboard`), das unverändert weiterläuft. Dieser Ordner ist **eins zu eins der Inhalt des neuen GitHub-Repositorys** `JPM-Prozess`.

**Zwei Bereiche auf der Startseite (Entscheidung Felix, 2026-10-18):**
1. **Länderanalyse:** Klick öffnet die Länderkacheln. USA aktiv (Oberthema 1 und 2), alle anderen Länder "folgt". Quellen und Konzept: [[10_Laenderanalyse/README]].
2. **JPM Makro-Prozess:** noch Platzhalter ("folgt"): Makro-Themen, Bewertung und Positionierung, Signale, Prozess-Werkzeuge. Wird gemeinsam neu aufgebaut (Vorlage: [[05_Dashboard/03_Doku/Dashboard_Themenbereiche_JPM_Prozess]]).

## Dateien

| Datei/Ordner | Inhalt |
|---|---|
| `index.html` | Startseite mit den zwei Bereichen |
| `laender/` | Länderübersicht, `usa-politik.html`, `usa-finanzsystem.html`, `daten/usa.js` (wird vom Skript geschrieben) |
| `skripte/Laender_Abrufen_USA.py` | Datenabruf (FRED, Wikipedia), nur Python-Standardbibliothek |
| `.github/workflows/daten-aktualisieren.yml` | Automatischer Abruf zweimal täglich (GitHub Actions) |
| `stil.css`, `einstellungen.js`, `hintergrund.js`, `bilder/` | Design, Einstellungsmenü und Hintergründe (Kopie aus dem Dashboard) |

**Lokal testen:** `index.html` per Doppelklick im Browser öffnen. **Daten lokal aktualisieren:** `python -X utf8 skripte/Laender_Abrufen_USA.py` (liest den FRED-Schlüssel aus `05_Dashboard/02_Datenskripte/zugangsdaten.txt`, die Datei bleibt außerhalb des Repositorys).

---

# Anleitung: GitHub-Repository und Website einrichten (einmalig)

## Teil 1: Repository erstellen
1. Auf https://github.com einloggen (Konto `felixxpb`).
2. Oben rechts auf **+** klicken, dann **New repository**.
3. **Repository name:** `JPM-Prozess`. **Public** auswählen (nötig für kostenloses GitHub Pages). **Keine** Häkchen bei "Add a README", ".gitignore" oder "license" setzen. Auf **Create repository** klicken.

## Teil 2: Dateien hochladen
1. Auf der neuen, leeren Repository-Seite auf den Link **uploading an existing file** klicken (alternativ: **Add file → Upload files**).
2. Im Explorer den Ordner `11_JPM_Prozess` öffnen. **Markiere alles darin** (Strg+A) und ziehe es in das Browserfenster. Es müssen darin liegen: `index.html`, `stil.css`, `einstellungen.js`, `hintergrund.js`, die Ordner `bilder`, `laender`, `skripte` und der Ordner `.github`. (`README.md` kann mit hoch, ist aber nicht nötig.)
3. **Achtung `.github`:** Der Ordner ist unter Windows manchmal versteckt. Falls er nicht angezeigt wird: im Explorer oben **Ansicht → Anzeigen → Ausgeblendete Elemente** einschalten. Ohne diesen Ordner gibt es keine automatische Aktualisierung (siehe Teil 5).
4. Warten, bis alle Dateien in der Liste stehen (sind viele, das dauert etwas). Unten auf **Commit changes** klicken.

## Teil 3: Website einschalten (GitHub Pages)
1. Im Repository oben auf **Settings** (Zahnrad) klicken.
2. Links auf **Pages**.
3. Bei **Source** "Deploy from a branch" wählen. Bei **Branch** `main` und Ordner `/ (root)` wählen, auf **Save** klicken.
4. 1 bis 2 Minuten warten und die Seite neu laden. Oben erscheint die Adresse: **https://felixxpb.github.io/JPM-Prozess/**

## Teil 4: FRED-Schlüssel hinterlegen (damit der Abruf läuft)
1. **Settings → Secrets and variables → Actions → New repository secret.**
2. **Name:** `FRED_API_KEY` (genau so). **Secret:** dein FRED-Schlüssel (steht in `05_Dashboard/02_Datenskripte/zugangsdaten.txt`, nach `FRED_API_KEY=`). **Add secret.**

## Teil 5: Automatik einmal starten und prüfen
1. Oben auf **Actions** klicken. Falls GitHub fragt, ob Workflows aktiviert werden sollen: bestätigen.
2. Links **Daten aktualisieren**, rechts **Run workflow**, grüner Knopf **Run workflow**.
3. Nach 1 bis 2 Minuten sollte der Lauf einen grünen Haken haben. Ist der Schritt "Laenderanalyse USA" rot, den Fehlertext an Claude schicken. Die Seite bleibt dann auf dem letzten guten Stand.
4. Die Website öffnen (Strg+F5 für frisches Laden). In der Länderanalyse unter USA steht unten "Letzter Datenabruf USA" mit neuem Datum.

## Spätere Änderungen hochladen
Im Repository **Add file → Upload files** und nur die geänderten Dateien hochladen. **Den Ordner `laender/daten` nicht hochladen** (die Automatik hält ihn aktuell). Die Datei `zugangsdaten.txt` gehört nie ins Repository.
