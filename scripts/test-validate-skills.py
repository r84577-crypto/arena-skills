#!/usr/bin/env python3
"""Negative tests for scripts/validate-skills.py.

A validator that passes everything is worse than no validator, so each case below
injects a specific defect into a throwaway copy of the repository and asserts the
checker reacts correctly. CI runs this before the real validation.

Usage:
    python3 scripts/test-validate-skills.py
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
CHECKER = "scripts/validate-skills.py"
IGNORE = shutil.ignore_patterns(".git", "node_modules", "__pycache__", ".cache")


def run_in(root: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, CHECKER, *args],
        cwd=root,
        capture_output=True,
        text=True,
    )


def fresh_copy(tmp: pathlib.Path) -> pathlib.Path:
    dest = tmp / "repo"
    shutil.copytree(REPO, dest, ignore=IGNORE)
    return dest


def case(name: str, mutate, expect_fail: bool, expect_text: str = "", reindex: bool = False) -> bool:
    """Mutate a copy of the repo, run the checker, assert the outcome.

    Set reindex=True when the mutation legitimately changes a description, so the
    test isolates the rule under examination instead of tripping index staleness.
    """
    with tempfile.TemporaryDirectory() as td:
        root = fresh_copy(pathlib.Path(td))
        mutate(root)
        if reindex:
            run_in(root, "--write-index")
        result = run_in(root)
        output = result.stdout + result.stderr

        ok = (result.returncode != 0) if expect_fail else (result.returncode == 0)
        text_ok = expect_text.lower() in output.lower() if expect_text else True

        status = "PASS" if ok and text_ok else "FAIL"
        print(f"  [{status}] {name}")
        if not (ok and text_ok):
            print(f"        expected fail={expect_fail} text={expect_text!r}")
            print(f"        exit={result.returncode}")
            for line in output.strip().splitlines()[:6]:
                print(f"        | {line}")
        return ok and text_ok


def set_front_matter(root: pathlib.Path, skill: str, fm: str) -> None:
    """Replace the entire front matter block, so block scalars cannot bleed into other keys."""
    p = root / "skills" / skill / "SKILL.md"
    lines = p.read_text(encoding="utf-8").splitlines()
    assert lines[0].strip() == "---"
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    p.write_text(
        "---\n" + fm.strip() + "\n---\n" + "\n".join(lines[end + 1 :]),
        encoding="utf-8",
    )


def custom_case(name: str, fn) -> bool:
    """Run an arbitrary assertion against a fresh copy."""
    with tempfile.TemporaryDirectory() as td:
        root = fresh_copy(pathlib.Path(td))
        try:
            ok, detail = fn(root)
        except Exception as exc:  # noqa: BLE001 - report, do not crash the suite
            ok, detail = False, f"exception: {exc}"
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            print(f"        {detail}")
        return ok


def edit_skill(root: pathlib.Path, skill: str, old: str, new: str) -> None:
    p = root / "skills" / skill / "SKILL.md"
    text = p.read_text(encoding="utf-8")
    assert old in text, f"fixture drift: {old!r} not found in {p}"
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> int:
    print("validate-skills.py negative tests")

    results = []

    results.append(case(
        "clean repository passes",
        lambda root: None,
        expect_fail=False,
    ))

    results.append(case(
        "front matter name does not match directory",
        lambda root: edit_skill(root, "repo-audit", "name: repo-audit", "name: repo-auditor"),
        expect_fail=True,
        expect_text="does not match directory",
    ))

    results.append(case(
        "missing description",
        lambda root: edit_skill(
            root, "repo-audit",
            "description: >",
            "note: >",
        ),
        expect_fail=True,
        expect_text="missing `description`",
    ))

    results.append(case(
        "description too short to drive retrieval",
        lambda root: edit_skill(
            root, "skill-authoring",
            "description: >",
            "description: Helps with things.",
        ),
        expect_fail=True,
        expect_text="description must be",
    ))

    results.append(case(
        "vague description warns without failing",
        lambda root: set_front_matter(
            root,
            "skill-authoring",
            """
name: skill-authoring
description: >
  Writes and repairs SKILL.md files for this repository so that the front matter
  contract stays intact across every skill directory that exists on disk.
