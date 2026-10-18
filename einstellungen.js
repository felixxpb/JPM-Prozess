/* ===========================================================================
   einstellungen.js - Einstellungs-Menue fuer das Makro-Dashboard
   ---------------------------------------------------------------------------
   Laeuft auf ALLEN Seiten. Baut den Zahnrad-Knopf in die Kopfzeile und
   oeffnet ein Menue mit zwei Abschnitten:

     Darstellung  - Hell/Dunkel
     Hintergrund  - Vorlage waehlen und je Vorlage einzeln einstellen

   Bewusste Entscheidungen (mit Felix am 2026-09-29 abgestimmt):
   - Der bestehende Hell/Dunkel-Knopf wird NICHT entfernt, sondern nur
     versteckt und aus dem Menue heraus programmatisch geklickt. So bleibt
     die vorhandene Thema-Logik in index.html, tracking.html und motor.js
     unveraendert gueltig (motor.js zeichnet z. B. offene Detail-Charts neu).
   - Die Einstellungen liegen in localStorage, also PRO GERAET. PC und Handy
     haben getrennte Einstellungen, weil es ohne kostenpflichtigen Server
     keine Synchronisation gibt.
   - Hintergrundbild laeuft seit 2026-10-17 auf ALLEN Seiten (hintergrund.js).
   - Auf schmalen Bildschirmen ist der Hintergrund beim ersten Besuch AUS
     (Akku), laesst sich aber jederzeit einschalten.
   =========================================================================== */

