/* ===========================================================================
   hintergrund.js - Hintergrundbild fuer die Startseite
   ---------------------------------------------------------------------------
   Laeuft seit 2026-10-17 auf ALLEN Seiten (Wunsch Felix: einheitlicher Look). Seit 2026-10-17 gibt es keine Animation und keine
   Interaktion mehr: ein festes Foto liegt hinter dem Inhalt, darueber der
   Abdunklungs-Schleier. Die alten Vorlagen (Kurstafel, Handelssaal, Bulle und
   Baer, Hologramm) wurden entfernt, Sicherung: 05_Dashboard/99_Archiv_Hintergruende.

   Gesteuert wird alles ueber einstellungen.js. Diese Datei hoert nur auf das
   Ereignis "hintergrund-geaendert" und setzt Bild und Deckkraft. Die
   Abdunklung ist reines CSS (--hg-abdunklung, .hg-schleier in stil.css).
   =========================================================================== */

(function () {
  "use strict";

  var bild = null, schleier = null;

  function bauen() {
    if (bild) { return; }
    bild = document.createElement("div");
    bild.className = "hg-bild";
    bild.setAttribute("aria-hidden", "true");
    document.body.insertBefore(bild, document.body.firstChild);

    schleier = document.createElement("div");
    schleier.className = "hg-schleier";
    schleier.setAttribute("aria-hidden", "true");
    document.body.insertBefore(schleier, bild.nextSibling);
  }

  function bildVon(id) {
    var liste = window.DASHBOARD_EINSTELLUNGEN ? window.DASHBOARD_EINSTELLUNGEN.vorlagen : [];
    for (var i = 0; i < liste.length; i++) {
      if (liste[i].id === id) { return liste[i].bild; }
    }
    return null;
  }

  function anwenden(stand) {
    bauen();
    /* Laenderseiten: Flagge des Landes (body data-flagge) hat Vorrang, "aus" blendet alles aus */
    var url;
    if (stand.flagge) { url = stand.flagge; }
    else if (stand.fotoAus) { url = null; }
    else { url = stand.an ? bildVon(stand.vorlage) : null; }
    if (!url) {
      bild.style.display = "none";
      schleier.style.display = "none";
      return;
    }
    bild.style.display = "";
    schleier.style.display = "";
    bild.style.backgroundImage = 'url("' + url + '")';
    bild.style.opacity = stand.flagge ? "1" : (stand.werte.deckkraft / 100).toFixed(2);
  }

  document.addEventListener("hintergrund-geaendert", function (e) { anwenden(e.detail); });

  function start() {
    if (window.DASHBOARD_EINSTELLUNGEN) { anwenden(window.DASHBOARD_EINSTELLUNGEN.lesen()); }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
