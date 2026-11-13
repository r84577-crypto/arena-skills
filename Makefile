# One entry point for every check, so CI and humans run identical commands.
# `make` == `make all`. Markdown lint needs Node; the rest is stdlib Python.

PYTHON ?= python3
MARKDOWNLINT_VERSION ?= 0.13.0

.PHONY: all check md fix skills links sources secrets envs tests hooks probe

all: md check

check: links skills tests sources secrets envs

links:
	$(PYTHON) scripts/check-links.py

skills:
	$(PYTHON) scripts/validate-skills.py

tests:
	$(PYTHON) scripts/test-check-links.py
	$(PYTHON) scripts/test-validate-skills.py
	$(PYTHON) scripts/test-check-skill-sources.py
	$(PYTHON) scripts/test-install-skills.py
	$(PYTHON) scripts/test-scan-secrets.py
	$(PYTHON) scripts/test-check-env-exposure.py

# --check-docs also compares the page's ranked table with the data file, because
# the page is what people read and nothing else noticed when the two disagreed.
sources:
	$(PYTHON) scripts/check-skill-sources.py --offline --check-docs

secrets:
	$(PYTHON) scripts/scan_secrets.py

# A secret behind NEXT_PUBLIC_/VITE_ ships to every browser and cannot be
# recalled. Run after a build with --bundle to check the real output too.
envs:
	$(PYTHON) scripts/check-env-exposure.py --bundle

# Live penetration checks. Needs the app running; see the script's docstring.
#   make probe BASE=http://127.0.0.1:3111
probe:
	$(PYTHON) scripts/security_probe.py --base $(BASE)

md:
	npx --yes markdownlint-cli2@$(MARKDOWNLINT_VERSION)

# Enable the pre-commit secret scan in this clone. Hooks are not cloned by git,
# so this is a one-time step per checkout, and it is never applied silently.
hooks:
	git config core.hooksPath .githooks
	chmod +x .githooks/pre-commit
	@echo "pre-commit hook enabled (core.hooksPath=.githooks)."
	@echo "It scans staged content only. Bypass with 'git commit --no-verify' and say why."

# Regenerate the manifest after adding or changing a skill.
fix:
	$(PYTHON) scripts/validate-skills.py --write-index
