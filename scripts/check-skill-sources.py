#!/usr/bin/env python3
"""Verify the repositories listed in data/skill-sources.json still exist and are alive.

Checks each repository against the GitHub API and reports:

  FAIL    repository is missing, renamed, or archived (exit 1)
  WARN    no push in 120 days, or the license changed since the snapshot (exit 0)
  OK      reachable, not archived, recently active

Usage:
    python3 scripts/check-skill-sources.py [--strict] [--offline] [--check-docs]

  --strict       treat warnings as failures
  --offline      skip network entirely (validates the JSON shape only)
  --check-docs   compare the ranked table in docs/skill-sources.md against the JSON

Requires the `gh` CLI and a token in GH_TOKEN or GITHUB_TOKEN.
"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "skill-sources.json"
DOCS = ROOT / "docs" / "skill-sources.md"
STALE_DAYS = 120
REQUIRED_KEYS = {"repo", "tier", "skills_distinct", "license", "last_push"}
TIERS = {"recommended", "recommended-with-caveat"}
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def gh(path: str) -> dict | None:
    env = dict(os.environ)
    token = env.get("GH_TOKEN") or env.get("GITHUB_TOKEN")
    if token:
        env["GH_TOKEN"] = token
    result = subprocess.run(
        ["gh", "api", path], capture_output=True, text=True, env=env
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def days_since(date_str: str) -> int:
    try:
        d = datetime.datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return 10_000
    return (datetime.date.today() - d).days


def validate_shape(entry: dict) -> list[str]:
    problems: list[str] = []
    missing = REQUIRED_KEYS - entry.keys()
    if missing:
        return [f"missing keys {sorted(missing)}"]

    if not isinstance(entry["skills_distinct"], int) or entry["skills_distinct"] < 1:
        problems.append("skills_distinct must be a positive integer")
    if entry["tier"] not in TIERS:
        problems.append(f"tier {entry['tier']!r} is not one of {sorted(TIERS)}")
    if not REPO_RE.match(str(entry["repo"])):
        problems.append(f"repo {entry['repo']!r} is not owner/name")
    if not DATE_RE.match(str(entry["last_push"])):
        problems.append(f"last_push {entry['last_push']!r} is not YYYY-MM-DD")
    if "stars" in entry and not isinstance(entry["stars"], int):
        problems.append("stars must be an integer")
    if "commits_90d" in entry and not isinstance(entry["commits_90d"], int):
        problems.append("commits_90d must be an integer")
    return problems


def validate_avoid(entries: list[dict]) -> list[str]:
    """The avoid list was previously never inspected, so it could rot silently."""
    problems: list[str] = []
    for entry in entries:
        missing = {"repo", "reason"} - entry.keys()
        if missing:
            problems.append(f"avoid entry {entry.get('repo', '<unnamed>')}: missing {sorted(missing)}")
            continue
        if not REPO_RE.match(str(entry["repo"])):
            problems.append(f"avoid entry {entry['repo']!r} is not owner/name")
        if len(str(entry["reason"])) < 10:
            problems.append(f"avoid entry {entry['repo']}: reason is too short to be useful")
    return problems


TABLE_ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|(.+)$")
REPO_LINK_RE = re.compile(r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)")


def _cell(value) -> str:
    """Render a JSON field the way the page writes it."""
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _commits(value) -> str:
    # The page collapses 100+ to '100+' because the 90-day query paginates at 100.
    return "100+" if isinstance(value, int) and value >= 100 else str(value)


def _license(value: str) -> str:
    # 'Mixed: 14 Apache-2.0 + 4 proprietary' renders as 'Mixed' in the table.
    return value.split(":")[0].strip()


def parse_page(text: str) -> tuple[dict[str, list[str]], str | None]:
    """Pull the ranked shortlist table and snapshot date out of the page.

    Returns ({repo: cells}, snapshot). Cells are #, distinct, stars, license,
    last push, 90-day commits - in page order.
    """
    rows: dict[str, list[str]] = {}
    snapshot = None
    match = re.search(r"\*\*Snapshot:\*\*\s*(\d{4}-\d{2}-\d{2})", text)
    if match:
        snapshot = match.group(1)

    in_table = False
    for line in text.splitlines():
        if line.startswith("| # | Repository"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                break
            if set(line) <= set("|-: "):
                continue  # separator
            found = REPO_LINK_RE.search(line)
            if not found:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows[found.group(1)] = cells[1:]
    return rows, snapshot


def check_docs(data: dict, page_text: str) -> list[str]:
    """The page and the JSON are two renderings of one snapshot; compare them.

    The JSON is the source of truth (see its `note` field). Nothing used to
    compare them, so a corrected star count or a dropped repository could sit in
    one and not the other indefinitely - and the page is what people read.
    """
    problems: list[str] = []
    rows, snapshot = parse_page(page_text)

    expected_snapshot = str(data.get("snapshot", ""))
    if snapshot != expected_snapshot:
        problems.append(
            f"snapshot date: page says {snapshot!r}, data says {expected_snapshot!r}"
        )

    repos = data.get("repositories", [])
    listed = {entry["repo"] for entry in repos}

    for name in sorted(set(rows) - listed):
        problems.append(f"{name}: in the page's ranked table but not in the data file")
    for entry in repos:
        name = entry["repo"]
        if name not in rows:
            problems.append(f"{name}: in the data file but missing from the page's ranked table")
            continue
        cells = rows[name]
        if len(cells) < 6:
            problems.append(f"{name}: ranked row has {len(cells)} columns, expected 6")
            continue
        distinct, stars, license_, last_push, commits = cells[1:6]
        checks = [
            ("distinct skills", distinct, _cell(entry.get("skills_distinct"))),
            ("stars", stars, _cell(entry.get("stars", ""))),
            ("license", license_, _license(str(entry.get("license", "")))),
            ("last push", last_push, str(entry.get("last_push", ""))),
            ("90d commits", commits, _commits(entry.get("commits_90d"))),
        ]
        for label, page_value, data_value in checks:
            if page_value != data_value:
                problems.append(
                    f"{name}: {label} is {page_value!r} in the page, {data_value!r} in the data file"
                )
    return problems


def main(argv: list[str]) -> int:
    strict = "--strict" in argv
    offline = "--offline" in argv
    check_docs_flag = "--check-docs" in argv

    if not DATA.exists():
        print(f"error: {DATA} not found", file=sys.stderr)
        return 1
    data = json.loads(DATA.read_text(encoding="utf-8"))
    repos = data.get("repositories", [])
    if not repos:
        print("error: no repositories listed", file=sys.stderr)
        return 1

    shape_errors = []
    for entry in repos:
        for problem in validate_shape(entry):
            shape_errors.append(f"{entry.get('repo', '<unnamed>')}: {problem}")
    avoid_entries = data.get("avoid", [])
    shape_errors.extend(validate_avoid(avoid_entries))

    if shape_errors:
        print("data validation failed:", file=sys.stderr)
        for problem in shape_errors:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print(
        f"data file valid: {len(repos)} checked repositories, "
        f"{len(avoid_entries)} avoid entries, snapshot {data.get('snapshot')}"
    )
    doc_problems: list[str] = []
    if check_docs_flag:
        if not DOCS.exists():
            print(f"error: {DOCS} not found", file=sys.stderr)
            return 1
        doc_problems = check_docs(data, DOCS.read_text(encoding="utf-8"))
        if doc_problems:
            print("page and data file disagree:", file=sys.stderr)
            for problem in doc_problems:
                print(f"  - {problem}", file=sys.stderr)
            print(
                "  fix the data file first, then regenerate the page's ranked table",
                file=sys.stderr,
            )
            return 1
        print(f"docs/skill-sources.md ranked table matches the data file ({len(repos)} rows)")

    if offline:
        print("offline mode: skipping network checks")
        return 0

    failures: list[str] = []
    warnings: list[str] = []

    header = f"{'repository':44} {'status':8} {'stars':>7} {'last push':10} {'license':10} idle"
    print()
    print(header)
    print("-" * len(header))

    for entry in repos:
        repo = entry["repo"]
        tier = entry.get("tier", "recommended")
        meta = gh(f"repos/{repo}")

        if meta is None:
            status = "MISSING"
            line = f"{repo:44} {'MISSING':8} {'-':>7} {'-':10} {'-':10} -"
            (failures if tier != "avoid" else []).append(f"{repo}: not reachable (deleted or renamed)")
            print(line)
            continue

        archived = bool(meta.get("archived"))
        stars = meta.get("stargazers_count", 0)
        pushed = (meta.get("pushed_at") or "")[:10]
        lic = (meta.get("license") or {}).get("spdx_id") or "none"
        idle = days_since(pushed)

        status = "ARCHIVED" if archived else ("STALE" if idle > STALE_DAYS else "OK")
        print(f"{repo:44} {status:8} {stars:>7} {pushed:10} {str(lic):10} {idle}d")

        if archived:
            failures.append(f"{repo}: archived")
        if idle > STALE_DAYS:
            warnings.append(f"{repo}: no push for {idle} days")

        # license drift is the highest-signal warning: it changes what you may legally do
        snapshot_lic = str(entry.get("license", ""))
        if snapshot_lic and snapshot_lic not in ("n/a",) and "Mixed" not in snapshot_lic:
            if lic.lower() != snapshot_lic.lower() and lic != "none":
                warnings.append(
                    f"{repo}: license changed since snapshot ({snapshot_lic} -> {lic})"
                )

    print()
    if warnings:
        print(f"{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  ! {w}")
    if failures:
        print(f"{len(failures)} failure(s):", file=sys.stderr)
        for f in failures:
            print(f"  x {f}", file=sys.stderr)
        return 1
    if strict and warnings:
        print("strict mode: failing on warnings", file=sys.stderr)
        return 1

    print("all listed repositories exist and are not archived")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
