#!/usr/bin/env python3
"""Negative tests for scripts/check-links.py.

Covers the two defects found by manual probing — indented code fences being
parsed as links, and broken images passing silently — plus the checks that must
keep working.

Usage:
    python3 scripts/test-check-links.py
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

SCRIPT = pathlib.Path(__file__).resolve().parent / "check-links.py"


def run(root: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=root, capture_output=True, text=True
    )


def case(name: str, files: dict[str, str], expect_fail: bool, expect_text: str = "") -> bool:
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        for rel, content in files.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

        result = run(root)
        output = result.stdout + result.stderr
        ok = (result.returncode != 0) if expect_fail else (result.returncode == 0)
        text_ok = expect_text.lower() in output.lower() if expect_text else True

        print(f"  [{'PASS' if ok and text_ok else 'FAIL'}] {name}")
        if not (ok and text_ok):
            print(f"        expected fail={expect_fail} text={expect_text!r} got exit={result.returncode}")
            for line in output.strip().splitlines()[:5]:
                print(f"        | {line}")
        return ok and text_ok


def main() -> int:
    print("check-links.py negative tests")
    results = []

    results.append(case(
        "indented fence inside a list item is not scanned for links",
        {"doc.md": "# Doc\n\n1. Step one:\n\n   ```python\n   see [not-real](ghost.md)\n   ```\n"},
        expect_fail=False,
    ))

    results.append(case(
        "top-level fence is not scanned for links",
        {"doc.md": "# Doc\n\n```python\nsee [not-real](ghost.md)\n```\n"},
        expect_fail=False,
    ))

    results.append(case(
        "link inside inline code is ignored",
        {"doc.md": "# Doc\n\nUse `[label](ghost.md)` as an example.\n"},
        expect_fail=False,
    ))

    results.append(case(
        "genuine dead link is reported",
        {"doc.md": "# Doc\n\nSee [the file](missing.md).\n"},
        expect_fail=True,
        expect_text="missing file",
    ))

    results.append(case(
        "missing image is reported",
        {"doc.md": "# Doc\n\n![diagram](missing-diagram.png)\n"},
        expect_fail=True,
        expect_text="missing image",
    ))

    results.append(case(
        "existing image passes",
        {"doc.md": "# Doc\n\n![diagram](diagram.png)\n", "diagram.png": "not-really-a-png"},
        expect_fail=False,
    ))

    results.append(case(
        "dead heading anchor is reported",
        {"doc.md": "# Doc\n\nSee [below](#no-such-heading).\n"},
        expect_fail=True,
        expect_text="dead anchor",
    ))

    results.append(case(
        "live heading anchor passes",
        {"doc.md": "# Doc\n\n## Real heading\n\nSee [below](#real-heading).\n"},
        expect_fail=False,
    ))

    results.append(case(
        "duplicate headings are reported",
        {"doc.md": "# Doc\n\n## Same\n\n## Same\n"},
        expect_fail=True,
        expect_text="duplicate heading",
    ))

    results.append(case(
        "link escaping the repository is reported",
        {"doc.md": "# Doc\n\nSee [outside](../../etc/passwd).\n"},
        expect_fail=True,
        expect_text="escapes the repository",
    ))

    results.append(case(
        "cross-file link and anchor resolve",
        {"a.md": "# A\n\nSee [b](b.md#target-heading).\n", "b.md": "# B\n\n## Target heading\n"},
        expect_fail=False,
    ))

    print()
    passed, total = sum(1 for r in results if r), len(results)
    print(f"{passed}/{total} cases behaved correctly")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
