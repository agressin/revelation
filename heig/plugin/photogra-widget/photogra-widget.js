/*
 * Widgets interactifs du livre « Photogrammétrie » dans une slide (plugin HEIG-VD).
 *
 * Dans le markdown, coller le lien donné par le bouton « Partager » du livre
 * (page widgets/embed.html, voir WIDGETS.md du livre, § Intégration) :
 *
 *   <div data-photogra="https://book-photogra-ba0665.gitlab.io/widgets/embed.html?w=parallaxe-bh&b=15&h=60"></div>
 *
 * Attributs facultatifs :
 *   data-width   largeur de la page du widget en px CSS (défaut 1000) : le
 *                widget est dessiné à cette largeur puis agrandi pour remplir
 *                le bloc ; plus petit = texte et commandes plus gros
 *   data-height  hauteur maximale dans la slide en px (défaut : place restante
 *                sous le bloc, jusqu'au bas de la slide)
 *
 * Comportement :
 *   - iframe chargée à l'approche de la slide (data-src de reveal.js), thème
 *     clair forcé, hauteur ajustée au message photogra-widget-height ;
 *   - les touches que le widget n'utilise pas (PageDown, Espace, N, P, Échap,
 *     B, C...) reviennent à la présentation (message photogra-widget-key) ;
 *     au changement de slide, le focus quitte l'iframe ;
 *   - impression (?print-pdf) : iframe chargée tout de suite, le widget
 *     s'imprime dans l'état de l'URL (vectoriel) ; un indicateur à l'écran
 *     compte les widgets prêts (lancer l'impression quand il est vert) ;
 *   - secours : widget en erreur ou sans réponse, la figure fixe du livre
 *     (index.json, champ « impression ») le remplace, sinon un message.
 *
 * Chargement (template) :
 *   <link rel="stylesheet" href="{{ static_revealjs }}/plugin/photogra-widget/photogra-widget.css">
 *   <script src="{{ static_revealjs }}/plugin/photogra-widget/photogra-widget.js"></script>
 *   Reveal.initialize({ plugins: [ RevealMarkdown, ..., RevealPhotogra ] })   (après RevealMarkdown)
 */
