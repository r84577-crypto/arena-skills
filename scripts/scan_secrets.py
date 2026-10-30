#!/usr/bin/env python3
"""Scan files for credential-shaped strings.

Shared by scripts/validate-skills.py and used directly in CI, so a token in a
skill's shell script is caught by the same rules as one in prose.

The filename is underscored rather than hyphenated on purpose: it is imported as
a module by the skills validator.

Usage:
    python3 scripts/scan_secrets.py                 # scan tracked files in the repo
    python3 scripts/scan_secrets.py path [path...]  # scan specific paths
    python3 scripts/scan_secrets.py --quiet         # exit code only

Exit codes: 0 clean, 1 findings.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

# Each rule is (name, compiled pattern). Patterns are deliberately narrow: this
# is a backstop for accidentally committed credentials, not a general DLP engine.
RULES: list[tuple[str, re.Pattern[str]]] = [
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("GitHub fine-grained token", re.compile(r"github_pat_[A-Za-z0-9_]{30,}")),
    ("AWS credential", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Slack token", re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}")),
    ("Google API key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("npm token", re.compile(r"npm_[A-Za-z0-9]{36}")),
    ("generic bearer secret", re.compile(r"(?i)\b(?:secret|password|token)\s*[:=]\s*['\"][A-Za-z0-9/+_-]{32,}['\"]")),
]

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".cache", "dist", "build", ".venv"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz", ".woff", ".woff2"}
MAX_BYTES = 2 * 1024 * 1024


def looks_binary(path: pathlib.Path) -> bool:
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    try:
        with path.open("rb") as fh:
            return b"\0" in fh.read(8192)
    except OSError:
        return True


def find_secrets(text: str) -> list[tuple[str, str]]:
    """Return [(rule_name, redacted_excerpt), ...] for every match in text."""
    found: list[tuple[str, str]] = []
    for name, pattern in RULES:
        for match in pattern.finditer(text):
            value = match.group(0)
            found.append((name, value[:12] + "…" if len(value) > 12 else value))
    return found


def tracked_files(root: pathlib.Path) -> list[pathlib.Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True
        )
        return [root / line for line in result.stdout.splitlines() if line.strip()]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [
            p
            for p in sorted(root.rglob("*"))
            if p.is_file() and not SKIP_DIRS.intersection(p.parts)
        ]


def scan(paths: list[pathlib.Path]) -> list[str]:
    problems: list[str] = []
    for path in paths:
        if not path.is_file() or SKIP_DIRS.intersection(path.parts):
            continue
        if looks_binary(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        if len(text) > MAX_BYTES:
            continue
        for name, excerpt in find_secrets(text):
            problems.append(f"{path}: possible {name} ({excerpt})")
    return problems


def main(argv: list[str]) -> int:
    quiet = "--quiet" in argv
    args = [a for a in argv[1:] if not a.startswith("--")]
    root = pathlib.Path(".").resolve()

    if not args:
        paths = tracked_files(root)
    else:
        paths = []
        for arg in args:
            target = pathlib.Path(arg).resolve()
            if target.is_dir():
                paths.extend(tracked_files(target))
            else:
                paths.append(target)

    problems = scan(paths)
    if problems:
        for problem in problems:
            print(f"FINDING  {problem}", file=sys.stderr)
        print(
            f"\n{len(problems)} possible credential(s). Remove them and rotate the token; "
            "rewriting history is not enough once it has been pushed.",
            file=sys.stderr,
        )
        return 1

    if not quiet:
        print(f"no credential-shaped strings in {len(paths)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
