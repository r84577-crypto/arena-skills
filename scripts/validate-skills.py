#!/usr/bin/env python3
"""Validate every skill in skills/ against the contract this repository enforces.

A skill is a directory containing a SKILL.md whose YAML front matter declares
`name` (matching the directory) and `description` (written for retrieval). This
checker enforces that, plus the things that silently break loading: dead
relative links, credential-shaped strings, and an out-of-date index.

Dependency-free by design, so a laptop and CI behave identically.

Usage:
    python3 scripts/validate-skills.py                # validate, verify index
    python3 scripts/validate-skills.py --write-index  # regenerate skills/index.json
    python3 scripts/validate-skills.py --quiet        # only problems

Exit codes: 0 clean (warnings allowed), 1 error.

Front matter support: the simple scalar subset — `key: value`, quoted values,
and `|` / `>` block scalars. Nested maps are recognised and ignored, not
validated.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
INDEX = SKILLS_DIR / "index.json"
TEMPLATE_DIRS = {"_template"}

# Shared with CI so a token in a skill's shell script is caught by the same rules
# as one in prose. Sibling import: both files live in scripts/.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scan_secrets import find_secrets, looks_binary  # noqa: E402

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE_RE = re.compile(r"^(`{3,}|~{3,}).*?^\1[^\n]*$", re.M | re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
RETRIEVAL_CUES = ("use when", "use for", "when the user", "trigger", "use this")
MIN_DESC, MAX_DESC = 40, 1024

errors: list[str] = []
warnings: list[str] = []


def err(skill: str, message: str) -> None:
    errors.append(f"{skill}: {message}")


def warn(skill: str, message: str) -> None:
    warnings.append(f"{skill}: {message}")


# --------------------------------------------------------------------------- #
# Front matter
# --------------------------------------------------------------------------- #

def split_front_matter(text: str) -> tuple[str | None, str]:
    """Return (front matter body, document body). Front matter body is None if absent."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1 :])
    return None, text


def parse_front_matter(body: str) -> dict[str, str]:
    """Parse the scalar subset of YAML used by SKILL.md front matter."""
    data: dict[str, str] = {}
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        # Nested map / list under a key: record nothing, skip the block.
        if line[:1].isspace():
            i += 1
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+):\s*(.*)$", line)
        if not match:
            i += 1
            continue
        key, value = match.group(1), match.group(2).strip()

        if value in {"|", ">", "|-", ">-", "|+", ">+"}:
            block: list[str] = []
            i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i][:1].isspace()):
                block.append(lines[i].strip())
                i += 1
            joiner = "\n" if value.startswith("|") else " "
            data[key] = joiner.join(block).strip()
            continue

        if not value:
            # A nested map (e.g. `metadata:`) — record one level as dotted keys so
            # `metadata.version` is not silently lost.
            nested: dict[str, str] = {}
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j][:1].isspace()):
                sub = re.match(r"^\s+([A-Za-z0-9_.-]+):\s*(.*)$", lines[j])
                if sub:
                    sub_value = sub.group(2).strip()
                    if len(sub_value) >= 2 and sub_value[0] == sub_value[-1] and sub_value[0] in "\"'":
                        sub_value = sub_value[1:-1]
                    nested[sub.group(1)] = sub_value
                j += 1
            for sub_key, sub_value in nested.items():
                data[f"{key}.{sub_key}"] = sub_value
            data[key] = ""
            i = j
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        data[key] = value
        i += 1
    return data


# --------------------------------------------------------------------------- #
# Per-skill checks
# --------------------------------------------------------------------------- #

def strip_code(text: str) -> str:
    return INLINE_CODE_RE.sub("", FENCE_RE.sub("", text))


def check_links(skill: str, path: pathlib.Path, text: str) -> None:
    for target in LINK_RE.findall(strip_code(text)):
        if target.startswith(("http://", "https://", "mailto:", "#", "//")):
            continue
        file_part = target.partition("#")[0]
        if not file_part:
            continue
        dest = (path.parent / file_part).resolve()
        if not dest.exists():
            err(skill, f"dead relative link in {path.name}: {target}")


