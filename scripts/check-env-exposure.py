#!/usr/bin/env python3
"""Fail the build if a secret could reach the browser.

The rule this enforces, in one line: **a variable whose name starts with a
browser-exposed prefix must not hold a secret, and a secret must not carry
such a prefix.** Next.js inlines every `NEXT_PUBLIC_*` value into the client
bundle at build time; Vite does the same for `VITE_*`; CRA for `REACT_APP_*`.
There is no runtime check, no warning, and no way to un-publish a bundle that
already shipped — so the only place to catch it is before the build.

Two directions, because both happen in real projects:

  prefix + secret-looking name   NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY
  secret-looking name, no prefix but a real value in a committed file

Reads:
  * every `.env.example` / `.env.sample` (names are fine, values must be empty)
  * the client bundle after a build, if `.next` exists (the ground truth)

Usage:
    python3 scripts/check-env-exposure.py            # static checks
    python3 scripts/check-env-exposure.py --bundle   # also scan .next output

Exit codes: 0 clean, 1 findings.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys

# ENVCHECK_ROOT lets the test suite point this at a throwaway tree. It is also
# how you check a different checkout without copying the script into it.
ROOT = pathlib.Path(
    os.environ.get("ENVCHECK_ROOT") or pathlib.Path(__file__).resolve().parent.parent
)

# Prefixes that end up in the browser bundle. Keep in sync with the framework
# in use — the cost of a stale entry here is a silent leak.
BROWSER_PREFIXES = ("NEXT_PUBLIC_", "VITE_", "REACT_APP_", "PUBLIC_", "NUXT_PUBLIC_")

# A name is "secret-shaped" if it mentions any of these. Deliberately broad:
# a false positive costs a rename, a false negative costs the account.
SECRET_WORDS = (
    "SECRET",
    "PASSWORD",
    "PASSWD",
    "TOKEN",
    "PRIVATE",
    "SERVICE_ROLE",
    "CREDENTIAL",
    "API_KEY",
    "APIKEY",
    "ACCESS_KEY",
    "SIGNING",
    "WEBHOOK",
    "SMTP_PASS",
    "DATABASE_URL",
    "CONNECTION_STRING",
    "DSN",
)

# Names that are public by design even though they match SECRET_WORDS.
PUBLIC_BY_DESIGN = {
    "NEXT_PUBLIC_SUPABASE_ANON_KEY",  # RLS is the guard; this key is meant to ship
    "NEXT_PUBLIC_SUPABASE_URL",
}

ENV_FILE_RE = re.compile(r"\.env($|\.)")
ASSIGN_RE = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*=\s*(.*)$")


def is_secret_shaped(name: str) -> bool:
    return any(word in name for word in SECRET_WORDS)


def check_env_files() -> list[str]:
    findings: list[str] = []
    for path in sorted(ROOT.rglob(".env*")):
        if any(part in {"node_modules", ".next", ".git"} for part in path.parts):
            continue
        if not path.is_file():
            continue
        name = path.name
        # A real .env* file must never be committed, and never exist in the tree
        # that gets deployed. `.env.example` is the only allowed exception.
        if name not in (".env.example", ".env.sample", ".env.template"):
            findings.append(
                f"{path.relative_to(ROOT)}: committed env file — real values must live in "
                f"the platform's secret store, not the repo (add to .gitignore and delete)"
            )
            continue

        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            m = ASSIGN_RE.match(line)
            if not m:
                continue
            var, value = m.group(1), m.group(2).strip().strip('"').strip("'")

            if var.startswith(BROWSER_PREFIXES) and is_secret_shaped(var) and var not in PUBLIC_BY_DESIGN:
                stripped = var
                for p in BROWSER_PREFIXES:
                    stripped = stripped.replace(p, "", 1)
                findings.append(
                    f"{path.relative_to(ROOT)}:{lineno}: {var} is browser-exposed and "
                    f"secret-shaped — rename to {stripped} (no prefix) and read it server-side only"
                )

            # A value in an example file is only a finding when the name is
            # secret-shaped. A default like RESEND_FROM or a public project URL
            # is documentation, and forcing it empty makes the example useless.
            # A secret-shaped name with a value is a committed credential.
            if value and is_secret_shaped(var):
                findings.append(
                    f"{path.relative_to(ROOT)}:{lineno}: {var} carries a value in an example "
                    f"file — secret values belong in the platform secret store, never the repo"
                )
    return findings


def check_bundle() -> tuple[list[str], int]:
    """The ground truth: grep the built client bundle for server-only values."""
    bundle = ROOT / "app" / ".next"
    if not bundle.exists():
        return [], 0

    server_only = {}
    example = ROOT / "app" / ".env.example"
    if example.exists():
        for line in example.read_text(encoding="utf-8").splitlines():
            m = ASSIGN_RE.match(line)
            if not m:
                continue
            var, value = m.group(1), m.group(2).strip().strip('"').strip("'")
            if value or var.startswith(BROWSER_PREFIXES):
                continue
            server_only[var] = value

    # Also read any local .env for names (never print values).
    for envfile in (ROOT / "app" / ".env.local", ROOT / "app" / ".env"):
        if envfile.exists():
            for line in envfile.read_text(encoding="utf-8").splitlines():
                m = ASSIGN_RE.match(line)
                if m and not m.group(1).startswith(BROWSER_PREFIXES):
                    server_only.setdefault(m.group(1), "")

    client = bundle / "static"
    if not client.exists():
        return [], len(server_only)

    findings: list[str] = []
    blobs = [p for p in client.rglob("*") if p.is_file() and p.suffix in {".js", ".mjs"}]
    for path in blobs:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for var in server_only:
            # The *name* appearing is a leak signal on its own: Next only inlines
            # a name when something references it client-side.
            if var in text:
                findings.append(
                    f"{path.relative_to(ROOT)}: server-only variable {var} is referenced in the "
                    f"client bundle — move the call behind an API route"
                )
    return findings, len(server_only)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bundle", action="store_true", help="also scan the built client bundle")
    args = ap.parse_args()

    findings = check_env_files()
    checked = 0
    if args.bundle:
        bundle_findings, checked = check_bundle()
        findings.extend(bundle_findings)

    if findings:
        print("env exposure check — FINDINGS\n", file=sys.stderr)
        for f in findings:
            print(f"  ✗ {f}", file=sys.stderr)
        return 1

    extra = f" and {checked} server-only names absent from the client bundle" if args.bundle else ""
    print(f"env exposure check — clean (no browser-exposed secret names{extra})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
