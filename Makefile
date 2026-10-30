# One entry point for every check, so CI and humans run identical commands.
# `make` == `make all`. Markdown lint needs Node; the rest is stdlib Python.

PYTHON ?= python3
MARKDOWNLINT_VERSION ?= 0.13.0

.PHONY: all check md fix skills links sources secrets tests

all: md check

check: links skills tests sources secrets

links:
	$(PYTHON) scripts/check-links.py

skills:
	$(PYTHON) scripts/validate-skills.py

tests:
	$(PYTHON) scripts/test-check-links.py
	$(PYTHON) scripts/test-validate-skills.py

sources:
	$(PYTHON) scripts/check-skill-sources.py --offline

secrets:
	$(PYTHON) scripts/scan_secrets.py

md:
	npx --yes markdownlint-cli2@$(MARKDOWNLINT_VERSION)

# Regenerate the manifest after adding or changing a skill.
fix:
	$(PYTHON) scripts/validate-skills.py --write-index
