#!/usr/bin/env bash
#
# Install skills from this repository into an agent's skill directory.
#
# Paths follow the conventions documented by the `skills` installer
# (github.com/vercel-labs/skills, docs/agents.md), so a skill lands where the
# host actually looks for it.
#
#   ./scripts/install-skills.sh --list
#   ./scripts/install-skills.sh --target claude-code --dry-run
#   ./scripts/install-skills.sh --target claude-code
#   ./scripts/install-skills.sh --target codex --global
#   ./scripts/install-skills.sh --target claude-code --skill repo-audit --force
#
# Project-scoped by default. Nothing is overwritten without --force.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_SRC="$REPO_ROOT/skills"

TARGET=""
SCOPE="project"
SKILL=""
DRY_RUN=0
FORCE=0

usage() {
  cat <<'USAGE'
Usage: install-skills.sh --target <agent> [options]

  --target <agent>   Agent to install for (see --list). Required.
  --global           Install for the current user instead of the project.
  --skill <name>     Install one skill. Default: every skill.
  --dry-run          Print what would happen, change nothing.
  --force            Overwrite an existing skill directory.
  --list             Show available targets and skills.
  -h, --help         Show this help.

Supported targets and the directories they use:

  claude-code      .claude/skills/          ~/.claude/skills/
  codex            .agents/skills/          ~/.agents/skills/
  cursor           .agents/skills/          ~/.cursor/skills/
  gemini-cli       .agents/skills/          ~/.gemini/skills/
  github-copilot   .agents/skills/          ~/.copilot/skills/
  cline            .agents/skills/          ~/.agents/skills/
  opencode         .opencode/skills/        ~/.opencode/skills/
  agents           .agents/skills/          ~/.agents/skills/
USAGE
}

# Project and global destinations per target.
project_path() {
  case "$1" in
    claude-code)    echo ".claude/skills" ;;
    opencode)       echo ".opencode/skills" ;;
    codex|cline|cursor|gemini-cli|github-copilot|agents) echo ".agents/skills" ;;
    *) return 1 ;;
  esac
}

global_path() {
  case "$1" in
    claude-code)    echo "$HOME/.claude/skills" ;;
    cursor)         echo "$HOME/.cursor/skills" ;;
    gemini-cli)     echo "$HOME/.gemini/skills" ;;
    github-copilot) echo "$HOME/.copilot/skills" ;;
    opencode)       echo "$HOME/.opencode/skills" ;;
    codex|cline|agents) echo "$HOME/.agents/skills" ;;
    *) return 1 ;;
  esac
}

list_all() {
  echo "Targets:"
  for t in claude-code codex cursor gemini-cli github-copilot cline opencode agents; do
    printf '  %-16s project: %-18s global: %s\n' "$t" "$(project_path "$t")" "$(global_path "$t")"
  done
  echo
  echo "Skills:"
  for d in "$SKILLS_SRC"/*/; do
    name="$(basename "$d")"
    [ "$name" = "_template" ] && continue
    [ -f "$d/SKILL.md" ] || continue
    printf '  %s\n' "$name"
  done
}

while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="${2:-}"; shift 2 ;;
    --global) SCOPE="global"; shift ;;
    --skill) SKILL="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --force) FORCE=1; shift ;;
    --list) list_all; exit 0 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "error: unknown argument: $1 (try --help)" >&2; exit 2 ;;
  esac
done

if [ -z "$TARGET" ]; then
  echo "error: --target is required (try --list)" >&2
  exit 2
fi

if [ "$SCOPE" = "global" ]; then
  DEST_ROOT="$(global_path "$TARGET")" || { echo "error: unknown target '$TARGET'" >&2; exit 2; }
else
  DEST_ROOT="$(project_path "$TARGET")" || { echo "error: unknown target '$TARGET'" >&2; exit 2; }
  DEST_ROOT="$PWD/$DEST_ROOT"
fi

# Collect skills to install. A counter is used instead of ${#SKILLS[@]} because
# bash 3.2 (the default /bin/bash on macOS) treats an empty array as unset under
# `set -u` and aborts before the friendly error below can run.
SKILLS=()
SKILL_COUNT=0
if [ -n "$SKILL" ]; then
  [ -f "$SKILLS_SRC/$SKILL/SKILL.md" ] || { echo "error: no such skill '$SKILL' (try --list)" >&2; exit 2; }
  SKILLS=("$SKILL")
  SKILL_COUNT=1
else
  for d in "$SKILLS_SRC"/*/; do
    name="$(basename "$d")"
    [ "$name" = "_template" ] && continue
    [ -f "$d/SKILL.md" ] || continue
    SKILLS+=("$name")
    SKILL_COUNT=$((SKILL_COUNT + 1))
  done
fi

[ "$SKILL_COUNT" -gt 0 ] || { echo "error: no skills found to install" >&2; exit 2; }

echo "target:  $TARGET ($SCOPE)"
echo "dest:    $DEST_ROOT"
echo "skills:  ${SKILLS[*]}"
[ "$DRY_RUN" -eq 1 ] && echo "mode:    dry run"

if [ "$DRY_RUN" -eq 0 ]; then
  mkdir -p "$DEST_ROOT"
fi

installed=0
for name in "${SKILLS[@]:-}"; do
  src="$SKILLS_SRC/$name"
  dest="$DEST_ROOT/$name"

  if [ -e "$dest" ]; then
    if [ "$FORCE" -eq 0 ]; then
      echo "skip:    $name (already exists; use --force to overwrite)"
      continue
    fi
    if [ "$DRY_RUN" -eq 0 ]; then
      rm -rf -- "$dest"
    fi
    echo "replace: $name"
  fi

  if [ "$DRY_RUN" -eq 1 ]; then
    echo "would install: $name -> $dest"
  else
    cp -R -- "$src" "$dest"
    echo "install: $name -> $dest"
  fi
  installed=$((installed + 1))
done

echo
echo "$installed skill(s) processed."
if [ "$DRY_RUN" -eq 0 ] && [ "$installed" -gt 0 ]; then
  cat <<'NEXT'

Next: make sure your agent actually scans that directory. A public repository is
not loaded automatically - the host has to be pointed at the skills path. If your
agent exposes a "skills directory" setting, set it to the dest above.
NEXT
fi
