# Fichiers HEIG-VD pour revelation

Tout ce qui est propre aux cours HEIG-VD et que `revelation installreveal`
ne télécharge pas (il n'installe que le reveal.js officiel).

| Dossier | Contenu |
|---|---|
| `theme/` | `heig_ec+g.css` (thème des cours, `REVEAL_THEME = "heig_ec+g"`), `heig_ec+g-print.css`, `heig_ec+g_old.css` |
| `images/` | logos utilisés par les templates (`logo-heig-vd.svg`, `logo-{gte,ggt,master,igso,sgpf,…}`, `coin_BG.png`) |
| `plugin/` | plugins absents de reveal.js : `timetimer` (minuteur, voir plus bas), `title-footer`, `toc-progress` (chargés par `myPresentation.html`), `menu` (reveal.js-menu, Greg Denehy, MIT), `chalkboard` (reveal.js-plugins, Asvin Goel, MIT, utilisé par `presentation_sgpf.html`) |

## Installation

```bash
revelation installreveal        # si reveal.js n'est pas encore installé
heig/install.sh                 # liens symboliques vers ce dossier
```

`install.sh` crée, dans le reveal.js servi par revelation
(`revelation/static/revealjs`, qui peut lui-même être un lien), des liens
symboliques vers les fichiers de ce dossier. Une copie identique est
remplacée par un lien ; un fichier différent est d'abord sauvegardé en
`*.avant-heig`.

Conséquence : on modifie le thème **ici**, et le changement est versionné.

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
