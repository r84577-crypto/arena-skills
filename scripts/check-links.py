#!/usr/bin/env python3
"""Validate relative links and heading anchors in this repository's Markdown.

Runs offline and with no dependencies, so it behaves identically on a laptop and
in CI. External URLs are deliberately out of scope — see the `links-upstream`
job in .github/workflows/docs.yml.

Usage:
    python3 scripts/check-links.py [paths...]

Exits 0 when everything resolves, 1 otherwise.
"""

from __future__ import annotations

import pathlib
import re
import sys

SKIP_DIRS = {"node_modules", ".git", ".cache", "dist", "build"}
# Leading whitespace is significant in real documents: fences inside list items
# are indented, and their contents must not be parsed as links.
FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?^[ \t]*\1[^\n]*$", re.M | re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$", re.M)


def slug(heading: str) -> str:
    """Approximate GitHub's heading anchor algorithm."""
    text = heading.strip().lower()
    text = re.sub(r"`", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # links -> link text
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text


def visible_text(raw: str) -> str:
    """Remove fenced code blocks and inline code so their contents are not parsed as links."""
    text = FENCE_RE.sub("", raw)
    return INLINE_CODE_RE.sub("", text)


def anchors_of(text: str) -> set[str]:
    found = set()
    for _, heading in HEADING_RE.findall(text):
        found.add(slug(heading))
    return found


def md_files(paths: list[str]) -> list[pathlib.Path]:
    roots = [pathlib.Path(p) for p in paths] if paths else [pathlib.Path(".")]
    out: list[pathlib.Path] = []
    for root in roots:
        if root.is_file() and root.suffix == ".md":
            out.append(root)
            continue
        for f in sorted(root.rglob("*.md")):
            if not SKIP_DIRS.intersection(f.parts):
                out.append(f)
    return out


def main(argv: list[str]) -> int:
    files = md_files(argv[1:])
    if not files:
        print("no Markdown files found", file=sys.stderr)
        return 1

    # Preload anchors for every file so cross-file fragments can be checked.
    text_cache = {f: f.read_text(encoding="utf-8") for f in files}
    anchor_cache = {f: anchors_of(t) for f, t in text_cache.items()}

    problems: list[str] = []
    checked = 0

    for path in files:
        for target in LINK_RE.findall(visible_text(text_cache[path])):
            if target.startswith(("http://", "https://", "mailto:", "//")):
                continue
            checked += 1

            if target.startswith("#"):
                if target[1:] not in anchor_cache[path]:
                    problems.append(f"{path}: dead anchor {target}")
                continue

            file_part, _, fragment = target.partition("#")
            dest = (path.parent / file_part).resolve()
            try:
                rel = dest.relative_to(pathlib.Path.cwd().resolve())
            except ValueError:
                problems.append(f"{path}: link escapes the repository: {target}")
                continue

            if not dest.exists():
                problems.append(f"{path}: missing file {target}")
                continue

            if fragment and dest.suffix == ".md":
                if fragment not in anchor_cache.get(rel, set()):
                    problems.append(f"{path}: dead anchor {target}")

        # Images are assets, not pages: the link pass skips them via the `(?<!!)`
        # lookahead, so a deleted diagram used to pass silently.
        for target in IMAGE_RE.findall(visible_text(text_cache[path])):
            if target.startswith(("http://", "https://", "//", "#")):
                continue
            checked += 1
            file_part = target.partition("#")[0]
            if not file_part:
                continue
            dest = (path.parent / file_part).resolve()
            try:
                dest.relative_to(pathlib.Path.cwd().resolve())
            except ValueError:
                problems.append(f"{path}: image escapes the repository: {target}")
                continue
            if not dest.exists():
                problems.append(f"{path}: missing image {target}")

    # Duplicate headings produce ambiguous anchors (GitHub silently appends -1, -2).
    for path in files:
        seen: dict[str, int] = {}
        for _, heading in HEADING_RE.findall(text_cache[path]):
            s = slug(heading)
            seen[s] = seen.get(s, 0) + 1
        for s, count in seen.items():
            if count > 1:
                problems.append(f"{path}: duplicate heading anchor '{s}' x{count}")

    print(f"checked {checked} relative links, anchors, and images in {len(files)} files")
    if problems:
        print(f"\n{len(problems)} problem(s):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("all relative links and anchors resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