license: MIT
version: 1.0.0
""",
        ),
        expect_fail=False,
        expect_text="no retrieval cue",
        reindex=True,
    ))

    results.append(case(
        "uppercase name rejected",
        lambda root: edit_skill(root, "repo-audit", "name: repo-audit", "name: Repo-Audit"),
        expect_fail=True,
        expect_text="must be lowercase",
    ))

    results.append(case(
        "dead relative link inside a skill",
        lambda root: (root / "skills" / "repo-audit" / "SKILL.md").write_text(
            (root / "skills" / "repo-audit" / "SKILL.md").read_text(encoding="utf-8")
            + "\nSee [the missing file](NOT-SHIPPED.md).\n",
            encoding="utf-8",
        ),
        expect_fail=True,
        expect_text="dead relative link",
    ))

    results.append(case(
        "credential-shaped string rejected",
        lambda root: (root / "skills" / "repo-audit" / "SKILL.md").write_text(
            (root / "skills" / "repo-audit" / "SKILL.md").read_text(encoding="utf-8")
            + "\nexport TOKEN=ghp_"
            + "A" * 36
            + "\n",
            encoding="utf-8",
        ),
        expect_fail=True,
        expect_text="possible GitHub token",
    ))

    results.append(case(
        "stale index detected",
        lambda root: edit_skill(
            root, "repo-audit",
            "description: >",
            "description: >\n  Audits a repository for hygiene gaps. Use when asked to review a repository,\n"
            "  adopt a dependency, or explain why it reads as abandoned. Not for code review.\n  ignore: >",
        ),
        expect_fail=True,
        expect_text="out of date",
    ))

    results.append(case(
        "skill directory without SKILL.md",
        lambda root: (root / "skills" / "orphan-skill").mkdir(exist_ok=True),
        expect_fail=True,
        expect_text="missing SKILL.md",
    ))

    results.append(case(
        "body without a top-level heading",
        lambda root: edit_skill(root, "repo-audit", "# Repository audit", "Repository audit"),
        expect_fail=True,
        expect_text="no top-level heading",
    ))

    # Token hidden in a shipped script — the case that motivated the shared scanner.
    results.append(case(
        "credential in a shipped shell script is caught",
        lambda root: (root / "skills" / "repo-audit" / "setup.sh").write_text(
            "#!/bin/sh\nexport GITHUB_TOKEN=ghp_" + "A" * 36 + "\n",
            encoding="utf-8",
        ),
        expect_fail=True,
        expect_text="possible GitHub token",
    ))

    # The template is what everyone copies, so it must be checked too.
    results.append(case(
        "template without a top-level heading is caught",
        lambda root: (root / "skills" / "_template" / "SKILL.md").write_text(
            (root / "skills" / "_template" / "SKILL.md")
            .read_text(encoding="utf-8")
            .replace("# Example Skill", "Example Skill"),
            encoding="utf-8",
        ),
        expect_fail=True,
        expect_text="no top-level heading",
    ))

    def template_not_indexed(root: pathlib.Path):
        run_in(root, "--write-index")
        data = json.loads((root / "skills" / "index.json").read_text(encoding="utf-8"))
        names = [s["name"] for s in data["skills"]]
        if "_template" in names:
            return False, f"template leaked into the index: {names}"
        return True, ""

    results.append(custom_case(
        "template is validated but never indexed",
        template_not_indexed,
    ))

    def metadata_version(root: pathlib.Path):
        skill = root / "skills" / "meta-version"
        skill.mkdir(exist_ok=True)
        (skill / "SKILL.md").write_text(
            "---\n"
            "name: meta-version\n"
            "description: >\n"
            "  Exercises nested metadata so that the index records a version declared\n"
            "  under a metadata map, which several published skills do in practice.\n"
            "license: MIT\n"
            "metadata:\n"
            "  version: 2.0.0\n"
            "---\n\n"
            "# Meta version\n",
            encoding="utf-8",
        )
        run_in(root, "--write-index")
        data = json.loads((root / "skills" / "index.json").read_text(encoding="utf-8"))
        entry = next((s for s in data["skills"] if s["name"] == "meta-version"), None)
        if entry is None:
            return False, "skill missing from the index"
        if entry["version"] != "2.0.0":
            return False, f"version recorded as {entry['version']!r}, expected '2.0.0'"
        return True, ""

    results.append(custom_case(
        "metadata.version is recorded in the index",
        metadata_version,
    ))

    print()
    passed, total = sum(1 for r in results if r), len(results)
    print(f"{passed}/{total} cases behaved correctly")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
