# Makefile : raccourcis. Tout passe par uv ; une seule source de dépendances
# (pyproject.toml + uv.lock), requirements.txt est exporté depuis le lock.

.PHONY: bootstrap
bootstrap: # reveal.js figé + menu + MathJax + fichiers HEIG (heig/bootstrap.sh)
	heig/bootstrap.sh

.PHONY: lock
lock: # régénère uv.lock puis requirements.txt (utilisé par la commande de lancement)
	uv lock
	uv export --no-dev --no-hashes --no-emit-project --format requirements-txt -o requirements.txt

.PHONY: test
test: # tests (le navigateur n'est pas ouvert)
	BROWSER=true uv run --group dev pytest

.PHONY: start
start: # lance la présentation du dossier courant : make start DIR=chemin
	uv run --no-project --with-requirements requirements.txt revelation.py start -h localhost $(DIR)
