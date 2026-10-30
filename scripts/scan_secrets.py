#!/usr/bin/env python3
"""Scan files for credential-shaped strings.

Shared by scripts/validate-skills.py and used directly in CI and in the pre-commit
hook, so a token in a skill's shell script is caught by the same rules as one in prose.

Two layers, with different confidence:

  known shape   provider prefixes (ghp_, npm_, AKIA, xox*, PEM blocks), the generic
                'secret = "..."' assignment. Hard evidence: these are errors.
  entropy       high-entropy strings that match no known provider, which is the only
                way to catch a custom token. Heuristic: errors in code and config,
                warnings in prose, because documentation legitimately quotes examples.

The filename is underscored rather than hyphenated on purpose: it is imported as a
module by the skills validator.

Usage:
    python3 scripts/scan_secrets.py                  # scan tracked files
    python3 scripts/scan_secrets.py path [path...]   # scan specific paths
    python3 scripts/scan_secrets.py --staged         # scan the index (pre-commit)
    python3 scripts/scan_secrets.py --quiet          # summary line only
    python3 scripts/scan_secrets.py --strict         # treat warnings as failures

Exit codes: 0 clean or warnings only, 1 findings.
"""

from __future__ import annotations

import fnmatch
import json
import math
import pathlib
import re
import subprocess
import sys
from collections import Counter
from typing import NamedTuple

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

ALLOWLIST = pathlib.Path("data") / "secret-allowlist.json"
ALLOWLIST_MIN_REASON = 15

# Prose legitimately quotes example credentials; code and config do not.
WARN_SUFFIXES = {".md", ".txt", ".rst", ".adoc"}

ENTROPY_RULE = "high-entropy string"
GENERIC_RULE = "generic bearer secret"
# Rules an allowlist entry may suppress. Provider prefixes are deliberately absent:
# `AKIA...` or `ghp_...` in a file is a live credential, not an example.
SUPPRESSIBLE = {ENTROPY_RULE, GENERIC_RULE}
# Two thresholds, because the evidence differs. A value assigned to a key named
# `token` is already suspicious; a bare quoted string has to look random on its own.
ENTROPY_MIN_ASSIGNED = 3.0
ENTROPY_MIN_BARE = 3.8
BARE_MIN = 24

# Values that are high-entropy but structurally never secrets.
NOT_A_SECRET = [
    re.compile(r"^(?:https?|git|ssh|ftp)://"),
    re.compile(r"^[0-9a-f]{32}$"),          # md5
    re.compile(r"^[0-9a-f]{40}$"),          # sha1, git short-ish
    re.compile(r"^[0-9a-f]{64}$"),          # sha256
    re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),  # uuid
    re.compile(r"^\d{4}-\d{2}-\d{2}"),      # dates
    re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$"),  # dotted names
]

QUOTED_RE = re.compile(r"""['"]([^'"\s]{24,})['"]""")
ASSIGNMENT_RE = re.compile(
    r"(?i)\b[\w.-]*(?:key|token|secret|passwd|password|credential|auth|apikey)[\w.-]*\s*[:=]\s*['\"]?([A-Za-z0-9/+_\-=]{20,})"
)

# A candidate must be made only of these characters. The moment a string contains
# a slash, a dot, a bracket or a bracket-like metacharacter it is a file path, a
# URL or a regular expression - all three are high-entropy and none is a secret.
TOKEN_CHARS_RE = re.compile(r"^[A-Za-z0-9+=_-]+$")


class Finding(NamedTuple):
    path: str
    rule: str
    excerpt: str
    severity: str  # "error" | "warn"


def looks_binary(path: pathlib.Path) -> bool:
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    try:
        with path.open("rb") as fh:
            return b"\0" in fh.read(8192)
    except OSError:
        return True


