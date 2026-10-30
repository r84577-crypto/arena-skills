#!/usr/bin/env python3
"""Tests for check-skill-sources.py.

The script has a dash in its name, so it cannot be imported by name; it is
loaded from its path instead and its DATA/DOCS constants are pointed at
throwaway fixtures. Nothing here touches the network.

    python3 scripts/test-check-skill-sources.py
"""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile

SCRIPT = pathlib.Path(__file__).resolve().parent / "check-skill-sources.py"

_spec = importlib.util.spec_from_file_location("check_skill_sources", SCRIPT)
module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module)

PASSED = 0
FAILED = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"PASS  {label}")
    else:
        FAILED += 1
        print(f"FAIL  {label}{': ' + detail if detail else ''}")


GOOD_DATA = {
    "snapshot": "2026-10-30",
    "repositories": [
        {
            "repo": "acme/one",
            "tier": "recommended",
            "category": "testing",
            "skills_distinct": 4,
            "stars": 1234,
            "license": "MIT",
            "last_push": "2026-10-29",
            "commits_90d": 7,
        },
        {
            "repo": "acme/two",
            "tier": "recommended-with-caveat",
            "category": "docs",
            "skills_distinct": 1,
            "stars": 90,
            "license": "Mixed: 2 Apache-2.0 + 1 proprietary",
            "last_push": "2026-10-01",
            "commits_90d": 100,
        },
    ],
    "avoid": [{"repo": "bad/repo", "reason": "No license, no commits, no tests"}],
}

GOOD_PAGE = """# Guide

> **Snapshot:** 2026-10-30. Numbers drift.

## Ranked shortlist

| # | Repository | Distinct skills | Stars | License | Last push | 90d commits |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | [`acme/one`](https://github.com/acme/one) | 4 | 1,234 | MIT | 2026-10-29 | 7 |
| 2 | [`acme/two`](https://github.com/acme/two) | 1 | 90 | Mixed | 2026-10-01 | 100+ |

`100+` means the query hit its pagination cap.
"""


def fixture(tmp: str, data: dict, page: str) -> tuple[dict, str]:
    """Write a data file and a page, point the module at them, return parsed page."""
    root = pathlib.Path(tmp)
    (root / "data").mkdir(exist_ok=True)
    (root / "docs").mkdir(exist_ok=True)
    data_path = root / "data" / "skill-sources.json"
    docs_path = root / "docs" / "skill-sources.md"
    data_path.write_text(json.dumps(data), encoding="utf-8")
    docs_path.write_text(page, encoding="utf-8")
    module.DATA = data_path
    module.DOCS = docs_path
    return data, page


def shape(data: dict) -> list[str]:
    problems = []
    for entry in data["repositories"]:
        problems.extend(module.validate_shape(entry))
    problems.extend(module.validate_avoid(data.get("avoid", [])))
    return problems


