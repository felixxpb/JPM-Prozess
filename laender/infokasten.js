/* ===========================================================================
   infokasten.js - gemeinsamer Infokasten "Wichtig: ..." fuer alle Laenderseiten
   ---------------------------------------------------------------------------
   Design (Felix, 2026-11-27): Aufbau wie Variante A (Kopfzeile, ein Kernsatz,
   bis zu drei Kennzahl-Kacheln, Quelle) mit farbig hinterlegtem Hintergrund wie
   Variante E. Die Farbe ist in den Einstellungen waehlbar (Laenderanalyse >
   Infokaesten): einstellungen.js setzt --info-farbe (Rueckfall: --warn).

   Benutzung:
     <div id="ik1"></div>
     infokasten("#ik1", {
       titel: "Charakter des britischen Handels",      // "Wichtig: " kommt dazu
       satz:  "Ein Satz mit der Kernaussage.",
       kacheln: [["ca. 1/3", "der Exporte gehen nach China"], ...],  // 1 bis 3
       quelle: "Quelle: ..."
     });
   Alle Texte duerfen einfaches HTML enthalten (nur eigene, feste Inhalte).
   =========================================================================== */
(function () {
  "use strict";
  var CSS =
    ".ik{--ik:var(--info-farbe,var(--warn,#b97a00));background:color-mix(in srgb,var(--ik) 13%,var(--flaeche,#fff));" +
    "border:1px solid var(--ik);border-left:6px solid var(--ik);border-radius:10px;padding:12px 16px;margin:10px 0 14px;" +
    "box-shadow:var(--schatten,none)}" +
    ".ik .ik-kopf{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--ik);font-weight:700}" +
    ".ik .ik-satz{font-size:16px;font-weight:600;margin:3px 0 10px;color:var(--text,inherit)}" +
    ".ik .ik-kz{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}" +
    ".ik .ik-kz>div{background:var(--flaeche,#fff);border:1px solid var(--rand,rgba(0,0,0,.1));border-radius:8px;padding:8px 12px}" +
    ".ik .ik-kz b{display:block;font-size:22px;line-height:1.15;color:var(--text,inherit)}" +
    ".ik .ik-kz span{font-size:12.5px;color:var(--text2,inherit)}" +
    ".ik .ik-q{font-size:11.5px;color:var(--stumm,#898781);margin-top:8px}" +
    ".ik .ik-kz+.ik-q{margin-top:8px}";

  function stil() {
    if (document.getElementById("ik-stil")) { return; }
    var s = document.createElement("style");
    s.id = "ik-stil";
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  function inhalt(d) {
    var h = '<div class="ik-kopf">Wichtig: ' + d.titel + "</div>";
    if (d.satz) { h += '<div class="ik-satz">' + d.satz + "</div>"; }
    if (d.kacheln && d.kacheln.length) {
      h += '<div class="ik-kz">' + d.kacheln.map(function (k) {
        return "<div><b>" + k[0] + "</b><span>" + k[1] + "</span></div>";
      }).join("") + "</div>";
    }
    if (d.quelle) { h += '<div class="ik-q">' + d.quelle + "</div>"; }
    return h;
  }

  /* In ein vorhandenes Element zeichnen */
  window.infokasten = function (ziel, d) {
    stil();
    var e = typeof ziel === "string" ? document.querySelector(ziel) : ziel;
    if (!e) { return; }
    e.className = "ik";
    e.innerHTML = inhalt(d);
  };

  /* Fertiges Markup als Text (fuer Vorlagen-Strings) */
  window.infokasten.html = function (d) {
    stil();
    return '<div class="ik">' + inhalt(d) + "</div>";
  };
})();
