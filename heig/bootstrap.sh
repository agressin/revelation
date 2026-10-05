#!/usr/bin/env bash
# Reconstruit l'environnement complet servi aux cours, hors ligne ensuite :
#
#   1. reveal.js  (version figée, paquet npm vérifié)  -> revelation installreveal
#   2. reveal.js-menu 2.1.0                            -> static/revealjs/plugin/menu
#   3. MathJax 2.7.9 (sans le dossier unpacked/)       -> static/revealjs/plugin/mathjax
#   4. fichiers HEIG (thème, logos, plugins locaux)    -> heig/install.sh
#
# Usage : heig/bootstrap.sh          (depuis n'importe où)
# Prérequis : uv, curl, tar, openssl.
# Après exécution, aucune présentation ne dépend plus d'Internet.
set -euo pipefail

HEIG="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RACINE="$(cd "$HEIG/.." && pwd)"
REVEALJS="$RACINE/revelation/static/revealjs"

# nom, version, integrity npm, dossier cible dans static/revealjs
PAQUETS=(
  "reveal.js-menu|2.1.0|sha512-35zp4fHSMyWd15+3CvQ8LrpS+4Gj2qvlkxX3lo5LpITDe6ZkA4A9y1E5fE63YlQl5fp7W1mNgNJr4kCU0s14lA==|plugin/menu"
  "mathjax|2.7.9|sha512-NOGEDTIM9+MrsqnjPEjVGNx4q0GQxqm61yQwSK+/5S59i26wId5IC5gNu9/bu8+CCVl5p9G2IHcAl/wJa+5+BQ==|plugin/mathjax"
)

echo "== 1. reveal.js"
uv run --no-project --with-requirements "$RACINE/requirements.txt" \
    "$RACINE/revelation.py" installreveal

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
for p in "${PAQUETS[@]}"; do
  IFS="|" read -r nom version integrity cible <<< "$p"
  echo "== $nom $version"
  tgz="$TMP/$nom.tgz"
  curl -fsSL -o "$tgz" "https://registry.npmjs.org/$nom/-/$nom-$version.tgz"
  obtenu="sha512-$(openssl dgst -sha512 -binary "$tgz" | openssl base64 -A)"
  if [ "$obtenu" != "$integrity" ]; then
    echo "Somme de contrôle incorrecte pour $nom $version" >&2; exit 1
  fi
  rm -rf "$TMP/package"
  tar -xzf "$tgz" -C "$TMP"
  rm -rf "$TMP/package/unpacked" "$TMP/package/test"     # MathJax : sources dupliquées
  dst="$REVEALJS/$cible"
  [ -L "$dst" ] && rm "$dst"                               # ancien lien vers heig/
  rm -rf "$dst"; mkdir -p "$(dirname "$dst")"
  mv "$TMP/package" "$dst"
  echo "$nom $version" > "$dst/VERSION.heig"
done

echo "== 4. fichiers HEIG"
"$HEIG/install.sh" "$REVEALJS"

echo "Environnement prêt : $REVEALJS"
cat "$REVEALJS/VERSION"
