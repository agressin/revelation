/*
 * Repères de section pour Reveal.js (plugin HEIG-VD).
 *
 * Une « section » = une slide horizontale et sa pile verticale (bloc entre
 * deux `---` dans le markdown). Son nom est, dans l'ordre :
 *   1. l'attribut data-section posé sur une de ses slides
 *        <!-- .slide: data-section="Accroche" -->
 *   2. le premier titre h1-h3 trouvé dans la section
 * Une section sans nom n'est pas affichée (slide de titre, image seule…).
 *
 * A. Pied de page (title-footer) : « titre du cours · section en cours ».
 * B. Barre de progression : un segment par section posé sur la barre de
 *    reveal.js, graduation à chaque frontière ; au survol le segment
 *    s'épaissit et donne son nom ; un clic y amène.
 *
 * Chargement (template) :
 *   <link rel="stylesheet" href="{{ static_revealjs }}/plugin/sections/sections.css">
 *   <script src="{{ static_revealjs }}/plugin/sections/sections.js"></script>
 *   Reveal.initialize({ plugins: [ ..., RevealSections ] })
 */
(function (root) {
  "use strict";

  var deck = null;
  var sections = [];        // { h, nom, debut, fin }  (debut / fin en fraction 0..1)
  var barre = null;
  var titreCours = null;    // titre court du cours (premier h1 de la slide de titre)
  var texteOrigine = null;  // texte d'origine du pied de page

  function nettoyer(t) {
    // retire les pictogrammes de tête (✏️, 🤔…) et les espaces multiples
    return String(t || "").replace(/^[^\p{L}\p{N}]+/u, "").replace(/\s+/g, " ").trim();
  }

  function nomSection(el) {
    var marque = el.matches("[data-section]") ? el : el.querySelector("[data-section]");
    if (marque) return nettoyer(marque.getAttribute("data-section"));
    var titre = el.querySelector("h1, h2, h3");
    return titre ? nettoyer(titre.textContent) : "";
  }

  function nbSlides(el) {
    var pile = el.querySelectorAll(":scope > section");
    return pile.length ? pile.length : 1;
  }

  function calculer() {
    var horizontales = deck.getHorizontalSlides();
    var total = Math.max(1, deck.getTotalSlides() - 1);   // même base que getProgress()
    var avant = 0;
    sections = [];
    horizontales.forEach(function (el, h) {
      var n = nbSlides(el);
      sections.push({ h: h, nom: h === 0 ? "" : nomSection(el), debut: avant / total, n: n });
      avant += n;
    });
    sections.forEach(function (s, i) {
      s.fin = i + 1 < sections.length ? sections[i + 1].debut : 1;
    });
    var titre = horizontales[0] && horizontales[0].querySelector("h1");
    titreCours = titre ? nettoyer(titre.textContent) : null;
  }

  // ---------------------------------------------------------------- A. pied de page
  function majPiedDePage() {
    var lien = document.querySelector("#title-footer a");
    if (!lien) return;
    if (texteOrigine === null) texteOrigine = lien.textContent;
    var h = deck.getIndices().h;
    var s = sections[h];
    // remonter à la dernière section nommée (une section sans titre garde la précédente)
    for (var i = h; i > 0 && s && !s.nom; i--) s = sections[i - 1];
    if (h === 0 || !s || !s.nom || !titreCours) lien.textContent = texteOrigine;
    else lien.textContent = titreCours + " · " + s.nom;
  }

  // ---------------------------------------------------------------- B. barre segmentée
  function construireBarre() {
    if (barre) barre.remove();
    barre = document.createElement("div");
    barre.className = "heig-sections";
    barre.setAttribute("aria-hidden", "true");
    sections.forEach(function (s, i) {
      if (i === 0) return;                       // la slide de titre n'a pas de segment
      var seg = document.createElement("div");
      seg.className = "heig-section";
      seg.style.left = (s.debut * 100) + "%";
      seg.style.width = Math.max(0, (s.fin - s.debut) * 100) + "%";
      seg.dataset.h = s.h;
      if (s.debut > 0.5) seg.classList.add("droite");
      if (s.nom) {
        var etiquette = document.createElement("span");
        etiquette.className = "heig-section-nom";
        etiquette.textContent = s.nom;
        seg.appendChild(etiquette);
      }
      seg.addEventListener("click", function (e) {
        e.stopPropagation();
        deck.slide(s.h, 0);
      });
      barre.appendChild(seg);
    });
    deck.getRevealElement().appendChild(barre);
  }

  function majBarre() {
    if (!barre) return;
    var h = deck.getIndices().h;
    Array.prototype.forEach.call(barre.children, function (seg) {
      var k = +seg.dataset.h;
      seg.classList.toggle("passee", k < h);
      seg.classList.toggle("courante", k === h);
    });
  }

  function maj() { majPiedDePage(); majBarre(); }

  root.RevealSections = {
    id: "sections",
    init: function (d) {
      deck = d;
      if (deck.isPrintView && deck.isPrintView()) return;    // rien à l'impression
      deck.on("ready", function () {
        calculer();
        construireBarre();
        // le pied de page est créé par title-footer dans un autre « ready » :
        // on attend qu'il existe
        setTimeout(maj, 0);
        setTimeout(maj, 300);
      });
      deck.on("slidechanged", maj);
    },
    sections: function () { return sections.slice(); }
  };
})(window);