def entropy(value: str) -> float:
    """Shannon entropy in bits per character."""
    if not value:
        return 0.0
    counts = Counter(value)
    length = len(value)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def is_plausible_secret(value: str, min_length: int, minimum_entropy: float) -> bool:
    """Decide whether a candidate string is worth reporting.

    Deliberately conservative, and tuned against this repository: the first version
    of this function produced 65 findings, every one of them a file path, a URL or a
    regular expression. A scanner that cries wolf at commit time is a scanner people
    turn off with --no-verify, so precision beats recall here on purpose.
    """
    if len(value) < min_length:
        return False
    if not TOKEN_CHARS_RE.match(value):
        return False
    if any(pattern.match(value) for pattern in NOT_A_SECRET):
        return False
    if not (any(c.isalpha() for c in value) and any(c.isdigit() for c in value)):
        # No digit: an identifier or a word. No letter: a number. Neither is a key.
        return False
    if not (any(c.islower() for c in value) and any(c.isupper() for c in value)):
        # A 40-character lowercase run is an identifier or a hash, not a token.
        return False
    return entropy(value) >= minimum_entropy


def redact(value: str) -> str:
    """Never print a credential. Four characters identify it; the rest is a length."""
    if len(value) <= 8:
        return value[:2] + "…"
    return f"{value[:4]}… ({len(value)} chars)"


def find_entropy(text: str) -> list[str]:
    """Return raw high-entropy candidates, deduplicated, in document order."""
    seen: set[str] = set()
    found: list[str] = []
    candidates = [
        (ASSIGNMENT_RE, 20, ENTROPY_MIN_ASSIGNED),
        (QUOTED_RE, BARE_MIN, ENTROPY_MIN_BARE),
    ]
    for pattern, min_length, minimum_entropy in candidates:
        for match in pattern.finditer(text):
            value = (match.group(1) if match.groups() else match.group(0)).strip().strip("'\"")
            if value in seen or not is_plausible_secret(value, min_length, minimum_entropy):
                continue
            seen.add(value)
            found.append(value)
    return found


def find_secrets(text: str) -> list[tuple[str, str]]:
    """Return [(rule_name, redacted_excerpt), ...] for every match in text.

    Prefix rules plus the entropy layer. Kept as the stable entry point for the
    skills validator, which reports anything returned here as an error.
    """
    found: list[tuple[str, str]] = []
    for name, pattern in RULES:
        for match in pattern.finditer(text):
            found.append((name, redact(match.group(0))))
    for value in find_entropy(text):
        found.append((ENTROPY_RULE, redact(value)))
    return found


def load_allowlist(path: pathlib.Path) -> tuple[list[dict], list[str]]:
    """Read and validate the allowlist. Every entry needs a reason.

    An allowlist without reasons becomes the place findings go to be forgotten.
    Requiring prose makes each exception a reviewable argument.
    """
    if not path.exists():
        return [], []
    problems: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], [f"{path}: not valid JSON ({exc})"]

    entries = data.get("allow") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return [], [f"{path}: expected an object with an 'allow' list"]

    for i, entry in enumerate(entries):
        where = f"{path}: allow[{i}]"
        if not isinstance(entry, dict):
            problems.append(f"{where}: not an object")
            continue
        unknown = set(entry) - {"path", "rule", "reason"}
        if unknown:
            problems.append(f"{where}: unknown key(s) {sorted(unknown)}")
        if not str(entry.get("path", "")).strip():
            problems.append(f"{where}: missing 'path'")
        reason = str(entry.get("reason", "")).strip()
        if len(reason) < ALLOWLIST_MIN_REASON:
            problems.append(f"{where}: 'reason' must explain why ({ALLOWLIST_MIN_REASON}+ chars)")
    return entries, problems


def is_allowed(entry_path: str, rule: str, entries: list[dict]) -> bool:
    for entry in entries:
        if entry.get("rule") and entry["rule"] != rule:
            continue
        if fnmatch.fnmatch(entry_path, str(entry.get("path", ""))):
            return True
    return False


