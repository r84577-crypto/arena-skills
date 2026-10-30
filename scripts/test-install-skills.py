#!/usr/bin/env python3
"""Tests for install-skills.sh.

Each case builds a throwaway repository containing a copy of the installer, so
nothing here reads or writes the real `skills/` tree and nothing touches $HOME.

The bash 3.2 case is important: the installer must print "no skills found to
install" rather than dying with "unbound variable" when the skill list is empty.
Bash 3.2 cannot be installed here, so that behaviour is covered twice - once by
exercising the empty-list path, and once by asserting the array-length
expansion that trips it is absent from the source.

    python3 scripts/test-install-skills.py
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

SCRIPT = pathlib.Path(__file__).resolve().parent / "install-skills.sh"

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


def build_repo(root: pathlib.Path, skills: tuple[str, ...] = ("alpha", "beta")) -> pathlib.Path:
    """Lay out a repository the installer can run from."""
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "skills").mkdir(exist_ok=True)
    shutil.copy2(SCRIPT, root / "scripts" / "install-skills.sh")
    (root / "skills" / "_template").mkdir(exist_ok=True)
    (root / "skills" / "_template" / "SKILL.md").write_text("---\nname: _template\n---\n")
    for name in skills:
        (root / "skills" / name).mkdir(exist_ok=True)
        (root / "skills" / name / "SKILL.md").write_text(f"---\nname: {name}\n---\nbody\n")
        (root / "skills" / name / "REFERENCE.md").write_text(f"{name} reference\n")
    return root


def run(repo: pathlib.Path, *args: str, home: pathlib.Path | None = None, cwd: pathlib.Path | None = None):
    env = dict(os.environ)
    if home is not None:
        env["HOME"] = str(home)
    return subprocess.run(
        ["bash", str(repo / "scripts" / "install-skills.sh"), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(cwd or repo),
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp)
        fake_home = base / "home"
        fake_home.mkdir()

        # --- --list -------------------------------------------------------
        repo = build_repo(base / "r1")
        result = run(repo, "--list")
        check("--list shows both skills", "alpha" in result.stdout and "beta" in result.stdout, result.stdout)
        check("--list hides the template", "_template" not in result.stdout, result.stdout)
        check("--list shows claude-code's path", ".claude/skills" in result.stdout, result.stdout)
        check("--list shows the shared agents path", ".agents/skills" in result.stdout, result.stdout)
        check("--list exits 0", result.returncode == 0, f"exit {result.returncode}")

        # --- argument handling --------------------------------------------
        result = run(repo, "--target", "nope", "--dry-run")
        check("unknown target exits 2", result.returncode == 2, f"exit {result.returncode}")
        check("unknown target names the target", "unknown target" in result.stderr, result.stderr)

        result = run(repo, "--target", "claude-code", "--skill", "ghost", "--dry-run")
        check("unknown skill exits 2", result.returncode == 2, f"exit {result.returncode}")
        check("unknown skill names the skill", "no such skill" in result.stderr, result.stderr)

        result = run(repo, "--frobnicate")
        check("unknown flag exits 2", result.returncode == 2, f"exit {result.returncode}")

        repo_help = build_repo(base / "r-help")
        result = run(repo_help, "--help")
        check("--help exits 0", result.returncode == 0, f"exit {result.returncode}")
        check("--help documents --force", "--force" in result.stdout, result.stdout)

        # --- dry run changes nothing --------------------------------------
        repo = build_repo(base / "r2")
        result = run(repo, "--target", "claude-code", "--dry-run")
        check("dry run reports two skills", "2 skill(s) processed" in result.stdout, result.stdout)
        check("dry run prints intent", "would install: alpha" in result.stdout, result.stdout)
        check("dry run creates no destination", not (repo / ".claude").exists(), str(repo))
        check("dry run exits 0", result.returncode == 0, f"exit {result.returncode}")

        # --- real install -------------------------------------------------
        result = run(repo, "--target", "claude-code")
        check("real install exits 0", result.returncode == 0, f"exit {result.returncode}")
        check("installs into .claude/skills", (repo / ".claude" / "skills" / "alpha" / "SKILL.md").exists())
        check("copies sibling files", (repo / ".claude" / "skills" / "alpha" / "REFERENCE.md").exists())
        check("does not install the template", not (repo / ".claude" / "skills" / "_template").exists())
        check("warns that nothing loads automatically", "not loaded automatically" in result.stdout, result.stdout)

        # --- overwrite protection -----------------------------------------
        target = repo / ".claude" / "skills" / "alpha" / "SKILL.md"
        target.write_text("locally edited\n")
        result = run(repo, "--target", "claude-code")
        check("does not overwrite without --force", "skip:" in result.stdout, result.stdout)
        check("keeps the local edit", target.read_text() == "locally edited\n", target.read_text())

        result = run(repo, "--target", "claude-code", "--force")
        check("--force overwrites", target.read_text() != "locally edited\n", target.read_text())
        check("--force announces the replace", "replace:" in result.stdout, result.stdout)

        # --- target routing -----------------------------------------------
        repo = build_repo(base / "r3")
        result = run(repo, "--target", "codex")
        check("codex lands in .agents/skills", (repo / ".agents" / "skills" / "alpha").is_dir())
        check("codex leaves .claude alone", not (repo / ".claude").exists())

        repo = build_repo(base / "r4")
        result = run(repo, "--target", "claude-code", "--global", home=fake_home)
        check("--global installs under HOME", (fake_home / ".claude" / "skills" / "alpha").is_dir(), result.stdout)
        check("--global writes outside the project", not (repo / ".claude").exists())

        repo = build_repo(base / "r4b")
        result = run(repo, "--target", "codex", "--global", home=fake_home, cwd=base)
        check(
            "--global for shared agents uses ~/.agents/skills",
            (fake_home / ".agents" / "skills" / "alpha").is_dir(),
            result.stdout,
        )

        # --- single skill --------------------------------------------------
        repo = build_repo(base / "r5")
        result = run(repo, "--target", "claude-code", "--skill", "beta")
        check("--skill installs only that skill", (repo / ".claude" / "skills" / "beta").is_dir())
        check("--skill skips the others", not (repo / ".claude" / "skills" / "alpha").exists())
        check("--skill counts one", "1 skill(s) processed" in result.stdout, result.stdout)

        # --- empty skill list (the bash 3.2 regression) --------------------
        repo = build_repo(base / "r6", skills=())
        result = run(repo, "--target", "claude-code", "--dry-run")
        check(
            "empty skill list exits 2, not a crash",
            result.returncode == 2,
            f"exit {result.returncode}: {result.stderr}",
        )
        check(
            "empty skill list prints the friendly error",
            "no skills found to install" in result.stderr,
            result.stderr,
        )
        check(
            "empty skill list does not raise unbound variable",
            "unbound variable" not in result.stderr,
            result.stderr,
        )

    # --- static guard for the bash 3.2 defect -----------------------------
    source = SCRIPT.read_text(encoding="utf-8")
    # Comments are allowed to name the construct; executable lines are not.
    code_lines = [ln for ln in source.splitlines() if not ln.lstrip().startswith("#")]
    check(
        "no bare ${#SKILLS[@]} (aborts on bash 3.2 with an empty array)",
        all("${#SKILLS[@]}" not in ln for ln in code_lines),
        "the guarded counter is the fix; keep it",
    )
    check("uses the guarded counter", "SKILL_COUNT" in source)
    check("sets strict mode", "set -euo pipefail" in source)
    check(
        "iterates defensively over a possibly-empty array",
        '"${SKILLS[@]:-}"' in source,
        "unsuffixed expansion of an empty array also aborts on bash 3.2",
    )

    print()
    if FAILED:
        print(f"{FAILED} case(s) failed, {PASSED} passed")
        return 1
    print(f"{PASSED}/{PASSED} cases behaved correctly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