def main() -> int:
    # --- shape validation -------------------------------------------------
    check("accepts the reference data file", shape(GOOD_DATA) == [], str(shape(GOOD_DATA)))

    bad = copy.deepcopy(GOOD_DATA)
    bad["repositories"][0]["tier"] = "best"
    problems = shape(bad)
    check("rejects an unknown tier", any("tier" in p for p in problems), str(problems))

    bad = copy.deepcopy(GOOD_DATA)
    bad["repositories"][0]["last_push"] = "29/10/2026"
    problems = shape(bad)
    check("rejects a non-ISO date", any("YYYY-MM-DD" in p for p in problems), str(problems))

    bad = copy.deepcopy(GOOD_DATA)
    bad["repositories"][0]["stars"] = "many"
    problems = shape(bad)
    check("rejects a non-integer star count", any("stars" in p for p in problems), str(problems))

    bad = copy.deepcopy(GOOD_DATA)
    bad["repositories"][0]["repo"] = "just-a-name"
    problems = shape(bad)
    check("rejects an owner/name violation", any("owner/name" in p for p in problems), str(problems))

    bad = copy.deepcopy(GOOD_DATA)
    bad["repositories"][0]["skills_distinct"] = 0
    problems = shape(bad)
    check(
        "rejects zero distinct skills",
        any("positive integer" in p for p in problems),
        str(problems),
    )

    bad = copy.deepcopy(GOOD_DATA)
    del bad["repositories"][0]["license"]
    problems = shape(bad)
    check("reports missing required keys", any("missing keys" in p for p in problems), str(problems))

    # The avoid list was never inspected before, so these are the regressions
    # that matter most: a malformed entry used to pass silently.
    bad = copy.deepcopy(GOOD_DATA)
    bad["avoid"] = [{"repo": "bad/repo"}]
    problems = shape(bad)
    check("rejects an avoid entry without a reason", any("reason" in p for p in problems), str(problems))

    bad = copy.deepcopy(GOOD_DATA)
    bad["avoid"] = [{"repo": "bad/repo", "reason": "bad"}]
    problems = shape(bad)
    check("rejects a useless avoid reason", any("too short" in p for p in problems), str(problems))

    bad = copy.deepcopy(GOOD_DATA)
    bad["avoid"] = [{"repo": "bad", "reason": "No license, no commits, no tests"}]
    problems = shape(bad)
    check("rejects a malformed avoid repo", any("owner/name" in p for p in problems), str(problems))

    # --- page/data agreement ---------------------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        data, page = fixture(tmp, GOOD_DATA, GOOD_PAGE)
        check("page and data agree", module.check_docs(data, page) == [], str(module.check_docs(data, page)))

        drifted = GOOD_PAGE.replace("| 1,234 |", "| 1,235 |")
        problems = module.check_docs(data, drifted)
        check(
            "catches a star count that drifted in the page",
            any("stars" in p and "1,235" in p for p in problems),
            str(problems),
        )

        drifted = GOOD_PAGE.replace("| 4 | 1,234 |", "| 5 | 1,234 |")
        problems = module.check_docs(data, drifted)
        check(
            "catches a distinct-skill count that drifted",
            any("distinct skills" in p for p in problems),
            str(problems),
        )

        drifted = GOOD_PAGE.replace("| MIT | 2026-10-29 |", "| Apache-2.0 | 2026-10-29 |")
        problems = module.check_docs(data, drifted)
        check("catches a license that drifted", any("license" in p for p in problems), str(problems))

        drifted = GOOD_PAGE.replace("| 2026-10-29 | 7 |", "| 2026-10-30 | 7 |")
        problems = module.check_docs(data, drifted)
        check("catches a last-push date that drifted", any("last push" in p for p in problems), str(problems))

        drifted = GOOD_PAGE.replace("| 2026-10-01 | 100+ |", "| 2026-10-01 | 99 |")
        problems = module.check_docs(data, drifted)
        check("catches a commit count that drifted", any("90d commits" in p for p in problems), str(problems))

        drifted = GOOD_PAGE.replace("| 2 | [`acme/two`](https://github.com/acme/two) | 1 | 90 | Mixed | 2026-10-01 | 100+ |\n", "")
        problems = module.check_docs(data, drifted)
        check(
            "catches a row dropped from the page",
            any("missing from the page" in p for p in problems),
            str(problems),
        )

        # A row appended after the trailing paragraph is not part of the table
        # (parse_page stops at the first non-pipe line), so insert it in-table.
        extra = GOOD_PAGE.replace(
            "| 2 | [`acme/two`](https://github.com/acme/two) | 1 | 90 | Mixed | 2026-10-01 | 100+ |",
            "| 2 | [`acme/two`](https://github.com/acme/two) | 1 | 90 | Mixed | 2026-10-01 | 100+ |\n"
            "| 3 | [`acme/three`](https://github.com/acme/three) | 2 | 10 | MIT | 2026-10-30 | 1 |",
        )
        problems = module.check_docs(data, extra)
        check(
            "catches a row the data file does not know about",
            any("not in the data file" in p for p in problems),
            str(problems),
        )

        drifted = GOOD_PAGE.replace("**Snapshot:** 2026-10-30", "**Snapshot:** 2026-10-01")
        problems = module.check_docs(data, drifted)
        check("catches a stale snapshot date", any("snapshot date" in p for p in problems), str(problems))

        # 'Mixed: 14 Apache-2.0 + 4 proprietary' renders as 'Mixed'; the
        # comparator must normalise that rather than demand the full string.
        check(
            "normalises a mixed-license description",
            module._license("Mixed: 14 Apache-2.0 + 4 proprietary") == "Mixed",
        )
        check("renders 100+ at the pagination cap", module._commits(100) == "100+")
        check("renders a sub-cap commit count plainly", module._commits(99) == "99")
        check("thousands separator", module._cell(111806) == "111,806")

        # A page with no table at all must fail loudly, not pass vacuously.
        problems = module.check_docs(data, "# Guide\n\nNo table here.\n")
        check("fails when the page has no ranked table", len(problems) >= 2, str(problems))

    # --- end-to-end through main() ----------------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        fixture(tmp, GOOD_DATA, GOOD_PAGE)
        code = module.main(["check-skill-sources.py", "--offline", "--check-docs"])
        check("main() exits 0 on an agreeing pair", code == 0, f"exit {code}")

        module.DOCS.write_text(GOOD_PAGE.replace("| 1,234 |", "| 9,999 |"), encoding="utf-8")
        code = module.main(["check-skill-sources.py", "--offline", "--check-docs"])
        check("main() exits 1 on drift", code == 1, f"exit {code}")

        fixture(tmp, GOOD_DATA, GOOD_PAGE)
        module.DATA.write_text("{not json", encoding="utf-8")
        try:
            module.main(["check-skill-sources.py", "--offline"])
            check("main() rejects malformed JSON", False, "no exception raised")
        except json.JSONDecodeError:
            check("main() rejects malformed JSON", True)

        fixture(tmp, GOOD_DATA, GOOD_PAGE)
        module.DOCS.unlink()
        code = module.main(["check-skill-sources.py", "--offline", "--check-docs"])
        check("main() fails when the page is missing", code == 1, f"exit {code}")

        fixture(tmp, dict(GOOD_DATA, repositories=[]), GOOD_PAGE)
        code = module.main(["check-skill-sources.py", "--offline"])
        check("main() fails on an empty repository list", code == 1, f"exit {code}")

    print()
    if FAILED:
        print(f"{FAILED} case(s) failed, {PASSED} passed")
        return 1
    print(f"{PASSED}/{PASSED} cases behaved correctly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
