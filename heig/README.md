# Fichiers HEIG-VD pour revelation

Tout ce qui est propre aux cours HEIG-VD et que `revelation installreveal`
ne télécharge pas (il n'installe que le reveal.js officiel), plus le script
qui reconstruit l'environnement complet, **hors ligne** ensuite.

| Dossier | Contenu |
|---|---|
| `theme/` | `heig_ec+g.css` (thème des cours, `REVEAL_THEME = "heig_ec+g"`), `heig_ec+g-print.css`, `heig_ec+g_old.css` |
| `images/` | logos utilisés par les templates (`logo-heig-vd.svg`, `logo-{gte,ggt,master,igso,sgpf,…}`, `coin_BG.png`), badges `cc/<licence>.png` |
| `plugin/` | plugins absents de reveal.js : `timetimer` (minuteur, voir plus bas), `title-footer`, `toc-progress` (chargés par `myPresentation.html`), `chalkboard` (reveal.js-plugins, Asvin Goel, MIT, utilisé par `presentation_sgpf.html`) |

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

## Lancement

```bash
uv run --no-project --with-requirements ~/Dev/Reveal/revelation/requirements.txt \
    ~/Dev/Reveal/revelation/revelation.py start -h localhost
```