(function () {
  "use strict";

  var SPEICHER = "dashboard-hintergrund";

  /* --- Vorlagen ---------------------------------------------------------
     Seit 2026-10-17 vier feste Hintergrundbilder (Felix). Keine Animation,
     keine Interaktion. Je Bild eigene Reglerwerte (Standard); "bild" ist der
     Pfad relativ zur Seite. */
  var VORLAGEN = [
    { id: "wallstreet", name: "Wall Street", bild: "bilder/hg-wallstreet.jpg",
      beschreibung: "Straßenschlucht mit Börsengebäude in New York.", fertig: true,
      standard: { abdunklung: 60, deckkraft: 100, kacheln: "durchscheinend" } },
    { id: "boerse-rot", name: "Kurstafel rot", bild: "bilder/hg-boerse-rot.webp",
      beschreibung: "Rote Anzeigetafel mit Kursverläufen.", fertig: true,
      standard: { abdunklung: 55, deckkraft: 100, kacheln: "durchscheinend" } },
    { id: "hologramm", name: "Hologramm", bild: "bilder/hg-hologramm.jpg",
      beschreibung: "Blaue Diagramme und Tabellen über einer Hand.", fertig: true,
      standard: { abdunklung: 55, deckkraft: 100, kacheln: "durchscheinend" } },
    { id: "kerzen", name: "Kerzenchart", bild: "bilder/hg-kerzen.jpg",
      beschreibung: "Grüne Kerzen mit Raster und roter Linie.", fertig: true,
      standard: { abdunklung: 50, deckkraft: 100, kacheln: "durchscheinend" } }
  ];

  /* Generischer Rueckfall, falls eine Vorlage einmal keinen eigenen
     "standard" mitbringt. */
  var STANDARD = { abdunklung: 60, deckkraft: 100, kacheln: "durchscheinend" };

  function kopie(o) {
    var n = {}, k;
    for (k in o) { if (Object.prototype.hasOwnProperty.call(o, k)) { n[k] = o[k]; } }
    return n;
  }

  function schmal() {
    return window.matchMedia && window.matchMedia("(max-width: 760px)").matches;
  }

  /* --- Speicher --------------------------------------------------------- */

  var zustand = null;

  function laden() {
    if (zustand) { return zustand; }
    var roh = null;
    try { roh = localStorage.getItem(SPEICHER); } catch (e) { }
    var g = null;
    if (roh) { try { g = JSON.parse(roh); } catch (e) { g = null; } }

    zustand = {
      /* Erster Besuch: auf dem Handy bewusst aus, am Rechner an */
      an: g && typeof g.an === "boolean" ? g.an : !schmal(),
      aktiv: g && g.aktiv ? g.aktiv : VORLAGEN[0].id,
      proVorlage: (g && g.proVorlage) || {},
      /* Eigene Graphen-Farben, unabhaengig von Hintergrund-Vorlage und Thema.
         Schluessel serie1/serie2 wie die CSS-Variablen --serie-1/--serie-2,
         die motor.js fuer Haupt- und Vergleichslinie in allen Detail-Charts
         benutzt. Fehlt ein Schluessel, gilt die Farbe der aktuellen Vorlage
         (kein Override). */
      farben: (g && g.farben) || {}
    };

    /* Fehlende oder unvollstaendige Vorlagen-Einstellungen auffuellen -
       jede Vorlage hat ihren EIGENEN Standard (siehe VORLAGEN oben), nicht
       einen gemeinsamen. */
    VORLAGEN.forEach(function (v) {
      var e = zustand.proVorlage[v.id] || {};
      var voll = kopie(v.standard || STANDARD), k;
      for (k in voll) {
        if (Object.prototype.hasOwnProperty.call(e, k)) { voll[k] = e[k]; }
      }
      zustand.proVorlage[v.id] = voll;
    });

    /* Falls eine noch nicht gebaute Vorlage gespeichert war */
    if (!vorlageVon(zustand.aktiv) || !vorlageVon(zustand.aktiv).fertig) {
      zustand.aktiv = VORLAGEN[0].id;
    }
    return zustand;
  }

  function sichern() {
    try { localStorage.setItem(SPEICHER, JSON.stringify(zustand)); } catch (e) { }
    melden();
  }

  function vorlageVon(id) {
    for (var i = 0; i < VORLAGEN.length; i++) { if (VORLAGEN[i].id === id) { return VORLAGEN[i]; } }
    return null;
  }

  function aktuelleWerte() {
    var z = laden();
    return z.proVorlage[z.aktiv];
  }

  function hexRgba(hex, a) {
    var h = (hex || "#000000").replace("#", "");
    if (h.length === 3) { h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2]; }
    var n = parseInt(h, 16) || 0;
    return "rgba(" + ((n >> 16) & 255) + "," + ((n >> 8) & 255) + "," + (n & 255) + "," + a + ")";
  }

  /* --- Bekanntgabe an hintergrund.js ------------------------------------ */

  function melden() {
    var z = laden();
    var w = aktuelleWerte();

    /* Abdunklung und Kachelstil sind reines CSS und wirken sofort */
    document.documentElement.style.setProperty("--hg-abdunklung", (w.abdunklung / 100).toFixed(2));
    document.documentElement.setAttribute("data-kachelstil", w.kacheln);
    document.documentElement.setAttribute("data-hintergrund", z.an ? z.aktiv : "aus");

    /* Eigene Graphenfarben: als Inline-Style gesetzt, das schlaegt IMMER die
       Palette-Bloecke in stil.css (frueher je Vorlage, seit 2026-10-17 entfernt),
       egal welche Vorlage gerade laeuft. Ohne eigene Wahl (kein Eintrag in
       z.farben) wird die Eigenschaft entfernt, dann greift wieder die Farbe
       der aktuellen Vorlage. */
    ["serie1", "serie2"].forEach(function (schluessel) {
      var cssVar = schluessel === "serie1" ? "--serie-1" : "--serie-2";
      if (z.farben[schluessel]) {
        document.documentElement.style.setProperty(cssVar, z.farben[schluessel]);
      } else {
        document.documentElement.style.removeProperty(cssVar);
      }
    });

    /* Kachel- und Textfarbe (je Farbmodus getrennt gemerkt). Inline-Style
       schlaegt stil.css; ohne eigene Wahl wird er entfernt. */
    var th = themaJetzt();
    var kc = z.farben["kachel-" + th], tc = z.farben["text-" + th];
    var root = document.documentElement.style;
    if (kc) {
      root.setProperty("--flaeche", kc);
      root.setProperty("--flaeche-glas", hexRgba(kc, 0.72));
    } else {
      root.removeProperty("--flaeche");
      root.removeProperty("--flaeche-glas");
    }
    if (tc) {
      root.setProperty("--text-primaer", tc);
      root.setProperty("--text-sekundaer", hexRgba(tc, 0.78));
      root.setProperty("--text-stumm", hexRgba(tc, 0.55));
    } else {
      root.removeProperty("--text-primaer");
      root.removeProperty("--text-sekundaer");
      root.removeProperty("--text-stumm");
    }

    document.dispatchEvent(new CustomEvent("hintergrund-geaendert", {
      detail: { an: z.an, vorlage: z.aktiv, werte: kopie(w) }
    }));
  }

  /* Nach aussen, damit hintergrund.js den Stand auch aktiv abfragen kann */
  window.DASHBOARD_EINSTELLUNGEN = {
    lesen: function () {
      var z = laden();
      return { an: z.an, vorlage: z.aktiv, werte: kopie(aktuelleWerte()) };
    },
    vorlagen: VORLAGEN
  };

  /* --- Thema ------------------------------------------------------------ */

  function altSchalter() { return document.getElementById("themaSchalter"); }

  function themaJetzt() {
    return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
  }

  function themaSetzen(neu) {
    if (themaJetzt() === neu) { return; }
    var s = altSchalter();
    if (s) {
      /* Den bestehenden Knopf klicken, damit die vorhandene Logik
         (Speichern, Charts neu zeichnen) unveraendert greift. */
      s.click();
    } else {
      document.documentElement.setAttribute("data-theme", neu);
      try { localStorage.setItem("dashboard-thema", neu); } catch (e) { }
    }
    melden();
  }

  /* --- Menue bauen ------------------------------------------------------ */

  var dialog = null, hintergrundAbschnitt = null, flaechenAbschnitt = null;

  function el(tag, klasse, text) {
    var e = document.createElement(tag);
    if (klasse) { e.className = klasse; }
    if (text !== undefined) { e.textContent = text; }
    return e;
  }

  function baueRegler(id, beschriftung, min, max, schritt, wert, formatieren, beiAenderung) {
    var zeile = el("div", "ein-regler");
    var kopf = el("div", "ein-regler-kopf");
    kopf.appendChild(el("span", null, beschriftung));
    var anzeige = el("span", "ein-regler-wert", formatieren(wert));
    kopf.appendChild(anzeige);

    var r = document.createElement("input");
    r.type = "range";
    r.id = id;
    r.min = min; r.max = max; r.step = schritt; r.value = wert;
    r.setAttribute("aria-label", beschriftung);
    r.addEventListener("input", function () {
      var v = parseInt(r.value, 10);
      anzeige.textContent = formatieren(v);
      beiAenderung(v);
    });

    zeile.appendChild(kopf);
    zeile.appendChild(r);
    return zeile;
  }

  function baueWahl(beschriftung, optionen, istAktiv, beiWahl) {
    var zeile = el("div", "ein-wahl");
    zeile.appendChild(el("span", "ein-wahl-titel", beschriftung));
    var gruppe = el("div", "ein-wahl-gruppe");
    gruppe.setAttribute("role", "group");
    gruppe.setAttribute("aria-label", beschriftung);
    optionen.forEach(function (o) {
      var b = el("button", "ein-wahl-knopf", o.text);
      b.type = "button";
      b.setAttribute("aria-pressed", istAktiv(o.wert) ? "true" : "false");
      b.addEventListener("click", function () {
        beiWahl(o.wert);
        Array.prototype.forEach.call(gruppe.children, function (k, i) {
          k.setAttribute("aria-pressed", istAktiv(optionen[i].wert) ? "true" : "false");
        });
      });
      gruppe.appendChild(b);
    });
    zeile.appendChild(gruppe);
    return zeile;
  }

  /* --- Graphenfarben ------------------------------------------------------
     Eigener Menue-Abschnitt, unabhaengig von Hell/Dunkel und Hintergrund-
     Vorlage: --serie-1 (Hauptlinie) und --serie-2 (Vergleichslinie, z. B.
     YoY-Linie) sind dieselben CSS-Variablen, die motor.js in allen
     Detail-Charts fuer die Linienfarbe benutzt (siehe motor.js, Suche nach
     "var(--serie-1)"). Kein Regler zerstoert die Werte der Vorlagen - die
     Wahl hier ist ein zusaetzlicher Override, der "Zuruecksetzen"-Knopf
     entfernt ihn wieder und die Vorlagen-Farbe kommt zurueck. */

  function rgbZuHex(rgb) {
    var z = (rgb || "").match(/\d+/g);
    if (!z || z.length < 3) { return "#2a78d6"; }
    function hh(n) {
      n = Math.max(0, Math.min(255, parseInt(n, 10) || 0));
      var s = n.toString(16);
      return s.length === 1 ? "0" + s : s;
    }
    return "#" + hh(z[0]) + hh(z[1]) + hh(z[2]);
  }

  function farbeAufloesen(cssVar) {
    /* --serie-1/--serie-2 stehen in stil.css als Hex-Werte, koennten aber
       grundsaetzlich jedes gueltige CSS-Farbformat sein. getPropertyValue()
       auf einer eigenen Eigenschaft liefert den Rohtext (z. B. "#3987e5"),
       kein normalisiertes "rgb(...)" - deshalb ueber eine Wegwerf-Element
       aufloesen, dessen berechneter "color"-Wert der Browser IMMER als
       rgb(...) liefert, egal welches Format urspruenglich benutzt wurde. */
    var sonde = document.createElement("span");
    sonde.style.display = "none";
    sonde.style.color = "var(" + cssVar + ")";
    document.body.appendChild(sonde);
    var normalisiert = getComputedStyle(sonde).color;
    document.body.removeChild(sonde);
    return rgbZuHex(normalisiert);
  }

  function schluesselVon(schluessel) {
    return typeof schluessel === "function" ? schluessel() : schluessel;
  }

  function anzeigeFarbe(schluessel, cssVar) {
    var z = laden();
    var k = schluesselVon(schluessel);
    if (z.farben[k]) { return z.farben[k]; }
    return farbeAufloesen(cssVar);
  }

  function baueFarbregler(id, beschriftung, schluessel, cssVar) {
    var z = laden();
    var zeile = el("div", "ein-regler ein-farbregler");
    var kopf = el("div", "ein-regler-kopf");
    kopf.appendChild(el("span", null, beschriftung));

    var zuruecksetzen = el("button", "ein-farbe-reset", "Zurücksetzen");
    zuruecksetzen.type = "button";
    kopf.appendChild(zuruecksetzen);
    zeile.appendChild(kopf);

    var eingabe = document.createElement("input");
    eingabe.type = "color";
    eingabe.id = id;
    eingabe.setAttribute("aria-label", beschriftung + " – eigene Farbe wählen");
    eingabe.value = anzeigeFarbe(schluessel, cssVar);
    eingabe.addEventListener("input", function () {
      z.farben[schluesselVon(schluessel)] = eingabe.value;
      sichern();
    });
    zeile.appendChild(eingabe);

    zuruecksetzen.addEventListener("click", function () {
      delete z.farben[schluesselVon(schluessel)];
      sichern();
      eingabe.value = anzeigeFarbe(schluessel, cssVar);
    });

    return zeile;
  }

  /* Kachel- und Textfarbe: je Farbmodus (hell/dunkel) getrennt gespeichert,
     weil eine Farbe fuer beide Modi nie passt. */
  function baueFlaechenAbschnitt() {
    var behaelter = el("div");
    behaelter.appendChild(el("p", "ein-hinweis",
      "Farbe der Kacheln und Textfarbe, getrennt für Hell und Dunkel (gilt für den gerade " +
      "gewählten Modus). Wirkt sofort auf allen Seiten und wird pro Gerät gespeichert."));
    behaelter.appendChild(baueFarbregler("einFarbeKachel", "Kachelfarbe",
      function () { return "kachel-" + themaJetzt(); }, "--flaeche"));
    behaelter.appendChild(baueFarbregler("einFarbeText", "Textfarbe",
      function () { return "text-" + themaJetzt(); }, "--text-primaer"));
    return behaelter;
  }

  function baueGraphenAbschnitt() {
    var behaelter = el("div");
    behaelter.appendChild(el("p", "ein-hinweis",
      "Ändert die Linienfarben in allen Detail-Charts, unabhängig vom " +
      "gewählten Hintergrund. Wirkt sofort und wird pro Gerät gespeichert."));
    behaelter.appendChild(baueFarbregler("einFarbeHaupt", "Hauptlinie", "serie1", "--serie-1"));
    behaelter.appendChild(baueFarbregler("einFarbeZweit", "Vergleichslinie", "serie2", "--serie-2"));
    return behaelter;
  }

  function baueHintergrundAbschnitt() {
    var z = laden();
    var behaelter = el("div");

    /* Ein/Aus */
    behaelter.appendChild(baueWahl("Hintergrund", [
      { text: "An", wert: true },
      { text: "Aus", wert: false }
    ], function (w) { return z.an === w; }, function (w) {
      z.an = w;
      sichern();
      zeichneEinstellungenNeu();
    }));

    var hinweis = el("p", "ein-hinweis",
      "Der Hintergrund erscheint auf allen Seiten, aber nur im Dunkelmodus. " +
      "Auf dem Handy ist er zunächst aus.");
    behaelter.appendChild(hinweis);

    if (!z.an) { return behaelter; }

    /* Vorlagen-Auswahl */
    var titel = el("div", "ein-untertitel", "Hintergrund ändern");
    behaelter.appendChild(titel);

    var liste = el("div", "ein-vorlagen");
    VORLAGEN.forEach(function (v) {
      var k = el("button", "ein-vorlage");
      k.type = "button";
      k.disabled = !v.fertig;
      k.setAttribute("aria-pressed", z.aktiv === v.id ? "true" : "false");

      var vorschau = el("span", "ein-vorlage-bild");
      vorschau.setAttribute("data-vorlage", v.id);
      vorschau.style.backgroundImage = 'url("' + v.bild + '")';
      vorschau.setAttribute("aria-hidden", "true");
      k.appendChild(vorschau);

      var name = el("span", "ein-vorlage-name", v.name);
      k.appendChild(name);
      k.appendChild(el("span", "ein-vorlage-text", v.fertig ? v.beschreibung : "Konzept noch offen"));

      if (v.fertig) {
        k.addEventListener("click", function () {
          z.aktiv = v.id;
          sichern();
          zeichneEinstellungenNeu();
        });
      }
      liste.appendChild(k);
    });
    behaelter.appendChild(liste);

    /* Einstellungen der gewaehlten Vorlage */
    var w = aktuelleWerte();
    var name = vorlageVon(z.aktiv).name;
    behaelter.appendChild(el("div", "ein-untertitel", "Einstellungen für „" + name + "“"));

    behaelter.appendChild(baueRegler("einAbdunklung", "Abdunklung", 0, 92, 1, w.abdunklung,
      function (v) { return v + " %"; },
      function (v) { w.abdunklung = v; sichern(); }));

    behaelter.appendChild(baueRegler("einDeckkraft", "Deckkraft Hintergrund", 10, 100, 5, w.deckkraft,
      function (v) { return v + " %"; },
      function (v) { w.deckkraft = v; sichern(); }));

    behaelter.appendChild(baueWahl("Kacheln", [
      { text: "Durchscheinend", wert: "durchscheinend" },
      { text: "Massiv", wert: "massiv" }
    ], function (v) { return w.kacheln === v; }, function (v) { w.kacheln = v; sichern(); }));

    var zurueck = el("button", "ein-zuruecksetzen", "Auf Standard zurücksetzen");
    zurueck.type = "button";
    zurueck.addEventListener("click", function () {
      z.proVorlage[z.aktiv] = kopie(vorlageVon(z.aktiv).standard || STANDARD);
      sichern();
      zeichneEinstellungenNeu();
    });
    behaelter.appendChild(zurueck);

    return behaelter;
  }

  function zeichneEinstellungenNeu() {
    if (!hintergrundAbschnitt) { return; }
    if (flaechenAbschnitt) {
      flaechenAbschnitt.innerHTML = "";
      flaechenAbschnitt.appendChild(baueFlaechenAbschnitt());
    }
    hintergrundAbschnitt.innerHTML = "";
    hintergrundAbschnitt.appendChild(baueHintergrundAbschnitt());
  }

  function baueDialog() {
    if (dialog) { return dialog; }

    var huelle = el("div", "ein-huelle");
    huelle.id = "einstellungenHuelle";
    huelle.hidden = true;

    var kasten = el("div", "ein-kasten");
    kasten.setAttribute("role", "dialog");
    kasten.setAttribute("aria-modal", "true");
    kasten.setAttribute("aria-label", "Einstellungen");

    var kopf = el("div", "ein-kopf");
    kopf.appendChild(el("h2", null, "Einstellungen"));
    var zu = el("button", "ein-schliessen", "✕");
    zu.type = "button";
    zu.setAttribute("aria-label", "Einstellungen schließen");
    zu.addEventListener("click", schliessen);
    kopf.appendChild(zu);
    kasten.appendChild(kopf);

    var koerper = el("div", "ein-koerper");

    /* Abschnitt Darstellung */
    koerper.appendChild(el("div", "ein-titel", "Darstellung"));
    koerper.appendChild(baueWahl("Farbmodus", [
      { text: "Hell", wert: "light" },
      { text: "Dunkel", wert: "dark" }
    ], function (v) { return themaJetzt() === v; }, function (v) {
      themaSetzen(v);
      zeichneEinstellungenNeu();
    }));

    /* Abschnitt Graphenfarben */
    koerper.appendChild(el("div", "ein-titel", "Graphenfarben"));
    koerper.appendChild(baueGraphenAbschnitt());

    /* Abschnitt Kachel- und Textfarbe */
    koerper.appendChild(el("div", "ein-titel", "Kachel- und Textfarbe"));
    flaechenAbschnitt = el("div");
    flaechenAbschnitt.appendChild(baueFlaechenAbschnitt());
    koerper.appendChild(flaechenAbschnitt);

    /* Abschnitt Hintergrund */
    koerper.appendChild(el("div", "ein-titel", "Hintergrund"));
    hintergrundAbschnitt = el("div");
    hintergrundAbschnitt.appendChild(baueHintergrundAbschnitt());
    koerper.appendChild(hintergrundAbschnitt);

    kasten.appendChild(koerper);
    huelle.appendChild(kasten);

    huelle.addEventListener("click", function (e) {
      if (e.target === huelle) { schliessen(); }
    });

    document.body.appendChild(huelle);
    dialog = huelle;
    return dialog;
  }

  var zuletztFokus = null;

  function oeffnen() {
    var d = baueDialog();
    zeichneEinstellungenNeu();
    zuletztFokus = document.activeElement;
    d.hidden = false;
    document.body.classList.add("ein-offen");
    var ersterKnopf = d.querySelector(".ein-schliessen");
    if (ersterKnopf) { ersterKnopf.focus(); }
  }

  function schliessen() {
    if (!dialog || dialog.hidden) { return; }
    dialog.hidden = true;
    document.body.classList.remove("ein-offen");
    if (zuletztFokus && zuletztFokus.focus) { zuletztFokus.focus(); }
  }

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && dialog && !dialog.hidden) { schliessen(); }
  });

  /* --- Zahnrad-Knopf in die Kopfzeile ----------------------------------- */

  function baueKnopf() {
    var alt = altSchalter();
    if (!alt) { return; }

    /* Der alte Knopf bleibt im Dokument, wird aber nur noch programmatisch
       benutzt (siehe Kopfkommentar). */
    alt.classList.add("thema-schalter-versteckt");
    alt.setAttribute("tabindex", "-1");
    alt.setAttribute("aria-hidden", "true");

    var knopf = el("button", "ein-knopf");
    knopf.type = "button";
    knopf.id = "einstellungKnopf";
    knopf.setAttribute("aria-label", "Einstellungen öffnen");
    knopf.title = "Einstellungen";
    knopf.innerHTML =
      '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" ' +
      'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<circle cx="12" cy="12" r="3.2"></circle>' +
      '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1.08-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 8.6a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path>' +
      '</svg><span>Einstellungen</span>';
    knopf.addEventListener("click", oeffnen);

    alt.parentNode.insertBefore(knopf, alt);
  }

  /* --- Start ------------------------------------------------------------ */

  function start() {
    laden();
    baueKnopf();
    melden();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }

})();
