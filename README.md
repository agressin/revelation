# Revelation (fork HEIG-VD)

Outil Python qui sert des présentations [reveal.js](https://revealjs.com/)
5.2.1 depuis des fichiers markdown, en local (aucune dépendance réseau en
salle ni pour l'impression PDF). Ce fork adapte
[revelation](https://github.com/humrochagf/revelation) aux besoins des
cours HEIG-VD : thème `heig_ec+g`, logos des filières, minuteur, tableau
blanc, pied de page avec le titre, menu avec un onglet « Outils », et une
configuration de présentation en TOML plutôt qu'en Python exécutable.

## Installation

Prérequis : [uv](https://docs.astral.sh/uv/).

```bash
heig/bootstrap.sh      # ou : make bootstrap
```

Ce script télécharge reveal.js 5.2.1, reveal.js-menu 2.1.0 et MathJax 2.7.9
depuis npm (sommes de contrôle vérifiées), puis relie les fichiers HEIG
(`heig/`) dans `revelation/static/revealjs/` par des liens symboliques.
Le résultat (non versionné, reconstruit en une commande) sert ensuite
toutes les présentations sans accès réseau. À relancer après une mise à
jour du dépôt ou sur une nouvelle machine.

## Lancement

```bash
uv run --no-project --with-requirements ~/Dev/Reveal/revelation/requirements.txt \
    ~/Dev/Reveal/revelation/revelation.py start -h localhost -p 4000 --no-browser chemin/vers/presentation
```

- `--no-browser` : ne pas ouvrir le navigateur automatiquement (utile en test).
- `--debug` : active le débogueur werkzeug (jamais en dehors d'un poste de travail de confiance).
- `--config`, `--media`, `--theme`, `--style-override-file` : surcharges ponctuelles (voir `revelation.py start --help`).

Autres commandes : `mkpresentation NOM` (crée un dossier de présentation),
`mkstatic DOSSIER` (export HTML statique), `installreveal` /
`installrevealplugin` (téléchargement reveal.js, utilisés en interne par
`heig/bootstrap.sh`), `convertconfig config.py` (migration vers TOML).

## Structure d'un dossier de présentation

```
presentation/
├── slides.md       # un ou plusieurs fichiers *.md (chargés par ordre alphabétique)
├── config.toml     # métadonnées, thème, licence, options reveal.js
└── media/          # images et fichiers référencés par ![](media/...)
```

`config.toml` est le format recommandé (pur, pas de code exécuté). Un
`config.py` existe encore pour compatibilité (exécution sandboxée, clés
restreintes) mais reste déconseillé ; `revelation convertconfig config.py`
le convertit en TOML. Voir `example_slides/config.toml` pour un exemple
commenté de toutes les clés reconnues (`reveal_meta`, `reveal_theme`,
`reveal_theme_logo`, `reveal_licence`, `reveal_template`,
`reveal_slide_separator`, `reveal_vertical_slide_separator`,
`reveal_config`).

## Conventions HEIG-VD

Thème, logos, minuteur (balise `<timetimer>`), tableau blanc (chalkboard),
menu (onglet « Outils »), zoom (Alt+clic) et recherche (Ctrl+Maj+F),
tableaux (`tab-zebre`, `tab-grille`), slides `corrige` masquées à
l'impression : voir [`heig/README.md`](heig/README.md). La syntaxe des
slides (séparateurs `---`/`--`, mises en page `<row>`/`<column2>`, notes
présentateur, MathJax) est documentée dans le `CLAUDE.md` à la racine des
dépôts de cours.

## Impression PDF

1. Lancer la présentation, ouvrir `http://localhost:4000/?print-pdf`.
2. Imprimer depuis le navigateur (Ctrl+P / Cmd+P), destination « Enregistrer
   en PDF », mise en page Paysage, marges Aucune, graphiques d'arrière-plan
   activés.

## Tests

```bash
make test      # BROWSER=true uv run --group dev pytest
```

## Projet d'origine

Fork de [humrochagf/revelation](https://github.com/humrochagf/revelation)
par Humberto Rocha, sous licence MIT (voir `LICENSE`).
