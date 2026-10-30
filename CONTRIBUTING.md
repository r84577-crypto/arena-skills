# Contributing

This repository is documentation and skills — no compiled artifacts. The
"build" is the lint and link check, so a change is done when those pass.

## Layout

```text
README.md              index
docs/                  GitHub Packages reference (vendored, CC BY 4.0)
                       plus skill-sources.md (original, MIT)
data/                  skill-sources.json, checked weekly by CI
skills/                skills, one directory each
skills/_template/      starting point for a new skill
scripts/               maintenance scripts
.github/               CI, templates
NOTICE.md              attribution and licensing per file
```

## Local checks

Run these before opening a pull request. They are the same checks CI runs.

```shell
make check    # every Python check + the test suites
make md       # markdownlint (needs Node)
make          # both of the above
```

`make check` runs, in order: relative links/anchors/images, the skill contract,
negative tests for both checkers, the data-file shape, and a credential scan of
every tracked file. It is deliberately the same set CI runs, so a green `make`
means a green pull request.

Two tools exist because both were needed after real defects:

| Target | Guards against |
| --- | --- |
| `scripts/test-check-links.py` | Indented fences parsed as links; broken images passing silently |
| `scripts/test-validate-skills.py` | Malformed front matter, name/directory drift, tokens in shipped scripts, stale index |

`make fix` regenerates `skills/index.json` after you add or change a skill.

External URLs are checked in CI as a separate report-only job, because
third-party documentation sites move and rate-limit bots — a red external check
does not block a merge, but it does mean a link needs attention.

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

## Updating the skill source guide

`docs/skill-sources.md` is a dated snapshot; `data/skill-sources.json` is what CI verifies.

1. Change `data/skill-sources.json` first.
2. Re-measure before you write numbers. These reproduce the table for any repository:

   ```shell
   gh api repos/OWNER/REPO/git/trees/HEAD?recursive=1 \
     --jq '[.tree[].path | select(test("SKILL.md$"))] | length'
   gh api "repos/OWNER/REPO/commits?since=$(date -u -d '90 days ago' +%FT%TZ)&per_page=100" --jq length
   ```

3. Run `python3 scripts/check-skill-sources.py` — it fails on deleted or archived repositories and
   warns on license drift or 120+ days without a push.
4. Update the page tables to match, and bump the snapshot date in both files.

Only add a repository you have inspected yourself. An entry without measured numbers does not belong
on that page — that is the entire point of it.

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
7. Regenerate the manifest and validate: `python3 scripts/validate-skills.py --write-index`
   then `python3 scripts/validate-skills.py`. Both must be clean.
8. If it ships a validator, add a test beside it and wire it into CI.

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