(function (root) {
  "use strict";

  var DELAI_SECOURS = 15000;   // ms sans « ready » après le début du chargement
  var deck = null;
  var impression = false;
  var widgets = [];            // { bloc, iframe, url, nom, largeur, hMax, h, etat }
  var indicateur = null;
  var manifestes = {};         // url de index.json -> promesse du manifeste

  // keyCode des touches nommées (reveal.js lit event.keyCode)
  var CODES = {
    "Backspace": 8, "Tab": 9, "Enter": 13, "Escape": 27, " ": 32,
    "PageUp": 33, "PageDown": 34, "End": 35, "Home": 36,
    "ArrowLeft": 37, "ArrowUp": 38, "ArrowRight": 39, "ArrowDown": 40, "Delete": 46,
    ".": 190, ",": 188, "/": 191, "?": 191,
    "F1": 112, "F5": 116, "F11": 122
  };

  function keyCode(d) {
    if (CODES[d.key]) return CODES[d.key];
    if (/^[a-z0-9]$/i.test(d.key)) return d.key.toUpperCase().charCodeAt(0);
    return d.keyCode || 0;
  }

  // ------------------------------------------------------------ construction
  function construire(bloc) {
    var url;
    try { url = new URL(bloc.getAttribute("data-photogra"), location.href); }
    catch (e) { return; }
    url.searchParams.set("theme", "light");

    var w = {
      bloc: bloc,
      url: url,
      nom: url.searchParams.get("w") || "",
      largeur: parseFloat(bloc.getAttribute("data-width")) || 1000,
      hMax: parseFloat(bloc.getAttribute("data-height")) || 0,
      h: 0,
      etat: "attente"
    };
    bloc.classList.add("photogra-widget");
    bloc.innerHTML = "";

    var cadre = document.createElement("div");
    cadre.className = "photogra-cadre";
    var iframe = document.createElement("iframe");
    iframe.setAttribute("title", "Widget interactif : " + w.nom);
    iframe.setAttribute("scrolling", "no");
    iframe.style.width = w.largeur + "px";
    iframe.style.height = "400px";
    if (impression) {
      iframe.src = url.href;
    } else {
      iframe.setAttribute("data-src", url.href);   // chargé / déchargé par reveal.js
    }
    iframe.addEventListener("load", function () {
      armerSecours(w);
      if (impression || w.bloc.closest("section.present")) mesurer(w.bloc);
    });
    cadre.appendChild(iframe);
    bloc.appendChild(cadre);
    w.cadre = cadre;
    w.iframe = iframe;
    widgets.push(w);
    if (impression) armerSecours(w);
  }

  // ---------------------------------------------------------------- échelle
  function hauteurMax(w) {
    if (w.hMax) return w.hMax;
    var slide = w.bloc.closest("section");
    var hSlide = deck.getConfig().height;
    if (!slide) return hSlide;
    // position du bloc dans la slide, en px de slide (non mis à l'échelle)
    var y = 0, el = w.bloc;
    while (el && el !== slide) { y += el.offsetTop; el = el.offsetParent; }
    return Math.max(200, hSlide - y - 40);
  }

  function ajuster(w) {
    if (!w.h || w.etat === "secours") return;
    var dispo = w.bloc.clientWidth || w.largeur;
    var s = Math.min(dispo / w.largeur, hauteurMax(w) / w.h);
    w.iframe.style.height = w.h + "px";
    w.iframe.style.transform = "scale(" + s + ")";
    w.cadre.style.width = Math.round(w.largeur * s) + "px";
    w.cadre.style.height = Math.round(w.h * s) + "px";
  }

  // ---------------------------------------------------------------- secours
  function armerSecours(w) {
    clearTimeout(w.minuteur);
    if (w.etat === "pret" || w.etat === "secours") return;
    w.minuteur = setTimeout(function () { secours(w, "pas de réponse"); }, DELAI_SECOURS);
  }

  function manifeste(w) {
    var u = new URL("index.json", w.url).href;
    if (!manifestes[u]) {
      manifestes[u] = fetch(u).then(function (r) { return r.ok ? r.json() : []; })
        .catch(function () { return []; });
    }
    return manifestes[u];
  }

  function secours(w, raison) {
    if (w.etat === "pret" || w.etat === "secours") return;
    clearTimeout(w.minuteur);
    w.etat = "secours";
    majIndicateur();
    manifeste(w).then(function (liste) {
      var e = null;
      for (var i = 0; i < liste.length; i++) if (liste[i].nom === w.nom) e = liste[i];
      w.bloc.innerHTML = "";
      w.bloc.classList.add("photogra-secours");
      if (e && e.impression) {
        var img = document.createElement("img");
        img.src = new URL("../" + e.impression, w.url).href;
        img.alt = e.description || e.titre || w.nom;
        img.style.maxHeight = (hauteurMax(w) - 60) + "px";
        img.addEventListener("load", function () { deck.layout(); });
        w.bloc.appendChild(img);
        var credit = document.createElement("p");
        credit.className = "photogra-credit";
        credit.textContent = "Photogrammétrie, HEIG-VD, CC BY-SA 4.0 : figure " + (e.figure || "") +
          " (figure fixe, widget indisponible)";
        w.bloc.appendChild(credit);
      } else {
        var p = document.createElement("p");
        p.className = "photogra-message";
        p.appendChild(document.createTextNode("Widget « " + w.nom + " » indisponible (" + raison.replace(/[.\s]+$/, "") + "). "));
        var a = document.createElement("a");
        a.href = w.url.href; a.target = "_blank"; a.rel = "noopener";
        a.textContent = "Ouvrir dans le navigateur";
        p.appendChild(a);
        w.bloc.appendChild(p);
      }
      deck.layout();
    });
  }

  // -------------------------------------------------------------- messages
  // Le widget répond (prêt, ou au moins sa hauteur) : plus de secours.
  function vivant(w) {
    if (w.etat === "secours") return;
    clearTimeout(w.minuteur);
    if (w.etat !== "pret") { w.etat = "pret"; majIndicateur(); }
  }

  // Demande la hauteur aux iframes de la slide courante : Chrome peut avoir
  // suspendu le rendu d'une iframe chargée sur une slide encore masquée, et
  // son ResizeObserver ne signale alors plus rien.
  function mesurer(slide) {
    widgets.forEach(function (w) {
      if (slide && !slide.contains(w.bloc)) return;
      var cw = w.iframe.contentWindow;
      if (cw) cw.postMessage({ type: "photogra-widget-measure" }, "*");
    });
  }

  function widgetDe(source) {
    for (var i = 0; i < widgets.length; i++) {
      if (widgets[i].iframe.contentWindow === source) return widgets[i];
    }
    return null;
  }

  function surMessage(ev) {
    var d = ev.data;
    if (!d || typeof d.type !== "string" || d.type.indexOf("photogra-widget-") !== 0) return;
    var w = widgetDe(ev.source);
    if (!w) return;
    if (d.type === "photogra-widget-height") {
      vivant(w);
      if (d.height === w.h) return;
      w.h = d.height;
      ajuster(w);
      deck.layout();   // recentrage vertical de la slide (center: true)
    } else if (d.type === "photogra-widget-ready") {
      vivant(w);
    } else if (d.type === "photogra-widget-error") {
      secours(w, d.message || "erreur");
    } else if (d.type === "photogra-widget-key") {
      transmettreTouche(d);
    }
  }

  // Touche venue de l'iframe : rejouée sur le document, pour que reveal.js et
  // ses plugins (menu, chalkboard...) la traitent comme une frappe normale.
  function transmettreTouche(d) {
    var ev = new KeyboardEvent("keydown", {
      key: d.key, code: d.code, shiftKey: !!d.shiftKey, bubbles: true, cancelable: true
    });
    var kc = keyCode(d);
    Object.defineProperty(ev, "keyCode", { get: function () { return kc; } });
    Object.defineProperty(ev, "which", { get: function () { return kc; } });
    document.dispatchEvent(ev);
  }

  // ---------------------------------------------------- indicateur (print)
  function majIndicateur() {
    if (!indicateur) return;
    var prets = 0, secoursN = 0;
    widgets.forEach(function (w) {
      if (w.etat === "pret") prets++;
      else if (w.etat === "secours") secoursN++;
    });
    var fini = prets + secoursN === widgets.length;
    indicateur.className = "photogra-indicateur" + (fini ? (secoursN ? " is-secours" : " is-pret") : "");
    indicateur.textContent = "Widgets prêts : " + prets + " / " + widgets.length +
      (secoursN ? " (" + secoursN + " en figure fixe)" : "") + (fini ? ", imprimer" : "");
  }

  // ------------------------------------------------------------------ init
  root.RevealPhotogra = {
    id: "photogra-widget",
    init: function (reveal) {
      deck = reveal;
      impression = /print-pdf/i.test(location.search);
      var blocs = deck.getRevealElement().querySelectorAll(".slides [data-photogra]");
      Array.prototype.forEach.call(blocs, construire);
      if (!widgets.length) return;

      window.addEventListener("message", surMessage);
      deck.on("resize", function () { widgets.forEach(ajuster); });
      deck.on("slidechanged", function (ev) {
        // le focus resté dans une iframe capterait la télécommande
        var a = document.activeElement;
        if (a && a.tagName === "IFRAME") a.blur();
        widgets.forEach(ajuster);
        mesurer(ev.currentSlide);
      });
      deck.on("ready", function (ev) { mesurer(ev.currentSlide); });

      if (impression) {
        indicateur = document.createElement("div");
        document.body.appendChild(indicateur);
        majIndicateur();
      }
    }
  };
})(window);
