#!/usr/bin/env bash
# Installe les fichiers HEIG-VD (thème, logos, plugins) dans le reveal.js
# utilisé par revelation, sous forme de liens symboliques vers ce dossier.
#
# Usage :  heig/install.sh [dossier_revealjs]
#          défaut : revelation/static/revealjs (suit le lien s'il en est un)
#
# À relancer après `revelation installreveal` (qui ne connaît pas ces
# fichiers) ou sur une nouvelle machine. Idempotent.
#
# Les liens pointent vers ce dépôt : modifier le thème ici, c'est modifier
# ce que servent les présentations, et le changement est versionné.
set -euo pipefail

HEIG="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REVEALJS="${1:-$HEIG/../revelation/static/revealjs}"

if [ ! -d "$REVEALJS" ]; then
    echo "Dossier reveal.js introuvable : $REVEALJS" >&2
    echo "Lancer d'abord : revelation installreveal" >&2
    exit 1
fi
REVEALJS="$(cd "$REVEALJS" && pwd -P)"
echo "reveal.js : $REVEALJS"

identique() {   # même contenu (fichier ou dossier) ?
    if [ -d "$1" ]; then diff -rq "$1" "$2" >/dev/null 2>&1; else cmp -s "$1" "$2"; fi
}

lier() {   # lier <source dans heig> <cible dans reveal.js>
    local src="$1" dst="$2"
    mkdir -p "$(dirname "$dst")"
    if [ -e "$dst" ] && [ ! -L "$dst" ]; then
        if identique "$src" "$dst"; then
            rm -rf "$dst"                      # copie identique : remplacée
        else
            mv "$dst" "$dst.avant-heig"        # différent : sauvegardé
            echo "  sauvegardé : $dst.avant-heig"
        fi
    fi
    ln -sfn "$src" "$dst"
    echo "  $dst -> $src"
}

for f in "$HEIG"/theme/*.css;   do lier "$f" "$REVEALJS/theme/$(basename "$f")"; done
for f in "$HEIG"/images/*;      do lier "$f" "$REVEALJS/images/$(basename "$f")"; done
for d in "$HEIG"/plugin/*/;     do d="${d%/}"; lier "$d" "$REVEALJS/plugin/$(basename "$d")"; done

echo "Installation HEIG terminée."
