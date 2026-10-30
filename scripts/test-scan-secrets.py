#!/usr/bin/env python3
"""Tests for scripts/scan_secrets.py.

Every case below exists because of a specific failure. The largest group guards
the opposite risk of the scanner itself: the first entropy implementation produced
65 findings on this repository, all of them file paths, URLs and regular
expressions. A scanner that cries wolf gets bypassed with --no-verify, so precision
is a tested property here, not a preference.

    python3 scripts/test-scan-secrets.py
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile

SCRIPT = pathlib.Path(__file__).resolve().parent / "scan_secrets.py"

_spec = importlib.util.spec_from_file_location("scan_secrets", SCRIPT)
module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module)

PASSED = 0
FAILED = 0

# A random-looking 32-character token. Not a real credential.
#
# Composed from fragments rather than written as one literal: this file is scanned
# by its own subject, and allowlisting an entire test file would create a permanent
# blind spot where a real token could hide later. The scanner sees no contiguous
# credential here; the fixtures it writes at runtime contain one, which is the point.
TOKEN = "9fK2mQ7xL4pR" + "8vT1nB6wY3zA0cD5eH2j"
SHA1 = "9f2c1ab34de56f7890ab12cd34ef5678901abcde"
GHP = "ghp_" + "A" * 36


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"PASS  {label}")
    else:
        FAILED += 1
        print(f"FAIL  {label}{': ' + detail if detail else ''}")


def make_repo(root: pathlib.Path, files: dict[str, str], stage: bool = True) -> pathlib.Path:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    if stage:
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    return root


def run(root: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=root, capture_output=True, text=True,
    )


def main() -> int:
    # --- unit level -------------------------------------------------------
    check("entropy of a repeated string is zero", module.entropy("aaaaaaaa") == 0.0)
    check("entropy of random text is high", module.entropy(TOKEN) >= 3.8, f"{module.entropy(TOKEN):.2f}")
    check("a random token is plausible", module.is_plausible_secret(TOKEN, 24, 3.8))
    check("a sha1 hash is not treated as a secret", not module.is_plausible_secret(SHA1, 24, 3.0))
    check("a file path is not a secret", not module.is_plausible_secret("scripts/check-links.py", 20, 3.0))
    check("a regex is not a secret", not module.is_plausible_secret(r"^[a-z0-9_-]{3,}$", 20, 3.0))
    check("an all-lowercase run is not a secret", not module.is_plausible_secret("abcdefghijklmnopqrstuvwxyz012345", 24, 3.0))
    check("redaction keeps four characters", module.redact(TOKEN).startswith(TOKEN[:4]))
    check("redaction states the length", str(len(TOKEN)) in module.redact(TOKEN))
    check("redaction never contains the full token", TOKEN not in module.redact(TOKEN))

    # --- error vs warning by file type ------------------------------------
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(pathlib.Path(td) / "code", {"leak.sh": f'API_TOKEN="{TOKEN}"\n'})
        result = run(root)
        check("token in a shell script is an error", result.returncode == 1, f"exit {result.returncode}")
        check("the error names the file", "leak.sh" in result.stderr, result.stderr)
        check("the output is redacted", TOKEN not in result.stdout + result.stderr)

        root = make_repo(pathlib.Path(td) / "prose", {"notes.md": f'Example: token = "{TOKEN}"\n'})
        result = run(root)
        check("token in prose is a warning, not a failure", result.returncode == 0, f"exit {result.returncode}")
        check("the warning is still shown", "WARN" in result.stdout, result.stdout)
        result = run(root, "--strict")
        check("--strict turns the warning into a failure", result.returncode == 1, f"exit {result.returncode}")

    # --- provider prefixes are not suppressible ---------------------------
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(pathlib.Path(td) / "ghp", {"leak.sh": f"export GITHUB_TOKEN={GHP}\n"})
        (root / "data").mkdir()
        (root / "data" / "secret-allowlist.json").write_text(
            '{"allow": [{"path": "leak.sh", "rule": "GitHub token", '
            '"reason": "attempting to suppress a live provider token"}]}',
            encoding="utf-8",
        )
        result = run(root)
        check(
            "a provider prefix cannot be allowlisted away",
            result.returncode == 1,
            f"exit {result.returncode}: {result.stdout}{result.stderr}",
        )

    # --- allowlist ---------------------------------------------------------
    with tempfile.TemporaryDirectory() as td:
        root = make_repo(pathlib.Path(td) / "allow", {"notes.md": f'token = "{TOKEN}"\n'})
        (root / "data").mkdir()
        allow = root / "data" / "secret-allowlist.json"

        allow.write_text(
            '{"allow": [{"path": "notes.md", "rule": "high-entropy string", '
            '"reason": "documented example, not a live credential"}]}',
            encoding="utf-8",
        )
        result = run(root)
        check(
            "an allowlist entry suppresses the named rule",
            "high-entropy" not in result.stdout,
            f"stdout: {result.stdout}",
        )
        check(
            "an allowlist entry is rule-specific: the other rule still warns",
            "generic bearer secret" in result.stdout,
            f"stdout: {result.stdout}",
        )

        allow.write_text(
            '{"allow": [{"path": "notes.md", "rule": "high-entropy string", '
            '"reason": "documented example, not a live credential"}, '
            '{"path": "notes.md", "rule": "generic bearer secret", '
            '"reason": "the same documented example, spelled out"}]}',
            encoding="utf-8",
        )
        result = run(root, "--strict")
        check(
            "allowlisting both rules passes even under --strict",
            result.returncode == 0,
            f"exit {result.returncode}: {result.stdout}",
        )

        allow.write_text('{"allow": [{"path": "notes.md", "reason": "short"}]}', encoding="utf-8")
        result = run(root)
        check("a reason shorter than 15 characters is rejected", result.returncode == 1, f"exit {result.returncode}")

        allow.write_text('{"allow": [{"path": "notes.md", "reason": "a long enough reason here", "extra": 1}]}',
                         encoding="utf-8")
        result = run(root)
        check("an unknown allowlist key is rejected", result.returncode == 1, f"exit {result.returncode}")

        allow.write_text("{not json", encoding="utf-8")
        result = run(root)
        check("malformed allowlist JSON is rejected", result.returncode == 1, f"exit {result.returncode}")

    # --- staged mode reads the index, not the working tree -----------------
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td) / "staged"
        make_repo(root, {"app.py": f'TOKEN = "{TOKEN}"\n'})
        # Now clean the working tree without touching the index: what is about to be
        # committed still contains the token.
        (root / "app.py").write_text('TOKEN = "clean"\n', encoding="utf-8")

        result = run(root)
        check("a worktree scan misses the staged-only token", result.returncode == 0, f"exit {result.returncode}")

        result = run(root, "--staged")
        check("the staged scan catches it", result.returncode == 1, f"exit {result.returncode}")
        check("the staged finding names the path", "app.py" in result.stderr, result.stderr)

        subprocess.run(["git", "checkout", "--", "app.py"], cwd=root, check=True)
        (root / "app.py").write_text('TOKEN = "clean"\n', encoding="utf-8")
        subprocess.run(["git", "add", "app.py"], cwd=root, check=True)
        result = run(root, "--staged")
        check("a clean index passes", result.returncode == 0, f"exit {result.returncode}")

    # --- this repository must stay clean ----------------------------------
    repo = SCRIPT.parent.parent
    result = run(repo)
    check(
        "this repository has no findings",
        result.returncode == 0,
        f"exit {result.returncode}: {(result.stdout + result.stderr)[:300]}",
    )
    check(
        "this repository has no warnings either",
        "WARN" not in result.stdout,
        result.stdout[:300],
    )

    # --- the hook is wired -------------------------------------------------
    hook = repo / ".githooks" / "pre-commit"
    check("the pre-commit hook exists", hook.is_file())
    check("the hook is executable", os.access(hook, os.X_OK))
    hook_text = hook.read_text(encoding="utf-8") if hook.is_file() else ""
    check("the hook runs the staged scan", "--staged" in hook_text)
    check("the hook documents the bypass", "--no-verify" in hook_text)

    print()
    if FAILED:
        print(f"{FAILED} case(s) failed, {PASSED} passed")
        return 1
    print(f"{PASSED}/{PASSED} cases behaved correctly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
