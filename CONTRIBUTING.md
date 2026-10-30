# Contributing

This repository is documentation and skills — no compiled artifacts. The
"build" is the lint and link check, so a change is done when those pass.

## Layout

```text
README.md              index
docs/                  GitHub Packages reference (vendored, CC BY 4.0)
skills/                skills, one directory each
skills/_template/      starting point for a new skill
scripts/               maintenance scripts
.github/               CI, templates
NOTICE.md              attribution and licensing per file
```

## Local checks

Run these before opening a pull request. They are the same checks CI runs.

```shell
# Structure: headings, lists, fences, blanks around blocks
npx --yes markdownlint-cli2@0.13.0

# Relative links, heading anchors, duplicate headings (offline, no deps)
python3 scripts/check-links.py
```

Both must pass; CI runs exactly these. External URLs are checked in CI as a
separate report-only job, because third-party documentation sites move and
rate-limit bots — a red external check does not block a merge, but it does mean
a link needs attention.

`MD013` (line length) is disabled deliberately: these pages carry long URLs and
tables, and wrapping them harms diffs more than it helps readability.

The CI also fails if any credential-bearing file (`nuget.config`, `.npmrc`,
`settings.xml`, `~/.gem/credentials`, keys, `.env`) is ever tracked.

## Commit email and signing

Commits in this repository must use the GitHub noreply address, not a personal
address:

```text
USER_ID+USERNAME@users.noreply.github.com
```

Set it once:

```shell
git config user.email "USER_ID+USERNAME@users.noreply.github.com"
```

If a commit has already been pushed with a real address, rewrite the history
with `scripts/rewrite-author-email.sh` — it is dry-run by default:

```shell
./scripts/rewrite-author-email.sh --old you@example.com
```

Then enable **Settings → Emails → "Block command line pushes that expose my
email"** so it cannot happen again.

Sign your commits if you have a key configured (`git commit -S`). Commits made
through the GitHub web editor are signed with GitHub's web-flow key, which
proves they were made in the browser — not that you signed them.

## Commit messages

Short imperative subject, optional body explaining *why*:

```text
docs: correct the ghcr.io digest placeholder

The previous example used a non-hexadecimal digest, so the pull command
failed with "invalid reference format".
```

Prefixes in use: `docs:`, `skills:`, `ci:`, `chore:`.

## Adding or changing a skill

1. Copy `skills/_template/SKILL.md` to `skills/<skill-name>/SKILL.md`.
2. `name` in the front matter must equal the directory name.
3. Write `description` for retrieval — it is the only text an agent reads before
   deciding to load the skill. Name the triggers, and name the near-misses.
4. Keep `SKILL.md` about method. Put reference tables and long examples in
   sibling files and link them relatively.
5. State the boundaries: what the skill may do unattended, what needs
   confirmation, what it must never do.
6. Add it to the table in `skills/README.md`.
7. If it ships a validator, add a test beside it and wire it into CI.

## Vendoring third-party material

Do not copy code or prose in silently. For each vendored item, record in
`NOTICE.md`:

- upstream URL and the exact commit SHA (not a branch),
- the upstream license, with the license file preserved in the directory,
- what was changed locally.

Unattributed vendoring is the most common reason repositories like this one get
taken down, and it is avoidable in thirty seconds.

## Changing a `docs/` page

Those pages are derived from GitHub Docs under CC BY 4.0. When you edit one:

- keep the source link and snapshot date at the top accurate,
- keep corrections that were made deliberately (search the file for `[!WARNING]`
  and `[!IMPORTANT]` blocks — several fix real defects in the upstream copy),
- if you re-sync from upstream, update `NOTICE.md` too.

## Pull requests

Fill in the template. Keep one topic per pull request. CI must be green.
