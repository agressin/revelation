# Fichiers HEIG-VD pour revelation

Tout ce qui est propre aux cours HEIG-VD et que `revelation installreveal`
ne télécharge pas (il n'installe que le reveal.js officiel), plus le script
qui reconstruit l'environnement complet, **hors ligne** ensuite.

| Dossier | Contenu |
|---|---|
| `theme/` | `heig_ec+g.css` (thème des cours, `REVEAL_THEME = "heig_ec+g"`) |
| `images/` | logos utilisés par les templates (`logo-heig-vd.svg`, `logo-{gte,ggt,master,igso,sgpf,…}`, `coin_BG.png`), badges `cc/<licence>.png` |
| `plugin/` | plugins absents de reveal.js : `timetimer` (minuteur, voir plus bas), `sections` (repères de section, voir plus bas), `title-footer` (pied de page avec le titre, chargé par `myPresentation.html`), `toc-progress` (table des matières en pied de page ; conservé mais **non chargé** par `myPresentation.html` : son bandeau déborde et chevauche le menu, le badge CC et les flèches de navigation une fois combiné au thème `heig_ec+g`, cf. historique git), `chalkboard` (2.3.3, reveal.js-plugins 4.6.0, Asvin Goel, MIT : tableau blanc et annotations, chargé par `myPresentation.html`, sans bouton à l'écran ; menu onglet « Outils », touches C annoter, B tableau, Suppr effacer) |
| `plugin/leaflet/`, `plugin/chartjs/`, `plugin/chartjs-plugin-datalabels/`, `plugin/chartjs-adapter-date-fns/` | Leaflet 1.9.4, Chart.js 4.5.1 (+ plugins datalabels 2.2.0 et adaptateur de dates date-fns 3.0.0, build `.bundle` qui inclut date-fns), versions figées vendues en local pour les templates `presentation_{lidar,sgpf,veille}.html` (cartes et graphiques). Les tuiles de carte et le WMS `geo.admin.ch`/`rar-indg.heig-vd.ch` restent en ligne (intrinsèque), regroupés dans une variable `RESSOURCES_EN_LIGNE` en tête de script de chaque template. |

## Installation : `heig/bootstrap.sh`

```bash
heig/bootstrap.sh       # ou : make bootstrap
```

| Étape | Version figée | Où |
|---|---|---|
| reveal.js (paquet npm : dist + plugins officiels) | 5.2.1 | `revelation installreveal` |
| reveal.js-menu | 2.1.0 | `static/revealjs/plugin/menu` |
| MathJax 2 (sans `unpacked/`) | 2.7.9 | `static/revealjs/plugin/mathjax` |
| fichiers HEIG | ce dossier | `heig/install.sh` (liens symboliques) |

Chaque archive est vérifiée contre la somme `integrity` publiée par npm.
`revelation/static/` reste hors de git : il se reconstruit en une commande.
Le template `myPresentation.html` ne charge plus rien depuis Internet
(reveal.js, plugins, MathJax et badge CC servis en local).

`revelation start` ne télécharge plus rien tout seul : si reveal.js est
absent, il s'arrête avec un message qui renvoie à ce script.

`install.sh` seul suffit pour relier les fichiers HEIG après une
modification de ce dossier. Une copie identique est remplacée par un lien ;
un fichier différent est d'abord sauvegardé en `*.avant-heig`. On modifie
donc le thème **ici**, et le changement est versionné.

## Conventions du thème `heig_ec+g`

- Tableaux : style « sobre » par défaut (en-tête souligné teal, lignes grises
  fines). Variantes sur la slide (`<!-- .slide: class="tab-zebre" -->`) ou
  autour d'un tableau (`<div class="tab-zebre">`, lignes vides autour) :
  `tab-zebre` (en-tête teal plein, lignes alternées), `tab-grille`
  (quadrillage léger), et le modificateur `compact` (combinable).
- `<div class="text-left">` : équivalent de l'historique `id="text-align-left"`.

- `<!-- .slide: class="corrige" -->` : la slide reste visible en projection
  mais est masquée à l'impression (`?print-pdf`), pour distribuer un PDF des
  énoncés sans les corrigés. Règle dans le bloc `@media print` du thème.

## Minuteur : balise `<timetimer>`

```html
<timetimer time="5min"></timetimer>
<timetimer time="90s" title="Concept test" sound="off"></timetimer>
```

- `time` : `5min`, `5 min`, `90s`, `1h`, `2:30` (mm:ss) ou `5` (minutes)
- `title` : texte du bandeau (optionnel, défaut : la durée)
- `sound` : `off` pour couper les trois bips de fin (optionnel)

La balise devient un bouton dans la slide. Un clic ouvre un petit panneau
flottant, déplaçable par son bandeau et posé hors des slides (il reste
affiché quand on change de slide) : disque rouge qui se vide, temps restant,
pause / reprise, remise à zéro, plein écran, fermer. Un seul minuteur à la
fois. À l'impression, le panneau est masqué et le bouton reste comme repère.

Fermer la balise (`</timetimer>`) : une balise non fermée fonctionne (le
contenu qui suit est conservé), mais c'est un rattrapage.

## Repères de section : plugin `sections`

Une section = un bloc entre deux `---` (slide horizontale et sa pile).

- **Pied de page** : « titre du cours · section en cours » (la slide de
  titre garde le pied de page d'origine).
- **Barre de progression** : la barre de reveal.js est découpée en un
  segment par section, avec une graduation à chaque frontière ; au survol le
  segment s'épaissit et affiche le nom de la section ; un clic y amène.

Nom d'une section : l'attribut `data-section` s'il est posé sur une de ses
slides, sinon son premier titre (h1 à h3). Pour un nom court :

```markdown
---

<!-- .slide: data-section="DBSCAN" -->
```

## Lancement

```bash
uv run --no-project --with-requirements ~/Dev/Reveal/revelation/requirements.txt \
    ~/Dev/Reveal/revelation/revelation.py start -h localhost
```
