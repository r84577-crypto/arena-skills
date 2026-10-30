# Agent Skills: verified source guide

> **Snapshot:** 2026-10-30. Every number below was measured against the GitHub API on that date and will drift.
> **Status:** original analysis for this repository (MIT). Not vendored — see [NOTICE.md](../NOTICE.md).
> **Machine-readable copy:** [`data/skill-sources.json`](../data/skill-sources.json). This page explains; the JSON is what CI checks.

This is a short list of agent-skill repositories that survived inspection. It exists because the
ecosystem is enormous and mostly unverified: at snapshot time, GitHub code search returned
**6,897,664** files matching `filename:SKILL.md`, and **39,096** repositories carried
`topic:agent-skills`. Stars are not a usable signal at that scale.

## How these were chosen

Candidates were pulled from topic and code search, then each was checked mechanically:

| Check | Method |
| --- | --- |
| Real skills | Count `SKILL.md` files in the full git tree, then count **distinct** skills (duplicates across harness directories are common) |
| Substance | Look for `tests/`, `evals/`, validators, schemas |
| Maintenance | Commits in the last 90 days, latest release, last push |
| License | Root `LICENSE`, plus per-skill license files where present |
| Security surface | Count shipped scripts and auto-executing `hooks/` |
| Capability claims | Read the actual front matter of sampled `SKILL.md` files |

**No skill listed here was executed.** Capability statements come from front matter and repository
structure, not from observed behaviour. Treat this as a starting point for your own review, not a
substitute for it.

## The format

