/* ============================================================================
   seewege.js  -  Seewege, Flugrouten und Hafen-Koordinaten fuer die Lieferketten-Karte
   (USA Oberthema 5, laender/usa-handel.html)

   WICHTIG: Das sind SCHEMATISCHE Hauptrouten, keine echten Schiffs- oder Flugdaten.
   - Seewege: Wegpunkte (Laenge, Breite) der ueblichen Hauptroute vom Hafen des Partnerlands
     zu einem US-Hafen (West: Los Angeles/Long Beach, Ost: New York/Newark, Golf: Houston).
     Die tatsaechliche Fahrt kann abweichen (z. B. Umfahrung des Kaps der Guten Hoffnung
     statt Suezkanal, Panamakanal, andere Haefen).
   - Flugrouten: Grosskreis (kuerzeste Linie auf der Erdkugel) zwischen dem wichtigsten
     Frachtflughafen des Partnerlands und einem grossen US-Frachtflughafen.
   Koordinaten stammen aus allgemein bekannten Hafen-/Flughafenlagen (Naeherungswerte).
   Die Datei wird von Hand gepflegt, nicht von einem Skript ueberschrieben.
   ============================================================================ */
(function(){
"use strict";
var R=Math.PI/180;
var X0=Math.PI*0.8707, SKAL=1000/(2*X0), MINY=null;

/* Natural-Earth-Projektion wie in Weltkarte_Bauen.py. MINY wird an einem bekannten Punkt
   (Mitte der USA, in welt-karte.js gespeichert) geeicht. */
function rohproj(lon,lat){
  var l=lon*R,p=lat*R,p2=p*p,p4=p2*p2;
  var x=l*(0.8707-0.131979*p2+p4*(-0.013791+p4*(0.003971*p2-0.001529*p4)));
  var y=p*(1.007226+p2*(0.015085+p4*(-0.044475+0.028874*p2-0.005916*p4)));
  return [x,-y];
}
function eichen(){
  if(MINY!==null)return true;
  var W=window.WELT; if(!W||!W.punkte||!W.punkte["840"])return false;
  MINY=rohproj(-98,39)[1]-W.punkte["840"][1]/SKAL; return true;
}
function proj(lon,lat){var q=rohproj(lon,lat);return [(q[0]+X0)*SKAL,(q[1]-MINY)*SKAL]}
function wrap(lon){return ((lon+180)%360+360)%360-180}

/* ---- Hilfen: Linienzug glaetten (Catmull-Rom) und in Teilstuecke an der Datumsgrenze schneiden ---- */
function entwickeln(pts){ /* Laengen fortlaufend machen (ohne Spruenge ueber 180 Grad) */
  var o=[[pts[0][0],pts[0][1]]];
  for(var i=1;i<pts.length;i++){var lo=pts[i][0],v=o[o.length-1][0];while(lo-v>180)lo-=360;while(lo-v<-180)lo+=360;o.push([lo,pts[i][1]])}
  return o;
}
function glaetten(pts,n){
  if(pts.length<3)return pts;
  var out=[],P=function(i){return pts[Math.max(0,Math.min(pts.length-1,i))]};
  for(var i=0;i<pts.length-1;i++){
    var p0=P(i-1),p1=P(i),p2=P(i+1),p3=P(i+2);
    for(var s=0;s<n;s++){var t=s/n,t2=t*t,t3=t2*t;
      out.push([0.5*((2*p1[0])+(-p0[0]+p2[0])*t+(2*p0[0]-5*p1[0]+4*p2[0]-p3[0])*t2+(-p0[0]+3*p1[0]-3*p2[0]+p3[0])*t3),
                0.5*((2*p1[1])+(-p0[1]+p2[1])*t+(2*p0[1]-5*p1[1]+4*p2[1]-p3[1])*t2+(-p0[1]+3*p1[1]-3*p2[1]+p3[1])*t3)]);}
  }
  out.push(pts[pts.length-1]); return out;
}
function zuPfad(pts){ /* pts: entwickelte (lon,lat)-Punkte -> SVG-Pfad, an der Datumsgrenze geteilt */
  var teile=[[]],i,a,b;
  for(i=0;i<pts.length;i++){
    b=pts[i];
    if(i>0){a=pts[i-1];
      var ka=Math.floor((a[0]+180)/360),kb=Math.floor((b[0]+180)/360);
      if(ka!==kb){var grenze=kb>ka?180+360*ka:180+360*kb,t=(grenze-a[0])/(b[0]-a[0]),lat=a[1]+(b[1]-a[1])*t;
        var seiteA=kb>ka?180:-180;
        teile[teile.length-1].push([seiteA,lat]);teile.push([[-seiteA,lat]]);}
    }
    teile[teile.length-1].push([wrap(b[0]),b[1]]);
  }
  return teile.filter(function(t){return t.length>1}).map(function(t){
    return "M"+t.map(function(q){var p=proj(q[0],q[1]);return p[0].toFixed(1)+","+p[1].toFixed(1)}).join("L");
  }).join("");
}

/* ---- US-Ankunftspunkte ---- */
var US={W:[-118.4,33.6],E:[-73.8,40.4],G:[-94.4,28.9]};

/* ---- Streckenstuecke (Laenge, Breite) ---- */
var P={
 /* Pazifik: Hub vor Tokio -> Los Angeles (noerdliche Grosskreisnaehe) */
 PAZ:[[142,34.2],[152,38],[167,43],[-178,45.8],[-158,43.5],[-138,38.5],[-125,34.5],[-120.3,33.6],US.W],
 /* Energie (Fluessiggas, Rohoel) zwischen dem Golf (Houston) und Ostasien: ueber den Panamakanal */
 PAN_PAZ:[[142,34.2],[160,31],[-175,26],[-150,19],[-125,12.5],[-100,8.5],[-85,6.5],[-79.5,8.3],[-79.9,9.4],[-80.3,10.8],[-82,18.5],[-85.8,22],[-87.5,24.5],[-91,27.4],US.G],
 /* Suedpazifik (Australien, Neuseeland) -> Los Angeles */
 SPAZ:[[-165,-10],[-150,0],[-137,13],[-127,24],[-121.5,31.5],US.W],
 /* Pazifikkueste Suedamerikas -> Los Angeles */
 PSA:[[-81,-8],[-82,-2],[-83,4],[-90,11],[-100,15.5],[-108,19.5],[-111,21.3],[-114.5,24.5],[-117.3,28.5],[-118.3,31.5],US.W],
 /* Rotes Meer, Suezkanal, Mittelmeer */
 RED:[[51.5,12.5],[45.5,12.2],[43.3,12.7],[41.5,14.3],[39.5,17.8],[37.5,21.5],[35.5,25],[33.8,27.2],[32.6,29.7],[32.3,31.3]],
 MEDE:[[29,33.0],[24,34.4]],
 MEDW:[[18,35.6],[12,36.9],[8,37.6],[2,38.2],[-1.5,36.5]],
 /* Atlantik ab Gibraltar */
 GIB_E:[[-5.6,36],[-9.6,36.2],[-28,37.5],[-50,39],[-64,39.8],[-72,39.8],US.E],
 GIB_G:[[-5.6,36],[-9.6,36.2],[-30,33],[-55,28.8],[-68,28.4],[-77,27.4],[-79.7,25.7],[-80.3,24.5],[-82.5,24.2],[-86.5,25.5],[-90.5,27.4],US.G],
 /* Atlantik ab Westeingang des Aermelkanals */
 EUR_E:[[-12,49.6],[-30,47.5],[-50,43.5],[-63,40.2],[-70.5,39.6],US.E],
 EUR_G:[[-12,49.6],[-26,43],[-45,34],[-62,28.6],[-70,28.4],[-77,27.4],[-79.7,25.7],[-80.3,24.5],[-82.5,24.2],[-86.5,25.5],[-90.5,27.4],US.G],
 /* Karibik: Knoten vor Kolumbien, weiter zum Golf oder zur Ostkueste */
 CAR_G:[[-82,18.5],[-85.8,22],[-87.5,24.5],[-91,27.4],US.G],
 CAR_E:[[-75.8,16],[-73.8,19.9],[-73.9,22],[-74.5,24.5],[-76,28],[-75,34],[-74.4,38.6],US.E],
 /* Yucatan-Strasse -> Ostkueste (ueber die Floridastrasse) */
 YUC_E:[[-83.5,23.6],[-80.5,24.2],[-79.6,25.9],[-79.3,28.5],[-76.5,33],[-74.5,38.5],US.E],
 YUC_G:[[-87.5,24.5],[-91,27.4],US.G],
 /* Suedatlantik (Brasilien) -> Ostkueste bzw. Karibik/Golf */
 SAA_E:[[-58,15.5],[-63,22],[-68,28],[-72,34],[-73.9,39.2],US.E],
 SAA_G:[[-58,11],[-61.6,11.5],[-66,13.5],[-72.5,13.5],[-76,13.6],[-78,14],[-82,18.5],[-85.8,22],[-87.5,24.5],[-91,27.4],US.G]
};
/* Suedostasien -> Ostasien (gemeinsame Bausteine) */
var SOA=[[117,21],[120.5,21.2],[122,22.5],[123.5,25.5],[126,28.5],[130.4,30],[135,31.6]];
var TWN=[[122,22.5],[123.5,25.5],[126,28.5],[130.4,30],[135,31.6]];
var BRA_N=[[-36,1],[-44,5.5],[-50,8.8],[-54,10.5]];
var BRA_S=[[-46.2,-24.2],[-41,-24],[-37.2,-14],[-33.8,-8],[-33.5,-4]];

/* ---- Partnerlaender (ISO-3166-numerisch wie in welt-karte.js) ----
   st: Weg vom Partnerhafen bis zum Anschluss, tail: Name des Anschluss-Stuecks (siehe unten)
   fix: erzwingt Ziel ("W","E","G"), sonst: Energie -> Golf, alles andere -> Ostkueste
   ek/gk: eigene Wegfolgen fuer Ostkueste bzw. Golf, falls die Route je nach Ziel anders beginnt */
var L={
 /* --- Ostasien / Pazifik (Ziel immer Westkueste) --- */
 "156":{n:"Shanghai",st:[[122.3,30.8],[125.5,30.6],[130.4,30],[135,31.6]],tail:"PAZ",fix:"W"},
 "158":{n:"Kaohsiung",st:[[120.2,22.5],[120.5,21.5]].concat(TWN),tail:"PAZ",fix:"W"},
 "344":{n:"Hongkong",st:[[114.2,22.2],[117,21.3],[120.5,21.2]].concat(TWN),tail:"PAZ",fix:"W"},
 "410":{n:"Busan",st:[[129.1,35],[128.9,33.8],[128.5,32.2],[130,30.3],[135,31.6]],tail:"PAZ",fix:"W"},
 "392":{n:"Tokio/Yokohama",st:[[139.8,35]],tail:"PAZ",fix:"W"},
 "704":{n:"Cai Mep",st:[[107,10.4],[109.5,11.5],[111,15],[113.5,19]].concat(SOA),tail:"PAZ",fix:"W"},
 "702":{n:"Singapur",st:[[103.8,1.1],[104.8,2.2],[107.5,6.5],[110.2,12],[112.2,17],[114.5,20]].concat(SOA),tail:"PAZ",fix:"W"},
 "458":{n:"Port Klang",st:[[101.3,2.9],[102.6,1.8],[103.8,1.1],[104.8,2.2],[107.5,6.5],[110.2,12],[112.2,17],[114.5,20]].concat(SOA),tail:"PAZ",fix:"W"},
 "764":{n:"Laem Chabang",st:[[100.9,13],[101.8,10.5],[103.6,8],[105.5,6.5],[107.5,6.5],[110.2,12],[112.2,17],[114.5,20]].concat(SOA),tail:"PAZ",fix:"W"},
 "360":{n:"Jakarta",st:[[106.9,-6],[106.4,-5],[105.6,-2.5],[105,0],[104.8,2.2],[107.5,6.5],[110.2,12],[112.2,17],[114.5,20]].concat(SOA),tail:"PAZ",fix:"W"},
 "608":{n:"Manila",st:[[120.9,14.5],[119.9,15.5],[119.9,18.5],[121,20.6],[122.8,23.5],[123.5,25.5],[126,28.5],[130.4,30],[135,31.6]],tail:"PAZ",fix:"W"},
 "036":{n:"Sydney",st:[[151.4,-34],[157,-32],[168,-27],[-178,-22]],tail:"SPAZ",fix:"W"},
 "554":{n:"Auckland",st:[[174.8,-36.5],[178,-33],[-178,-27],[-170,-15]],tail:"SPAZ",fix:"W"},
 "152":{n:"Valparaiso",st:[[-71.6,-33],[-73,-28],[-76.5,-18]],tail:"PSA",fix:"W"},
 "604":{n:"Callao",st:[[-77.3,-12.2],[-80,-6]],tail:"PSA",fix:"W"},
 "218":{n:"Guayaquil",st:[[-80,-2.3],[-81.4,-2.9]],tail:"PSA",fix:"W"},
 "068":{n:"Arica (Chile)",st:[[-70.4,-18.5],[-72,-18],[-76.5,-18]],tail:"PSA",fix:"W",via:true},
 /* --- Europa (Atlantik) --- */
 "276":{n:"Bremerhaven/Hamburg",st:[[8.5,53.8],[6.8,54.2],[3.8,53.4],[2.4,51.7],[1.5,50.9],[-1.5,49.9],[-6,49.2]],tail:"EUR"},
 "528":{n:"Rotterdam",st:[[4,52],[3.2,51.8],[2.4,51.5],[1.5,50.9],[-1.5,49.9],[-6,49.2]],tail:"EUR"},
 "056":{n:"Antwerpen",st:[[3.5,51.5],[2.4,51.5],[1.5,50.9],[-1.5,49.9],[-6,49.2]],tail:"EUR"},
 "826":{n:"Southampton",st:[[-1.4,50.7],[-1.5,50],[-6,49.2]],tail:"EUR"},
 "372":{n:"Dublin",st:[[-6.1,53.3],[-5.8,52],[-7.5,51],[-11,50]],tail:"EUR"},
 "250":{n:"Le Havre",st:[[0,49.65],[-1.2,50.2],[-6,49.2]],tail:"EUR"},
 "752":{n:"Goeteborg",st:[[11.7,57.6],[8,58],[5,56.5],[3.7,54],[2.4,51.8],[1.5,50.9],[-1.5,49.9],[-6,49.2]],tail:"EUR"},
 "756":{n:"Rotterdam (Schweiz ohne Seehafen)",st:[[4,52],[3.2,51.8],[2.4,51.5],[1.5,50.9],[-1.5,49.9],[-6,49.2]],tail:"EUR",via:true},
 "703":{n:"Bremerhaven (Slowakei ohne Seehafen)",st:[[8.5,53.8],[6.8,54.2],[3.8,53.4],[2.4,51.7],[1.5,50.9],[-1.5,49.9],[-6,49.2]],tail:"EUR",via:true},
 /* --- Mittelmeer (ueber Gibraltar) --- */
 "724":{n:"Valencia",st:[[-0.3,39.4],[0.3,38.2],[-1.5,36.5]],tail:"GIB"},
 "380":{n:"Genua",st:[[8.9,44.3],[8.5,42.8],[6,40.6],[2.2,38.6],[-1.5,36.5]],tail:"GIB"},
 "818":{n:"Alexandria",st:[[29.9,31.4],[27,33.5],[24,34.4]].concat(P.MEDW),tail:"GIB"},
 "268":{n:"Poti",st:[[41.6,42.1],[38,42.4],[31,42.2],[29.2,41.3],[28.8,40.8],[26.6,40.3],[26,39.8],[25,38.5],[23.5,36.6],[22,35.8]].concat(P.MEDW),tail:"GIB"},
 "376":{n:"Haifa",st:[[34.9,32.9],[31,33.7],[24,34.4]].concat(P.MEDW),tail:"GIB"},
 /* --- Suez / Golf von Aden --- */
 "356":{n:"Mumbai (Nhava Sheva)",st:[[72.9,18.9],[69,17.5],[60,14.5]].concat(P.RED,P.MEDE,P.MEDW),tail:"GIB"},
 "682":{n:"Ras Tanura (Golf)",st:[[50.8,27],[52.5,26.8],[55,26.5],[56.5,26.4],[57.5,25],[59.5,22.8],[58,19],[55,15]].concat(P.RED,P.MEDE,P.MEDW),tail:"GIB"},
 "784":{n:"Jebel Ali (Golf)",st:[[55,25.1],[56.5,26.4],[57.5,25],[59.5,22.8],[58,19],[55,15]].concat(P.RED,P.MEDE,P.MEDW),tail:"GIB"},
 "368":{n:"Umm Qasr (Golf)",st:[[48.2,29.8],[49.5,28.5],[52.5,26.8],[55,26.5],[56.5,26.4],[57.5,25],[59.5,22.8],[58,19],[55,15]].concat(P.RED,P.MEDE,P.MEDW),tail:"GIB"},
 /* --- Amerika --- */
 "484":{n:"Veracruz",st:[[-96,19.3],[-95.5,22.5],[-95.3,26],[-94.5,28.7]],tail:null,fix:"G"},
 "124":{n:"Halifax",st:[[-63.5,44.5],[-63.3,43.5],[-66,42.5],[-69.5,41],[-72.5,40.2],[-73.8,40.4]],tail:null,fix:"E"},
 "170":{n:"Cartagena",st:[[-75.6,10.4],[-76.2,12],[-77.5,14]],tail:"CAR"},
 "862":{ek:{n:"La Guaira",st:[[-66.9,10.7],[-67,14],[-67.9,18],[-68.4,21],[-70,26],[-72.5,33],[-73.9,39],[-73.8,40.4]],tail:null},
         gk:{n:"La Guaira",st:[[-66.9,10.7],[-69,12],[-72.2,13.2],[-76,13.6],[-78,14]],tail:"CAR_G"}},
 "328":{n:"Georgetown",st:[[-58.3,6.9],[-57.4,9.8],[-54,10.5]],tail:"SAA"},
 "188":{n:"Puerto Limon",st:[[-83,10.1],[-81.5,11.8],[-79.5,13.5]],tail:"CAR"},
 "320":{n:"Santo Tomas",st:[[-88.4,15.9],[-86.5,17],[-85.2,19],[-85.8,22]],tail:"YUC"},
 "076":{n:"Santos",st:[[-46.2,-24.2],[-41,-24],[-37.2,-14],[-33.8,-8],[-33.5,-4]].concat(BRA_N),tail:"SAA"},
 "032":{n:"Buenos Aires",st:[[-58.3,-34.5],[-56,-35.2],[-52,-33.5],[-49,-29]].concat(BRA_S,BRA_N),tail:"SAA"},
 "858":{n:"Montevideo",st:[[-56.2,-34.9],[-54,-35.2],[-52,-33.5],[-49,-29]].concat(BRA_S,BRA_N),tail:"SAA"},
 "600":{n:"Buenos Aires (Paraguay ohne Seehafen)",st:[[-58.3,-34.5],[-56,-35.2],[-52,-33.5],[-49,-29]].concat(BRA_S,BRA_N),tail:"SAA",via:true}
};
/* Anschluss-Stuecke nach Ziel (E/G); fuer Westkueste ist das Stueck selbst das Ziel */
var TAILS={
 PAZ:{W:P.PAZ}, SPAZ:{W:P.SPAZ}, PSA:{W:P.PSA},
 EUR:{E:P.EUR_E,G:P.EUR_G}, GIB:{E:P.GIB_E,G:P.GIB_G},
 CAR:{E:P.CAR_E,G:P.CAR_G}, CAR_G:{E:P.CAR_G,G:P.CAR_G},
 YUC:{E:P.YUC_E,G:P.YUC_G}, SAA:{E:P.SAA_E,G:P.SAA_G}
};

/* ---- Frachtflughaefen (Partner) und US-Tore ---- */
var HUB={ /* iso: [Laenge, Breite, Tor] ; Tor: JFK, LAX, MIA, ORD, DFW */
 "156":[121.8,31.1,"LAX"],"344":[113.9,22.3,"LAX"],"158":[121.2,25.1,"LAX"],"410":[126.4,37.5,"LAX"],"392":[140.4,35.8,"LAX"],
 "704":[106.7,10.8,"LAX"],"702":[104,1.4,"LAX"],"458":[101.7,2.7,"LAX"],"764":[100.8,13.7,"LAX"],"360":[106.7,-6.1,"LAX"],"608":[121,14.5,"LAX"],
 "036":[151.2,-33.9,"LAX"],"554":[174.8,-37,"LAX"],"356":[72.9,19.1,"JFK"],
 "276":[8.6,50,"JFK"],"528":[4.8,52.3,"JFK"],"056":[5.4,50.6,"JFK"],"826":[-0.45,51.5,"JFK"],"372":[-6.3,53.4,"JFK"],"250":[2.5,49,"JFK"],
 "752":[18,59.7,"JFK"],"756":[8.5,47.5,"JFK"],"703":[17.2,48.2,"JFK"],"724":[-3.6,40.5,"JFK"],"380":[8.7,45.6,"JFK"],"818":[31.4,30.1,"JFK"],
 "376":[34.9,32,"JFK"],"268":[44.95,41.67,"JFK"],"682":[46.7,24.9,"JFK"],"784":[55.4,25.2,"JFK"],"368":[44.2,33.3,"JFK"],
 "484":[-99.1,19.4,"DFW"],"124":[-79.6,43.7,"ORD"],"170":[-74.1,4.7,"MIA"],"862":[-66.9,10.6,"MIA"],"328":[-58.3,6.5,"MIA"],"188":[-84.2,10,"MIA"],
 "320":[-90.5,14.6,"MIA"],"076":[-46.5,-23.4,"MIA"],"032":[-58.5,-34.8,"MIA"],"858":[-56,-34.8,"MIA"],"600":[-57.5,-25.2,"MIA"],
 "152":[-70.8,-33.4,"MIA"],"604":[-77.1,-12,"MIA"],"218":[-78.4,-0.1,"MIA"],"068":[-68.2,-16.5,"MIA"]
};
var TOR={JFK:[-73.8,40.6],LAX:[-118.4,33.9],MIA:[-80.3,25.8],ORD:[-87.9,42],DFW:[-97,32.9]};

function grosskreis(a,b,n){
  var la1=a[1]*R,lo1=a[0]*R,la2=b[1]*R,lo2=b[0]*R;
  var d=2*Math.asin(Math.sqrt(Math.pow(Math.sin((la2-la1)/2),2)+Math.cos(la1)*Math.cos(la2)*Math.pow(Math.sin((lo2-lo1)/2),2)));
  var out=[];
  if(d<1e-6)return [a,b];
  for(var i=0;i<=n;i++){var f=i/n,A=Math.sin((1-f)*d)/Math.sin(d),B=Math.sin(f*d)/Math.sin(d);
    var x=A*Math.cos(la1)*Math.cos(lo1)+B*Math.cos(la2)*Math.cos(lo2),y=A*Math.cos(la1)*Math.sin(lo1)+B*Math.cos(la2)*Math.sin(lo2),z=A*Math.sin(la1)+B*Math.sin(la2);
    out.push([Math.atan2(y,x)/R,Math.atan2(z,Math.sqrt(x*x+y*y))/R]);}
  return out;
}


/* ---- US-Haefen (Namen wie im Census-Datensatz, Lage als Naeherung) ---- */
var HAFEN={
 "HOUSTON, TX":[-95.27,29.73],"CORPUS CHRISTI, TX":[-97.22,27.81],"LOS ANGELES, CA":[-118.27,33.73],"NEW ORLEANS, LA":[-90.06,29.95],
 "BEAUMONT, TX":[-94.1,30.08],"BALTIMORE, MD":[-76.58,39.26],"NEWARK, NJ":[-74.15,40.69],"BRUNSWICK, GA":[-81.49,31.15],
 "LAKE CHARLES, LA":[-93.22,30.23],"SAVANNAH, GA":[-81.09,32.08],"NORFOLK-NEWPORT NEWS, VA":[-76.33,36.95],"CHARLESTON, SC":[-79.93,32.78],
 "FREEPORT, TX":[-95.3,28.94],"OAKLAND, CA":[-122.32,37.8],"SABINE, TX":[-93.87,29.73],"PHILADELPHIA, PA":[-75.14,39.92],
 "JACKSONVILLE, FL":[-81.63,30.39],"PORT HUENEME, CA":[-119.21,34.15],"LONG BEACH, CA":[-118.21,33.75],"GRAMERCY, LA":[-90.69,30.05],
 "PORT ARTHUR, TX":[-93.93,29.88],"PORTLAND, OR":[-122.67,45.62],"TACOMA, WA":[-122.42,47.27],"TEXAS CITY, TX":[-94.9,29.38],
 "RICHMOND, CA":[-122.38,37.93],"CARQUINEZ STRAIT, CA":[-122.2,38.06],"SAN DIEGO, CA":[-117.15,32.7],"MORGAN CITY, LA":[-91.2,29.7],
 "KALAMA, WA":[-122.85,46.02],"BOSTON, MA":[-71.05,42.35],"NEW YORK, NY":[-74.02,40.67],"MARTINEZ, CA":[-122.13,38.02],
 "CHESTER, PA":[-75.36,39.85],"PASCAGOULA, MS":[-88.56,30.35],"SEATTLE, WA":[-122.35,47.6],"GALVESTON, TX":[-94.8,29.31],
 "PORT EVERGLADES, FL":[-80.12,26.09],"LONGVIEW, WA":[-122.95,46.14],"MIAMI, FL":[-80.17,25.78],"VANCOUVER, WA":[-122.67,45.63],
 "WILMINGTON, NC":[-77.95,34.23],"WILMINGTON, DE":[-75.55,39.73],"INTERNATIONAL FALLS-RANIER, MN":[-93.4,48.6],"PORTSMOUTH, NH":[-70.76,43.07],
 "MOBILE, AL":[-88.04,30.69],"TAMPA, FL":[-82.45,27.95],"PORTLAND, ME":[-70.25,43.65],"BATON ROUGE, LA":[-91.19,30.45],"SAN FRANCISCO, CA":[-122.4,37.77],
 "STOCKTON, CA":[-121.29,37.95],"EVERETT, WA":[-122.2,47.98],"PORT CANAVERAL, FL":[-80.6,28.41],"FERNANDINA BEACH, FL":[-81.46,30.67],
 "PROVIDENCE, RI":[-71.4,41.82],"BRIDGEPORT, CT":[-73.19,41.18],"TOLEDO, OH":[-83.5,41.69],"DETROIT, MI":[-83.05,42.33],"CHICAGO, IL":[-87.6,41.88],
 "DULUTH-SUPERIOR, MN":[-92.1,46.78],"PORT MANATEE, FL":[-82.56,27.64],"CAMDEN-GLOUCESTER, NJ":[-75.12,39.94]
};

/* ---- Oeffentliche Funktionen ---- */
window.SEE={
  bereit:eichen,
  proj:function(lon,lat){return eichen()?proj(lon,lat):null},
  /* Seeweg vom Partner zum US-Hafen (Import-Richtung). Rueckgabe {pfad, hafenName, via, ziel} oder null */
  see:function(iso,gid,rev){
    if(!eichen())return null;var e=L[iso];if(!e)return null;
    var ziel=(gid==="energie")?"G":"E";
    var spec=e;
    if(e.ek||e.gk){spec=ziel==="G"?e.gk:e.ek}
    var z=spec.fix||ziel,pts=spec.st.slice();
    if(spec.tail==="PAZ"&&gid==="energie"){pts=pts.concat(P.PAN_PAZ);z="G"}
    else if(spec.tail){var tn=spec.tail,t=TAILS[tn];if(!t)return null;var tt=t[z]||t.E||t.W;pts=pts.concat(tt)}
    else if(spec.tail===null){/* Weg endet im Zielhafen */}
    if(rev)pts.reverse();
    return {pfad:zuPfad(glaetten(entwickeln(pts),9)),hafen:spec.n,via:!!spec.via,ziel:z};
  },
  /* Flugroute vom Partner zum US-Frachtflughafen (Import-Richtung) */
  luft:function(iso,rev){
    if(!eichen())return null;var h=HUB[iso],a,tor;
    if(h){a=[h[0],h[1]];tor=TOR[h[2]]}
    else return null;
    var gk=grosskreis(a,tor,48);if(rev)gk.reverse();
    return {pfad:zuPfad(entwickeln(gk)),tor:h[2]};
  },
  hatSee:function(iso){return !!L[iso]},
  hafen:function(name){return HAFEN[String(name||'').toUpperCase()]||null},
  hatLuft:function(iso){return !!HUB[iso]},
  zuPfad:zuPfad,
  rohpfade:{glaetten:glaetten,entwickeln:entwickeln,grosskreis:grosskreis}
};
})();
