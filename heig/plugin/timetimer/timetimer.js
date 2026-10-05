/*
 * Time-timer pour Reveal.js (plugin HEIG-VD).
 *
 * Dans une slide (markdown ou HTML) :
 *     <timetimer time="5min"></timetimer>
 *     <timetimer time="90s" title="Concept test" sound="off"></timetimer>
 *
 * time  : "5min", "5 min", "5m", "90s", "1h", "2:30" (mm:ss) ou "5" (minutes)
 * title : texte affiché dans le bandeau du minuteur (optionnel)
 * sound : "off" pour couper les bips de fin (optionnel, défaut "on")
 *
 * La balise devient un bouton. Un clic ouvre un petit panneau flottant,
 * déplaçable par son bandeau, posé hors des slides : il reste affiché quand
 * on change de slide. Boutons : pause / reprise, remise à zéro, plein écran,
 * fermer. Un seul minuteur à la fois.
 *
 * Chargement (template) :
 *     <link rel="stylesheet" href="{{ static_revealjs }}/plugin/timetimer/timetimer.css">
 *     <script src="{{ static_revealjs }}/plugin/timetimer/timetimer.js"></script>
 *     Reveal.initialize({ plugins: [ ..., RevealTimeTimer ] })
 */
(function (root) {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";
  var panneau = null;          // un seul panneau pour toute la présentation
  var etat = null;             // { duree, restant, debut, enCours, fini, titre, son }
  var tic = null;

  // ------------------------------------------------------------------ durées
  function lireDuree(txt) {
    txt = String(txt || "").trim().toLowerCase().replace(",", ".");
    var m = txt.match(/^(\d+):(\d{1,2})$/);                 // mm:ss
    if (m) return (+m[1]) * 60 + (+m[2]);
    m = txt.match(/^(\d+(?:\.\d+)?)\s*(h|min|mn|m|s|sec)?$/);
    if (!m) return null;
    var v = parseFloat(m[1]), u = m[2] || "min";
    if (u === "h") return Math.round(v * 3600);
    if (u === "s" || u === "sec") return Math.round(v);
    return Math.round(v * 60);
  }

  function formater(s) {
    s = Math.max(0, Math.ceil(s));
    var h = Math.floor(s / 3600), mn = Math.floor((s % 3600) / 60), sec = s % 60;
    var mmss = (h ? h + ":" + String(mn).padStart(2, "0") : mn) + ":" + String(sec).padStart(2, "0");
    return mmss;
  }

  function libelleCourt(s) {
    if (s % 60 === 0 && s >= 60) return (s / 60) + " min";
    if (s < 60) return s + " s";
    return formater(s);
  }

  // ------------------------------------------------------------------ dessin
  // Disque plein = durée totale ; le secteur rouge (temps restant) se vide
  // dans le sens horaire, comme un Time Timer.
  function secteur(fraction) {
    if (fraction >= 0.9999) return "M50,50 m-46,0 a46,46 0 1,0 92,0 a46,46 0 1,0 -92,0";
    if (fraction <= 0) return "";
    var a = fraction * 2 * Math.PI;
    var x = 50 - 46 * Math.sin(a), y = 50 - 46 * Math.cos(a);   // part du haut, recule vers la gauche
    var grand = fraction > 0.5 ? 1 : 0;
    return "M50,50 L50,4 A46,46 0 " + grand + ",0 " + x.toFixed(3) + "," + y.toFixed(3) + " Z";
  }

  function el(tag, attrs, parent, ns) {
    var e = ns ? document.createElementNS(NS, tag) : document.createElement(tag);
    for (var k in attrs || {}) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }

  function construirePanneau() {
    var p = el("div", { "class": "tt-panneau", role: "timer", "aria-live": "off" }, document.body);
    var bandeau = el("div", { "class": "tt-bandeau", title: "Glisser pour déplacer" }, p);
    el("span", { "class": "tt-titre" }, bandeau);
    var fermer = el("button", { "class": "tt-btn tt-fermer", title: "Fermer", "aria-label": "Fermer" }, bandeau);
    fermer.textContent = "×";

    var svg = el("svg", { "class": "tt-cadran", viewBox: "0 0 100 100" }, p, true);
    el("circle", { cx: 50, cy: 50, r: 48, "class": "tt-fond" }, svg, true);
    for (var i = 0; i < 12; i++) {                                  // graduations
      var a = i * Math.PI / 6;
      el("line", { x1: 50 + 44 * Math.sin(a), y1: 50 - 44 * Math.cos(a),
                   x2: 50 + 48 * Math.sin(a), y2: 50 - 48 * Math.cos(a), "class": "tt-grad" }, svg, true);
    }
    el("path", { "class": "tt-secteur", d: secteur(1) }, svg, true);
    el("circle", { cx: 50, cy: 50, r: 5, "class": "tt-axe" }, svg, true);

    el("div", { "class": "tt-temps" }, p);
    var barre = el("div", { "class": "tt-commandes" }, p);
    var pause = el("button", { "class": "tt-btn tt-pause" }, barre);
    var raz = el("button", { "class": "tt-btn tt-raz", title: "Remettre à zéro" }, barre);
    raz.textContent = "↺";
    var plein = el("button", { "class": "tt-btn tt-plein", title: "Plein écran" }, barre);
    plein.textContent = "⛶";

    pause.addEventListener("click", function () { basculerPause(); this.blur(); });
    raz.addEventListener("click", function () { lancer(etat.duree, etat.titre, etat.son); this.blur(); });
    plein.addEventListener("click", function () { pleinEcran(); this.blur(); });
    fermer.addEventListener("click", fermerPanneau);
    rendreDeplacable(p, bandeau);
    return p;
  }

  // ------------------------------------------------------------------ déplacement
  function rendreDeplacable(p, poignee) {
    var dx = 0, dy = 0, actif = false;
    poignee.addEventListener("pointerdown", function (e) {
      if (e.target.closest("button") || document.fullscreenElement === p) return;
      actif = true;
      var r = p.getBoundingClientRect();
      dx = e.clientX - r.left; dy = e.clientY - r.top;
      poignee.setPointerCapture(e.pointerId);
      e.preventDefault();
    });
    poignee.addEventListener("pointermove", function (e) {
      if (!actif) return;
      var x = Math.min(Math.max(0, e.clientX - dx), window.innerWidth - p.offsetWidth);
      var y = Math.min(Math.max(0, e.clientY - dy), window.innerHeight - p.offsetHeight);
      p.style.left = x + "px"; p.style.top = y + "px"; p.style.right = "auto";
    });
    poignee.addEventListener("pointerup", function () { actif = false; });
  }

  // ------------------------------------------------------------------ minuteur
  function restant() {
    if (!etat) return 0;
    if (!etat.enCours) return etat.restant;
    return etat.restant - (Date.now() - etat.debut) / 1000;
  }

  function afficher() {
    if (!panneau || !etat) return;
    var r = Math.max(0, restant());
    panneau.querySelector(".tt-secteur").setAttribute("d", secteur(r / etat.duree));
    panneau.querySelector(".tt-temps").textContent = etat.fini ? "Terminé" : formater(r);
    panneau.querySelector(".tt-pause").textContent = etat.enCours ? "❚❚" : "▶";
    panneau.querySelector(".tt-pause").title = etat.enCours ? "Pause" : "Reprendre";
    if (r <= 0 && !etat.fini) terminer();
  }

  function lancer(duree, titre, son) {
    if (!panneau) panneau = construirePanneau();
    etat = { duree: duree, restant: duree, debut: Date.now(), enCours: true, fini: false,
             titre: titre, son: son };
    panneau.classList.remove("tt-fini");
    panneau.querySelector(".tt-titre").textContent = titre || libelleCourt(duree);
    panneau.style.display = "";
    clearInterval(tic);
    tic = setInterval(afficher, 200);
    afficher();
  }

  function basculerPause() {
    if (!etat || etat.fini) return;
    if (etat.enCours) { etat.restant = restant(); etat.enCours = false; }
    else { etat.debut = Date.now(); etat.enCours = true; }
    afficher();
  }

  function terminer() {
    etat.fini = true; etat.enCours = false; etat.restant = 0;
    clearInterval(tic);
    panneau.classList.add("tt-fini");
    afficher();
    if (etat.son) bips();
  }

  function fermerPanneau() {
    clearInterval(tic);
    if (document.fullscreenElement === panneau) document.exitFullscreen();
    if (panneau) panneau.style.display = "none";
    etat = null;
  }

  function pleinEcran() {
    if (document.fullscreenElement === panneau) document.exitFullscreen();
    else if (panneau.requestFullscreen) panneau.requestFullscreen();
  }

  function bips() {
    try {
      var ctx = new (window.AudioContext || window.webkitAudioContext)();
      [0, 0.35, 0.7].forEach(function (t) {
        var o = ctx.createOscillator(), g = ctx.createGain();
        o.frequency.value = 880; o.connect(g); g.connect(ctx.destination);
        g.gain.setValueAtTime(0.25, ctx.currentTime + t);
        g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + t + 0.25);
        o.start(ctx.currentTime + t); o.stop(ctx.currentTime + t + 0.26);
      });
    } catch (e) { /* pas d'audio : tant pis */ }
  }

  // ------------------------------------------------------------------ balises
  function remplacerBalises(racine) {
    var balises = racine.querySelectorAll("timetimer");
    Array.prototype.forEach.call(balises, function (b) {
      var duree = lireDuree(b.getAttribute("time"));
      var titre = b.getAttribute("title") || "";
      var son = ["off", "no", "false", "0"].indexOf((b.getAttribute("sound") || "on").toLowerCase()) < 0;
      var bouton = document.createElement("button");
      bouton.className = "tt-lancer";
      if (duree === null) {
        bouton.textContent = "timetimer : time illisible « " + b.getAttribute("time") + " »";
        bouton.disabled = true;
      } else {
        bouton.innerHTML = '<svg viewBox="0 0 100 100" aria-hidden="true"><circle cx="50" cy="50" r="44"/>'
          + '<path d="' + secteur(0.25) + '"/></svg><span>' + libelleCourt(duree) + "</span>";
        bouton.title = "Lancer le minuteur (" + libelleCourt(duree) + ")";
        bouton.addEventListener("click", function (e) {
          e.stopPropagation();
          lancer(duree, titre, son);
          this.blur();                 // sinon Espace relance le bouton au lieu d'avancer
        });
      }
      // une balise non fermée avale le contenu qui suit : on le remet après
      var parent = b.parentNode;
      parent.insertBefore(bouton, b);
      while (b.firstChild) parent.insertBefore(b.firstChild, b);
      parent.removeChild(b);
    });
  }

  root.RevealTimeTimer = {
    id: "timetimer",
    init: function (deck) {
      deck.on("ready", function () { remplacerBalises(deck.getRevealElement()); });
      // Échap ferme le plein écran du navigateur ; on laisse Reveal tranquille sinon.
    },
    // exposé pour la console : RevealTimeTimer.lancer(300)
    lancer: function (s, titre) { lancer(s, titre, true); },
    lireDuree: lireDuree
  };
})(window);