def severity_for(path: pathlib.Path) -> str:
    return "warn" if path.suffix.lower() in WARN_SUFFIXES else "error"


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


def staged_blobs(root: pathlib.Path) -> list[tuple[pathlib.Path, str]]:
    """Read staged content from the index, not the working tree.

    With `git add -p` the working tree and the index disagree; scanning the file on
    disk would miss what is about to be committed, which is the only thing that
    matters at commit time.
    """
    listing = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM", "-z"],
        cwd=root, capture_output=True, text=True,
    )
    blobs: list[tuple[pathlib.Path, str]] = []
    for name in listing.stdout.split("\0"):
        if not name.strip():
            continue
        path = root / name
        if SKIP_DIRS.intersection(path.parts) or looks_binary(path):
            continue
        show = subprocess.run(["git", "show", f":{name}"], cwd=root, capture_output=True)
        if show.returncode != 0:
            continue
        try:
            blobs.append((path, show.stdout.decode("utf-8")))
        except UnicodeDecodeError:
            continue
    return blobs


def scan(paths: list[pathlib.Path], root: pathlib.Path | None = None) -> list[Finding]:
    allow, _ = load_allowlist((root or pathlib.Path(".")) / ALLOWLIST)
    findings: list[Finding] = []
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
        findings.extend(_scan_text(path, text, root, allow))
    return findings


def _scan_text(path: pathlib.Path, text: str, root: pathlib.Path | None, allow: list[dict]) -> list[Finding]:
    try:
        rel = str(path.resolve().relative_to((root or pathlib.Path(".")).resolve()))
    except ValueError:
        rel = str(path)
    rel = rel.replace("\\", "/")
    severity = severity_for(path)

    findings: list[Finding] = []
    for rule, excerpt in find_secrets(text):
        # The heuristic rules are suppressible; a provider prefix is not. An
        # allowlist entry may explain "we quote an example", never "ignore ghp_".
        if rule in SUPPRESSIBLE and is_allowed(rel, rule, allow):
            continue
        findings.append(Finding(rel, rule, excerpt, severity))
    return findings


def main(argv: list[str]) -> int:
    quiet = "--quiet" in argv
    staged = "--staged" in argv
    strict = "--strict" in argv
    args = [a for a in argv[1:] if not a.startswith("--")]
    root = pathlib.Path(".").resolve()

    _, allow_problems = load_allowlist(root / ALLOWLIST)
    if allow_problems:
        for problem in allow_problems:
            print(f"ERROR    {problem}", file=sys.stderr)
        return 1

    if staged:
        blobs = staged_blobs(root)
        allow, _ = load_allowlist(root / ALLOWLIST)
        findings: list[Finding] = []
        for path, text in blobs:
            findings.extend(_scan_text(path, text, root, allow))
        scanned = len(blobs)
    else:
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
        findings = scan(paths, root)
        scanned = len(paths)

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warn"]

    for finding in findings:
        label = "FINDING" if finding.severity == "error" else "WARN   "
        stream = sys.stderr if finding.severity == "error" else sys.stdout
        print(f"{label}  {finding.path}: {finding.rule} ({finding.excerpt})", file=stream)

    if warnings and not errors:
        print(
            f"\n{len(warnings)} warning(s) in prose. Documentation may quote examples; "
            "confirm each by hand, or add an entry to data/secret-allowlist.json with a reason.",
            file=sys.stderr,
        )
    if errors:
        print(
            f"\n{len(errors)} possible credential(s). Remove them and rotate the token; "
            "rewriting history is not enough once it has been pushed.",
            file=sys.stderr,
        )
        return 1
    if strict and warnings:
        print("strict mode: failing on warnings", file=sys.stderr)
        return 1

    if not quiet:
        where = "staged file(s)" if staged else "file(s)"
        print(f"no credential-shaped strings in {scanned} {where}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
