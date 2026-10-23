/* ===========================================================================
   seitenhintergrund.js - Flagge als Seitenhintergrund auf den USA-Unterseiten
   Die Unterseiten (usa-politik.html usw.) sind eigenstaendige Seiten ohne stil.css.
   Dieses kleine Skript zeigt die Flagge aus <body data-flagge="..."> als feste
   Hintergrundebene, im Dunkelmodus, wie auf usa.html. Es liest dieselben
   Einstellungen wie die Laenderuebersicht (localStorage "dashboard-laender":
   seite = flagge/foto/aus, flaggeAbd = Abdunklung in Prozent).
   =========================================================================== */
(function () {
  "use strict";
  var flagge = document.body && document.body.getAttribute("data-flagge");
  if (!flagge) { return; }

  var L = { seite: "flagge", flaggeAbd: 70 };
  try {
    var g = JSON.parse(localStorage.getItem("dashboard-laender") || "null");
    if (g) {
      if (g.seite) { L.seite = g.seite; }
      if (typeof g.flaggeAbd === "number") { L.flaggeAbd = g.flaggeAbd; }
    }
  } catch (e) { }
  if (L.seite !== "flagge") { return; }

  var css = document.createElement("style");
  css.textContent =
    ".sh-bild,.sh-schleier{position:fixed;top:0;right:0;bottom:0;left:0;pointer-events:none}" +
    ".sh-bild{z-index:-2;background-size:cover;background-position:center;background-repeat:no-repeat}" +
    ".sh-schleier{z-index:-1;background:var(--ebene,#0d0d0d);opacity:" + (L.flaggeAbd / 100).toFixed(2) + "}" +
    ":root:not([data-theme=\"dark\"]) .sh-bild,:root:not([data-theme=\"dark\"]) .sh-schleier{display:none}";
  document.head.appendChild(css);

  var bild = document.createElement("div");
  bild.className = "sh-bild";
  bild.setAttribute("aria-hidden", "true");
  bild.style.backgroundImage = 'url("' + flagge + '")';
  var schleier = document.createElement("div");
  schleier.className = "sh-schleier";
  schleier.setAttribute("aria-hidden", "true");
  document.body.insertBefore(schleier, document.body.firstChild);
  document.body.insertBefore(bild, document.body.firstChild);
})();