def check_credentials(skill: str, directory: pathlib.Path) -> None:
    """Scan every shipped file, not just prose: scripts are where tokens hide."""
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or looks_binary(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        for name, excerpt in find_secrets(text):
            err(skill, f"possible {name} in {path.relative_to(directory)} ({excerpt})")


def load_skill(directory: pathlib.Path, template: bool = False) -> dict[str, str] | None:
    name = directory.name
    skill_md = directory / "SKILL.md"
    if not skill_md.is_file():
        err(name, "missing SKILL.md")
        return None

    text = skill_md.read_text(encoding="utf-8")
    body = split_front_matter(text)
    if body[0] is None:
        err(name, "SKILL.md has no YAML front matter (must start with ---)")
        return None

    fm = parse_front_matter(body[0])
    doc = body[1]

    declared = fm.get("name", "")
    if not declared:
        err(name, "front matter is missing `name`")
    elif not template:
        # The template intentionally documents a placeholder name.
        if declared != name:
            err(name, f"front matter name '{declared}' does not match directory '{name}'")
        if not NAME_RE.match(declared):
            err(name, f"name '{declared}' must be lowercase letters, digits, and hyphens")
        if len(declared) > 64:
            err(name, "name must be 64 characters or fewer")

    description = fm.get("description", "")
    if not description:
        err(name, "front matter is missing `description`")
    else:
        if not MIN_DESC <= len(description) <= MAX_DESC:
            err(name, f"description must be {MIN_DESC}-{MAX_DESC} characters (is {len(description)})")
        lowered = description.lower()
        if not any(cue in lowered for cue in RETRIEVAL_CUES):
            warn(name, "description has no retrieval cue ('Use when ...') — agents may never load it")
        if len(description) < 100:
            warn(name, "description is short; name the trigger conditions explicitly")

    if not re.search(r"^#\s+\S", doc, re.M):
        err(name, "document body has no top-level heading")

    if "license" not in fm:
        warn(name, "no `license` in front matter (required if you vendor this skill)")

    for md in sorted(directory.rglob("*.md")):
        check_links(name, md, md.read_text(encoding="utf-8"))

    check_credentials(name, directory)

    scripts = [p for p in directory.rglob("*") if p.suffix in {".sh", ".py", ".js", ".mjs", ".cjs", ".ts", ".ps1"}]
    if scripts:
        warn(name, f"ships {len(scripts)} script(s); document what they execute")

    return {
        "name": name,
        "path": f"skills/{name}",
        "description": description,
        "license": fm.get("license", ""),
        # Several published skills declare version under `metadata:`.
        "version": fm.get("version") or fm.get("metadata.version", ""),
        "has_scripts": bool(scripts),
    }


# --------------------------------------------------------------------------- #
# Index
# --------------------------------------------------------------------------- #

def build_index(entries: list[dict]) -> dict:
    return {
        "generated_by": "scripts/validate-skills.py --write-index",
        "skills": sorted(entries, key=lambda e: e["name"]),
    }


def check_index(entries: list[dict]) -> None:
    expected = build_index(entries)
    if not INDEX.is_file():
        err("index", "skills/index.json is missing — run: python3 scripts/validate-skills.py --write-index")
        return
    try:
        actual = json.loads(INDEX.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        err("index", f"skills/index.json is not valid JSON ({exc})")
        return
    if actual != expected:
        err("index", "skills/index.json is out of date — run: python3 scripts/validate-skills.py --write-index")


# --------------------------------------------------------------------------- #

def main(argv: list[str]) -> int:
    write_index = "--write-index" in argv
    quiet = "--quiet" in argv

    if not SKILLS_DIR.is_dir():
        print("error: skills/ directory not found", file=sys.stderr)
        return 1

    directories = sorted(d for d in SKILLS_DIR.iterdir() if d.is_dir())
    if not directories:
        print("error: no skills found under skills/ (index.json would be empty)", file=sys.stderr)
        return 1

    # The template is validated (it is what everyone copies) but never indexed.
    entries = []
    for directory in directories:
        entry = load_skill(directory, template=directory.name in TEMPLATE_DIRS)
        if entry and directory.name not in TEMPLATE_DIRS:
            entries.append(entry)

    if write_index:
        INDEX.write_text(json.dumps(build_index(entries), indent=2) + "\n", encoding="utf-8")
        print(f"wrote {INDEX.relative_to(ROOT)} with {len(entries)} skill(s)")
    else:
        check_index(entries)

    if errors:
        for e in errors:
            print(f"ERROR  {e}", file=sys.stderr)
    if warnings and not quiet:
        for w in warnings:
            print(f"WARN   {w}")

    if not quiet or errors:
        print(
            f"\n{len(entries)} skill(s) checked, {len(errors)} error(s), {len(warnings)} warning(s)"
        )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
