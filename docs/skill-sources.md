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

`100+` means the 90-day commit query hit its pagination cap: at least 100 commits.

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
| Security (defensive) | `cloudflare/security-audit-skill` | 1 | Validators and tests |
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
| [`morluto/rea`](https://github.com/morluto/rea) | 408,964 | 5 `SKILL.md` against **5,983 scripts** plus `native/` and `patches/`. An application, not a skill. |
| [`paperclipai/paperclip`](https://github.com/paperclipai/paperclip) | 108,752 | 85 skills, **7,914 scripts**, Docker runtime. An app. |
| [`mksglu/context-mode`](https://github.com/mksglu/context-mode) | 32,875 | `NOASSERTION` license, **132 hook files**, pre-release tags only. |
| [`msitarzewski/agency-agents`](https://github.com/msitarzewski/agency-agents) | 165,233 | **0 `SKILL.md`** — these are subagent personas, not skills. |
| [`Leonxlnx/taste-skill`](https://github.com/Leonxlnx/taste-skill) | 105,744 | Description says skills (plural); the tree contains one. |

Also note: [`anthropics/claude-plugins-official`](https://github.com/anthropics/claude-plugins-official)
(Apache-2.0, 33 skills) bundles `external_plugins/` for Discord, iMessage, and Telegram with
`access` and `configure` skills. That is messaging-account access by design — install it only if that
is what you are deliberately setting up.

## Security notes

**Hooks execute; `SKILL.md` does not.** Before installing a repository, count its hooks. Verified at
snapshot: 132 in `context-mode`, 38 in `awesome-copilot`, 9 in `addyosmani/agent-skills`, 6 in
`superpowers`. Read every hook file and know what it runs.

**Script count is the surface area.** Measured: 5,983 in `rea`, 7,914 in `paperclip`, 831 in
`alirezarezvani/claude-skills`, 776 in `K-Dense-AI`, 432 in `last30days`. A repository with zero
scripts (`kepano/obsidian-skills`) is a different risk class from one with thousands.

**Prefer skills that declare their tools.** `last30days` sets `allowed-tools: Bash, Read, Write,
AskUserQuestion, WebSearch` in front matter. Silence about tools is not a safety claim.

**Install project-scoped, not global.** `.agents/skills/` in a project beats `~/.agents/skills/`.
Run agents that load third-party skills in a container or devcontainer, with a credential-free shell.

**Pin everything.** `npx skills@VERSION add`, and `git checkout <sha>` for anything vendored. A plugin
marketplace entry that tracks a branch is a moving supply chain.

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
