#!/usr/bin/env bash
#
# Rewrite the author email on every commit in this repository.
#
# Use this when a personal email address has already been committed and pushed
# and you want it replaced with the GitHub noreply address.
#
# Dry run by default. Nothing is modified and nothing is pushed without --apply.
#
#   ./scripts/rewrite-author-email.sh --old you@example.com
#   ./scripts/rewrite-author-email.sh --old you@example.com --apply
#
# After applying, you must force-push yourself:
#
#   git push --force-with-lease origin main
#
# Read the caveats printed at the end before you do.

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: rewrite-author-email.sh [options]

  --old ADDRESS     Author/committer email to replace (required unless detected)
  --new ADDRESS     Replacement address (default: GitHub noreply for this account)
  --apply           Actually rewrite history (default is a dry run)
  --force           Proceed even if the repository has forks
  -h, --help        Show this help

Options are intentionally conservative: a rewrite is destructive and cannot be
undone for anyone who has already fetched the repository.
USAGE
}

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
note() { printf '%s\n' "$*"; }

OLD_EMAIL=""
NEW_EMAIL=""
APPLY=0
FORCE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --old) OLD_EMAIL="${2:-}"; shift 2 ;;
    --new) NEW_EMAIL="${2:-}"; shift 2 ;;
    --apply) APPLY=1; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1 (try --help)" ;;
  esac
done

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not inside a git repository"
cd "$REPO_ROOT"

# --- Detect the address to replace -------------------------------------------

if [ -z "$OLD_EMAIL" ]; then
  OLD_EMAIL="$(git log --format='%ae%n%ce' --all \
    | grep -v 'noreply@github\.com$' \
    | grep -v '^$' \
    | sort | uniq -c | sort -rn | head -1 | awk '{print $2}')"
  [ -n "$OLD_EMAIL" ] || die "could not detect an author email; pass --old ADDRESS"
  note "Detected author email to replace: $OLD_EMAIL"
fi

# --- Determine the replacement -----------------------------------------------

if [ -z "$NEW_EMAIL" ]; then
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    _id="$(gh api user --jq '.id' 2>/dev/null || true)"
    _login="$(gh api user --jq '.login' 2>/dev/null || true)"
    if [ -n "${_id:-}" ] && [ -n "${_login:-}" ]; then
      NEW_EMAIL="${_id}+${_login}@users.noreply.github.com"
    fi
  fi
fi
[ -n "$NEW_EMAIL" ] || die "could not determine a noreply address; pass --new ADDRESS"
note "Replacement email:             $NEW_EMAIL"

if [ "$OLD_EMAIL" = "$NEW_EMAIL" ]; then
  note "Nothing to do: the addresses are identical."
  exit 0
fi

# --- Safety checks ------------------------------------------------------------

if [ -n "$(git status --porcelain)" ]; then
  die "working tree is dirty — commit or stash first"
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
note "Current branch:                $BRANCH"

AFFECTED="$(git log --all --format='%H %ae %ce' | grep -F "$OLD_EMAIL" | wc -l | tr -d ' ')"
note "Commits carrying that address: $AFFECTED"
if [ "$AFFECTED" = "0" ]; then
  note "No commits use $OLD_EMAIL. Nothing to do."
  exit 0
fi

if [ "$FORCE" -eq 0 ] && command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  FORKS="$(gh api "repos/{owner}/{repo}" --jq '.forks_count' 2>/dev/null || echo "")"
  if [ -n "$FORKS" ] && [ "$FORKS" -gt 0 ]; then
    die "repository has $FORKS fork(s); the old address will persist in them.
       Re-run with --force only if you accept that."
  fi
fi

FILTER_CMD=(git filter-repo
  --email-callback "return email.replace(b\"$OLD_EMAIL\", b\"$NEW_EMAIL\")"
  --force)

# --- Dry run ------------------------------------------------------------------

if [ "$APPLY" -eq 0 ]; then
  note ""
  note "DRY RUN — nothing has been changed."
  note "This is the command that would run:"
  note ""
  printf '  %q ' "${FILTER_CMD[@]}"; printf '\n'
  note ""
  note "Re-run with --apply to execute it."
  exit 0
fi

# --- Apply --------------------------------------------------------------------

command -v git-filter-repo >/dev/null 2>&1 || die \
  "git-filter-repo is not installed. Install it with: pipx install git-filter-repo
       (or: pip install git-filter-repo) and re-run."

BACKUP="backup/pre-email-rewrite-$(date -u +%Y%m%dT%H%M%SZ)"
git branch "$BACKUP" || die "could not create backup branch $BACKUP"
note "Backup branch created:         $BACKUP"

"${FILTER_CMD[@]}"

note ""
note "Rewrite complete. Verification:"
git log --format='%h %ae' | sort -u -k2 | sed 's/^/  /'

if git log --format='%ae%n%ce' --all | grep -qF "$OLD_EMAIL"; then
  die "the old address is still present — do not push; restore from $BACKUP"
fi

cat <<NEXT

Next steps — in this order:

  1. Force-push to the default branch (never --force, always --force-with-lease):

       git push --force-with-lease origin main

  2. Set the address for future commits so this does not recur:

       git config --global user.email "$NEW_EMAIL"

  3. In GitHub: Settings -> Emails
       - enable "Keep my email addresses private"
       - enable "Block command line pushes that expose my email"

  4. Delete the local backup branch once you are satisfied:

       git branch -D $BACKUP

Caveats:
  - Anyone who has already fetched still has the old address in their clone, and
    GitHub caches commit views; expect the old value to linger for a while.
  - Rewriting the default branch invalidates open pull request merge bases.
  - If the address was ever used as a signing identity or a verified email, remove
    it from the account afterwards.
NEXT
