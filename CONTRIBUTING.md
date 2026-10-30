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
negative tests for every checker, the data-file shape and its agreement with the
published page, and a credential scan of every tracked file. It is deliberately the
same set CI runs, so a green `make` means a green pull request.

A test suite exists for each checker because every one of them shipped a defect that
a test would have caught:

| Suite | Guards against |
| --- | --- |
| `scripts/test-check-links.py` | Indented fences parsed as links; broken images passing silently; links escaping the repository |
| `scripts/test-validate-skills.py` | Malformed front matter, name/directory drift, tokens in shipped scripts, stale index, missing or empty `## Boundaries`, unparseable `allowed-tools` |
| `scripts/test-check-skill-sources.py` | Bad tier, date, or repo shape; a useless `avoid` entry; a ranked table that disagrees with the data file |
| `scripts/test-install-skills.py` | Wrong host directory, silent overwrite, dry runs that write, and the empty-array crash on bash 3.2 |

`make fix` regenerates `skills/index.json` after you add or change a skill.

### When the data file changes

`data/skill-sources.json` is the source of truth and `docs/skill-sources.md` is its
readable rendering. Update the JSON first, then the page — `make check` compares the
ranked table against the JSON and fails on any disagreement, so the two cannot drift
apart unnoticed.

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

## Before you commit

One-time setup per clone — hooks are not cloned by git, and nothing enables this silently:

```shell
make hooks      # git config core.hooksPath .githooks
```

The pre-commit hook runs `scripts/scan_secrets.py --staged`, which reads the index rather
than the working tree, so a `git add -p` hunk cannot slip past it. It takes about 200 ms
on this repository because it only reads staged files.

If it blocks you wrongly, the answer is an allowlist entry, not `--no-verify`:

```json
{
  "allow": [
    {
      "path": "docs/example.md",
      "rule": "high-entropy string",
      "reason": "documented example token, replaced before publication"
    }
  ]
}
```

| Field | Required | Meaning |
| --- | --- | --- |
| `path` | yes | Glob matched against the repository-relative path |
| `rule` | no | Restrict the entry to one rule; omit to cover all suppressible rules |
| `reason` | yes | At least 15 characters. An exception without an argument is not an exception |

Only the heuristic rules are suppressible — `high-entropy string` and
`generic bearer secret`. A provider prefix (`ghp_`, `AKIA`, PEM blocks) is never
suppressible, because that is a live credential rather than a quotation.

`git commit --no-verify` still exists. If you use it, say why in the commit message;
the next person to read that history deserves to know.

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

## Branch protection

`main` is protected by a ruleset, and the intended configuration is versioned in
[`.github/ruleset-protect-main.json`](.github/ruleset-protect-main.json) so it is
reviewable in a diff rather than living only in the settings UI.

What it enforces:

| Rule | Setting | Why |
| --- | --- | --- |
| Pull request required | 0 approvals | Keeps the gate without locking out a solo maintainer — GitHub does not let you approve your own PR |
| Required status checks | Markdown lint · Relative links, anchors, images · Skill contract · No credentials committed · Verify listed repositories | The five jobs that run on a pull request |
| Strict checks | on | The branch must be current with `main`, which is what surfaces duplicate-content conflicts after a squash merge |
| Force pushes | blocked | History on `main` is append-only |
| Deletion | blocked | — |

Two checks are deliberately **not** required:

- **External links (report only)** — `continue-on-error` by design; requiring a check
  whose premise is "may fail harmlessly" teaches you to ignore red marks.
- Anything that does not run on `pull_request`. A required check that never reports
  blocks the pull request forever. `skill-sources.yml` was in that state until it
  gained a `pull_request` trigger; keep that trigger if you touch the file.

Apply the versioned configuration after editing it:

```shell
gh api --method PUT \
  repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/rulesets/$(gh api repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/rulesets --jq '.[] | select(.name=="protect main") | .id') \
  --input .github/ruleset-protect-main.json
```

Confirm what is actually applied — the file describes intent, the API describes reality:

```shell
gh api repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/rulesets \
  --jq '.[] | select(.name=="protect main") | .id' | \
  xargs -I{} gh api repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/rulesets/{} \
  --jq '.rules[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context'
```

`CODEOWNERS` is documentation of ownership, not enforcement: it does nothing until
*Require review from Code Owners* is switched on, and that switch must stay off while
there is a single owner.