`SKILL.md` is YAML front matter plus instructions. `name` and `description` are the de facto required
keys; `license`, `version`, `metadata`, `allowed-tools`, and `argument-hint` are common extensions.
The specification and a template ship in [`anthropics/skills`](https://github.com/anthropics/skills)
under `spec/` and `template/`.

Most repositories install through one npm package:

```shell
npx skills@1.7.4 add OWNER/REPO          # pin the version
npx skills@1.7.4 add OWNER/REPO --list   # inspect before installing
```

That package is [`vercel-labs/skills`](https://github.com/vercel-labs/skills) (MIT, two runtime
dependencies, maintains a per-agent install-path matrix covering more than thirty agents). It is a
single trust root for most of this ecosystem — pin it.

## Ranked shortlist

Ordered by verified substance and engineering rigour, not popularity.

| # | Repository | Distinct skills | Stars | License | Last push | 90d commits |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | [`addyosmani/agent-skills`](https://github.com/addyosmani/agent-skills) | 25 | 111,806 | MIT | 2026-10-29 | 100+ |
| 2 | [`obra/superpowers`](https://github.com/obra/superpowers) | 15 | 308,823 | MIT | 2026-10-29 | 6 |
| 3 | [`github/awesome-copilot`](https://github.com/github/awesome-copilot) | 466 | 40,581 | MIT | 2026-10-30 | 100+ |
| 4 | [`anthropics/skills`](https://github.com/anthropics/skills) | 20 | 184,856 | Mixed | 2026-10-28 | 15 |
| 5 | [`cloudflare/security-audit-skill`](https://github.com/cloudflare/security-audit-skill) | 1 | 53,110 | MIT | 2026-09-14 | 3 |
| 6 | [`coreyhaines31/marketingskills`](https://github.com/coreyhaines31/marketingskills) | 54 | 57,372 | MIT | 2026-10-29 | 100+ |
| 7 | [`K-Dense-AI/scientific-agent-skills`](https://github.com/K-Dense-AI/scientific-agent-skills) | 178 | 55,317 | MIT | 2026-10-26 | 95 |
| 8 | [`kepano/obsidian-skills`](https://github.com/kepano/obsidian-skills) | 6 | 50,413 | MIT | 2026-09-15 | 3 |
| 9 | [`wshobson/agents`](https://github.com/wshobson/agents) | 185 | 41,994 | MIT | 2026-10-26 | 90 |
| 10 | [`mvanhorn/last30days-skill`](https://github.com/mvanhorn/last30days-skill) | 1 | 65,926 | MIT | 2026-10-28 | 100+ |
| 11 | [`mattpocock/skills`](https://github.com/mattpocock/skills) | 38 | 307,148 | MIT | 2026-10-30 | 100+ |
| 12 | [`nextlevelbuilder/ui-ux-pro-max-skill`](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | 7 | 142,897 | MIT | 2026-10-26 | 79 |
| 13 | [`JuliusBrussee/caveman`](https://github.com/JuliusBrussee/caveman) | 22 | 116,257 | Apache-2.0 | 2026-10-30 | 100+ |
| 14 | [`ayghri/i-have-adhd`](https://github.com/ayghri/i-have-adhd) | 1 | 59,474 | MIT | 2026-10-19 | 100+ |
| 15 | [`microsoft/skills`](https://github.com/microsoft/skills) | 211 | 3,157 | MIT | 2026-10-30 | 100+ |
| 16 | [`trailofbits/skills`](https://github.com/trailofbits/skills) | 97 | 7,892 | CC-BY-SA-4.0 | 2026-10-28 | 97 |
| 17 | [`microsoft/azure-skills`](https://github.com/microsoft/azure-skills) | 56 | 1,603 | MIT | 2026-10-30 | 70 |
| 18 | [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills) | 9 | 33,249 | MIT stated in README, no LICENSE file | 2026-10-28 | 23 |
| 19 | [`DietrichGebert/ponytail`](https://github.com/DietrichGebert/ponytail) | 6 | 180,769 | MIT | 2026-10-29 | 100+ |

`100+` means the 90-day commit query hit its pagination cap: at least 100 commits.

**Ranks 11-14 come from a second measurement pass**, run on the same snapshot date against
repositories that kept appearing in "best skills" lists but had not surfaced in the code-search
sweep. They are ordered among themselves only; the ordering does not claim they outrank 1-10. Three
of them show the duplication this page warns about: `ui-ux-pro-max` is 13 files for 7 skills,
`caveman` is 28 for 22, `i-have-adhd` is 2 for 1. File counts published by a repository are usually
file counts, not skill counts.

**Ranks 15-19 come from a third pass**, over a "best of 2026" list that named twelve repositories.
Five survived; seven are in the avoid table below. The survival rate is the finding: **the lists that
recommend skill repositories do not check licenses or maintenance**, and four of those seven fail on
licensing alone.

### What earned the top places

**1. `addyosmani/agent-skills`** — 25 distinct skills, **145 eval files** under `evals/cases/`, 9
hooks, CI workflows, release `0.6.14`. It is the only library here that ships an eval harness for its
own skills. Version `0.6.x` means the surface is still moving.

**2. `obra/superpowers`** — 15 skills, 44 contributors, releases through `v7.0.1`, and genuine
multi-vendor install paths (Claude, Codex, Grok, OpenCode, Cursor, Devin). Highest release cadence of
any repository here. It is a workflow doctrine, not a bag of tricks: adopting it changes how your
agent plans. Only 6 commits in 90 days against 308K stars — high reputation, low recent churn.

**3. `github/awesome-copilot`** — 466 `SKILL.md`, **all 466 distinct**, plus 619 scripts and 38
hooks, maintained under the GitHub organisation. Best breadth on the list; quality varies by
contribution and there are no releases to pin. Vet each skill you take.

**5. `cloudflare/security-audit-skill`** — a single skill, and the best evidence-to-claim ratio here:
it ships `validate-findings.cjs` and `validate-coverage-ledger.cjs` **with `.test.cjs` tests** and a
machine-readable report schema. MIT, so fork it while it is small (4 contributors, 3 commits in 90
days).

### Which agents do these support

Compatibility is a property of the installer and the tree, not of a promise. Repositories that ship
per-harness artefacts at snapshot time: `obra/superpowers` (12+ plugin directories),
`addyosmani/agent-skills` (`.claude-plugin/`, `.codex-plugin/`, `.gemini/`, `.opencode/`),
`wshobson/agents` (7+), and `OthmanAdi/planning-with-files` (18). For the rest, `npx skills add`
writes into the agent-specific path from the installer's matrix.

## By category

| Category | Best verified pick | Skills | Note |
| --- | --- | --- | --- |
| Software development | `addyosmani/agent-skills` | 25 | Only library with evals |
| Workflow and methodology | `obra/superpowers` | 15 | v7 maturity, vendor-neutral |
| Testing and QA | `addyosmani` (`test-driven-development`, `browser-testing-with-devtools`) | — | Enforces red-green-refactor |
| Security (defensive) | [`trailofbits/skills`](https://github.com/trailofbits/skills) | 97 | Firm-published, CodeQL/Semgrep workflows — but **CC BY-SA 4.0**, not MIT |
| Security (offensive) | [`usestrix/strix`](https://github.com/usestrix/strix) | 9 | Apache-2.0, benchmarks |
| Research (ML) | [`Orchestra-Research/AI-Research-SKILLs`](https://github.com/Orchestra-Research/AI-Research-SKILLs) | 98 | Stale: 0 commits in 90 days |
| Research (social and web) | `mvanhorn/last30days-skill` | 1 | Declares its tools |
| Science and data | `K-Dense-AI/scientific-agent-skills` | 178 | Heavy Python runtime |
| Document processing | `anthropics/skills` (`docx`, `pdf`, `pptx`, `xlsx`) | 4 | **Proprietary — see below** |
| Office files | [`iOfficeAI/OfficeCLI`](https://github.com/iOfficeAI/OfficeCLI) | 12 | Apache-2.0, npm distribution |
| Business operations | `coreyhaines31/marketingskills` | 54 | Tested, versioned |
| Personal productivity | `kepano/obsidian-skills` | 6 | **Zero scripts** |
| Long-running tasks | [`OthmanAdi/planning-with-files`](https://github.com/OthmanAdi/planning-with-files) | 6 | 18 files, 6 distinct — 3x duplication |
| Design | [`cathrynlavery/diagram-design`](https://github.com/cathrynlavery/diagram-design) | 1 | MIT, tests |
| MCP authoring | `anthropics/skills` → `mcp-builder` | 1 | Apache-2.0 |
| MCP runtime | [`modelcontextprotocol/servers`](https://github.com/modelcontextprotocol/servers) | 11 | `NOASSERTION` license |

No dedicated web-browsing skill pack surfaced. Browsing appears to be consumed at the MCP layer
instead — see [`punkpeye/awesome-mcp-servers`](https://github.com/punkpeye/awesome-mcp-servers), which
is a reference list (MIT, zero `SKILL.md`), not an installable library.

## Licensing: the finding that matters most

[`anthropics/skills`](https://github.com/anthropics/skills) has **no root `LICENSE`** and licensing
is per-skill. Of the 18 skills carrying a `LICENSE.txt` at snapshot time:

| Skills | License | Commercial use |
| --- | --- | --- |
| 14 — `mcp-builder`, `skill-creator`, `frontend-design`, `canvas-design`, `webapp-testing`, `brand-guidelines`, and others | Apache-2.0 | Yes |
| 4 — **`docx`, `pdf`, `pptx`, `xlsx`** | Proprietary | No |

The proprietary `LICENSE.txt` reads *"© 2025 Anthropic, PBC. All rights reserved"* and restricts users
from extracting the materials, retaining copies outside the services, reproducing them, or **creating
derivative works**. The README describes these four as *"source-available, not open source"*, and
their front matter says `license: Proprietary`.

> [!WARNING]
> The four document skills are the most commonly vendored artefacts in this ecosystem, and vendoring
> them is precisely what the license forbids. Use them inside Claude under your Anthropic agreement.
> Do not copy them into your skills directory, your product, or your own repository.

The general lesson: **check the license beside the `SKILL.md` you take, not the badge on the repo.**
A repository-level `MIT` label does not tell you what a subdirectory contains.

## Repositories to avoid, with reasons

Every defect below was verified in the repository, not inferred.

| Repository | Stars | Problem |
| --- | --- | --- |
| [`ComposioHQ/awesome-claude-skills`](https://github.com/ComposioHQ/awesome-claude-skills) | 78,301 | No license file at all, yet it vendors **864 `SKILL.md`**, and had **0 commits in 90 days**. Unlicensed redistribution plus staleness. |
| [`travisvn/awesome-claude-skills`](https://github.com/travisvn/awesome-claude-skills) | 15,630 | No license, 2 contributors, last push 2026-04-28. Effectively abandoned. |
| [`VoltAgent/awesome-agent-skills`](https://github.com/VoltAgent/awesome-agent-skills) | 36,596 | MIT, but the tree contains **0 `SKILL.md`** — a link list, nothing to install. |
| [`affaan-m/ECC`](https://github.com/affaan-m/ECC) | 292,865 | 1,068 `SKILL.md` but only **317 distinct**; 518 are copies under `docs/`. |
| [`multica-ai/andrej-karpathy-skills`](https://github.com/multica-ai/andrej-karpathy-skills) | 226,677 | **No license file**, and no commits since 2026-04-20. The most-starred entry in this table is one `SKILL.md` of behavioural rules: readable, unlicensed, unmaintained, and not redistributable. |
| [`morluto/rea`](https://github.com/morluto/rea) | 408,964 | 5 `SKILL.md` against **5,983 scripts** plus `native/` and `patches/`. An application, not a skill. |
| [`paperclipai/paperclip`](https://github.com/paperclipai/paperclip) | 108,752 | 85 skills, **7,914 scripts**, Docker runtime. An app. |
| [`mksglu/context-mode`](https://github.com/mksglu/context-mode) | 32,875 | `NOASSERTION` license, **132 hook files**, pre-release tags only. |
| [`msitarzewski/agency-agents`](https://github.com/msitarzewski/agency-agents) | 165,233 | **0 `SKILL.md`** — these are subagent personas, not skills. |
| [`Leonxlnx/taste-skill`](https://github.com/Leonxlnx/taste-skill) | 105,744 | Description says skills (plural); the tree contains one. |
| [`Graphify-Labs/graphify`](https://github.com/Graphify-Labs/graphify) | 139,242 | **0 `SKILL.md`** against 602 scripts and 13 hooks. Recommended as a "skill for large codebases"; it is an application. |
| [`openai/skills`](https://github.com/openai/skills) | 28,413 | The README states **"This repository is deprecated"** and points at `openai/plugins`. 0 commits in 90 days; no root license, only per-skill `LICENSE.txt`. |
| [`remotion-dev/skills`](https://github.com/remotion-dev/skills) | 5,908 | **No license file anywhere and no license statement.** Twelve usable skills you may read but not redistribute. |
| [`pedronauck/skills`](https://github.com/pedronauck/skills) | 647 | One `LICENSE` across 88 `SKILL.md`; the rest of the collection grants no rights. |
| [`skillcreatorai/Awesome-Agent-Skills`](https://github.com/skillcreatorai/Awesome-Agent-Skills) | 165 | No license, and last pushed 2025-12-18 — ten months stale. |
| [`mouadja02/skills`](https://github.com/mouadja02/skills) | 12 | `NOASSERTION` license — terms nobody can read — plus 539 scripts across 797 skills. |
| [`itsual/agent-skills-collection`](https://github.com/itsual/agent-skills-collection) | 6 | 503 `SKILL.md` and **zero scripts, zero tests**, 0 commits in 90 days. A bulk dump, not a library. |

Also note: [`anthropics/claude-plugins-official`](https://github.com/anthropics/claude-plugins-official)
(Apache-2.0, 33 skills) bundles `external_plugins/` for Discord, iMessage, and Telegram with
`access` and `configure` skills. That is messaging-account access by design — install it only if that
is what you are deliberately setting up.

## Security notes

**Hooks execute; `SKILL.md` does not.** Before installing a repository, count its hooks. Verified at
snapshot: 132 in `context-mode`, 48 in `microsoft/azure-skills`, 45 in `microsoft/skills`, 38 in
`awesome-copilot`, 18 in `ponytail`, 13 in `graphify`, 9 in `addyosmani/agent-skills` and
`trailofbits/skills`, 6 in `superpowers`. Read every hook file and know what it runs.

**Script count is the surface area.** Measured: 7,914 in `paperclip`, 5,983 in `rea`, 831 in
`alirezarezvani/claude-skills`, 776 in `K-Dense-AI`, 602 in `graphify` (which ships **zero**
`SKILL.md`), 539 in `mouadja02/skills`, 432 in `last30days`, 269 in `trailofbits/skills`. A repository
with zero scripts (`kepano/obsidian-skills`, `itsual/agent-skills-collection`) is a different risk
class from one with thousands.

**Prefer skills that declare their tools.** `last30days` sets `allowed-tools: Bash, Read, Write,
AskUserQuestion, WebSearch` in front matter. Silence about tools is not a safety claim.

**Install project-scoped, not global.** `.agents/skills/` in a project beats `~/.agents/skills/`.
Run agents that load third-party skills in a container or devcontainer, with a credential-free shell.

**The installer reports what you install, by default.** `skills@1.7.4` reads `DISABLE_TELEMETRY`
and `DO_NOT_TRACK`; its own troubleshooting page states that anonymous usage data is sent, that
repository and skill identifiers go with it, and that for non-GitHub sources identifiers may be sent
because visibility cannot be checked. One env var turns off telemetry and the security-audit lookups
together:

```shell
DISABLE_TELEMETRY=1 npx skills@1.7.4 add OWNER/REPO
```

This is not a vulnerability — it is a client behaving as documented. It belongs in a page about
supply-chain risk because the tool that fetches executable instruction text is also the tool with an
outbound channel.

**Pinning means a lockfile here, not a flag.** `skills` has no `--pin`. What it has:

| Mechanism | Command | Effect |
| --- | --- | --- |
| Lock file | `experimental_install` | Restores from `skills-lock.json`, which you commit and review |
| Snapshot copy | `add --copy` | Copies files instead of symlinking them into agent directories |
| Version pin | `npx skills@1.7.4` | Pins the installer, not the skill |

That middle row matters more than it looks: the default is a **symlink** into the source checkout, so
whoever updates that checkout changes what your agent loads, with no diff in your repository. `--copy`
turns the install into a reviewable snapshot. Pick deliberately.

**`--all` does not exist for `add`.** It exists for `remove`. The correct full install is:

```shell
npx skills@1.7.4 add OWNER/REPO -s '*' -a '*'
```

`-s/--skill` and `-a/--agent` both take `*`; a documented `--all` on `add` is a sign the instruction
was written from memory rather than from `--help`.

**Read before you install.** `-l/--list` lists what a repository offers, and
`use OWNER/REPO@SKILL` renders one skill's text without installing anything:

```shell
npx skills@1.7.4 add OWNER/REPO -l
npx skills@1.7.4 use OWNER/REPO@SKILL-NAME
```

**Pin anything vendored.** `git checkout <sha>` and record the SHA in `NOTICE.md`. A marketplace entry
that tracks a branch is a moving supply chain — and so is a skill you symlinked last month.

## Before you adopt a skill

Popularity is not evidence of usefulness, and this page's own numbers are the proof: the
most-starred repository in the avoid table above has 226,677 stars and one unlicensed file. Published
benchmarks disagree with each other as well — some report large gains from curated skills, others
find most engineering skills change nothing. The only measurement that applies to you is on your own
tasks.

A protocol that costs an afternoon:

1. **Pick 5-10 real tasks** from your actual work, including at least two easy ones. Losses cluster
   on easy tasks: an agent that already succeeds does not need a process imposed on it.
2. **Record a baseline.** Same model, same settings, no skill. Note success, number of turns, and
   rough token use.
3. **Run the same tasks with the skill installed.** Change one variable.
4. **Compare, and be willing to lose.** A skill that costs 40% more tokens for no quality change is a
   negative, even if its README claims otherwise.
5. **Repeat on a second model if you use one.** Skill effects transfer between models poorly, so a
   win on one model is not a win on another.
6. **Keep the decision per project.** A skill is a deployment decision, not a portable asset.

Two failure modes to watch for specifically:

- **Two methodologies at once.** Two process skills on the same change give the agent two sources of
  truth about what to do next. Pick one per project.
- **Silent scope creep.** A style skill that changes formatting should not also be shipping twenty
  scripts and four hooks — one of the entries above does exactly that.

## Re-verifying this page

These commands reproduce the table above for any repository:

```shell
gh api repos/OWNER/REPO/git/trees/HEAD?recursive=1 \
  --jq '[.tree[].path | select(test("SKILL.md$"))] | length'

gh api "repos/OWNER/REPO/commits?since=$(date -u -d '90 days ago' +%FT%TZ)&per_page=100" --jq length

gh api repos/OWNER/REPO/contents/PATH/TO/SKILL.md --jq .content | base64 -d | head -12
```

To check existence, archival, and license drift for everything listed here in one pass:

```shell
python3 scripts/check-skill-sources.py
```

That script runs weekly in CI against `data/skill-sources.json`. It fails if a listed repository has
been deleted or archived, and warns if one has gone quiet or changed license.

## Maintenance policy

Numbers here are a snapshot, not a live dashboard. When updating:

1. Edit `data/skill-sources.json` first — it is the source of truth for CI.
2. Update the tables on this page to match.
3. Bump the snapshot date at the top of both.

If you add a repository, run the three verification commands above and record what you actually saw.
An entry without measured numbers does not belong on this page.
