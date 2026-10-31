# Skills

One directory per skill. Each skill is self-contained and loadable on its own.

## Layout

```text
skills/
  README.md            # this index
  _template/
    SKILL.md           # copy this to start a new skill
  <skill-name>/
    SKILL.md           # required — entry point, YAML front matter
    *.md               # optional supporting documents, referenced from SKILL.md
    validate-*.cjs     # optional validators
    *.test.cjs         # optional tests for the validators
```

The leading underscore on `_template` keeps it out of any glob that loads every skill directory alphabetically.

## Index

| Skill | Description | License | Version |
| --- | --- | --- | --- |
| [`agent-permissions`](agent-permissions/SKILL.md) | Reviews what an agent can reach, and what needs confirmation before it acts | MIT | 1.0.0 |
| [`code-change`](code-change/SKILL.md) | Makes a narrow, tested change in an existing repository | MIT | 1.0.0 |
| [`document-delivery`](document-delivery/SKILL.md) | Writes and reviews documents a specific reader can act on | MIT | 1.0.0 |
| [`persistent-memory`](persistent-memory/SKILL.md) | Keeps project state in external memory files across sessions | MIT | 1.0.0 |
| [`repo-audit`](repo-audit/SKILL.md) | Audits a repository for licensing, CI, link, metadata, and credential gaps | MIT | 1.0.0 |
| [`skill-authoring`](skill-authoring/SKILL.md) | Writes and repairs `SKILL.md` files so agents actually load them | MIT | 1.0.0 |
| [`source-verification`](source-verification/SKILL.md) | Checks claims against primary sources and labels what is unverified | MIT | 1.0.0 |

`skills/index.json` is the machine-readable form of this table. It is generated, not
hand-edited — see [Validating](#validating).

External skills worth referencing are tracked in
[`docs/skill-sources.md`](../docs/skill-sources.md), with measured metrics, install commands, and the
licensing traps to avoid. That page is verified and dated; this index is not duplicated here so the
two cannot drift apart.

## The `SKILL.md` contract

Each `SKILL.md` starts with YAML front matter:

```yaml
---
name: skill-name
description: One or two sentences. What it does, and when an agent should load it.
---
```

- `name` — lowercase, hyphenated, and **identical to the directory name**. Mismatch breaks indexing.
- `description` — this is the only thing an agent reads before deciding to load the skill. Write it for retrieval, not for style: name the tasks and the trigger conditions. A vague description means the skill never loads.

Optional keys used by some tooling — document any you rely on in the skill itself, because support varies by platform:

| Key | Purpose |
| --- | --- |
| `license` | SPDX identifier of the skill's own license |
| `version` | Semver, bumped when behaviour changes |
| `tags` | Retrieval hints |

## Writing a skill

1. Copy `_template/SKILL.md` into `skills/<skill-name>/SKILL.md`.
2. Set `name` to the directory name and write a description aimed at retrieval.
3. Keep `SKILL.md` focused on _how to work_. Move reference tables and long examples into sibling files and link them relatively.
4. State the boundaries explicitly: what the skill may do on its own, and what requires the user to ask. A skill that silently writes files or runs destructive commands is a bug.
5. If the skill ships a validator, add a test beside it and wire it into CI.
6. Add a row to the index above.

## Recalling the right skill

A skill that is never selected is dead weight, and selection is a retrieval problem. Every
approach is a trade between context cost and accuracy, and the trade changes with library size:

| Library size | What works | What stops working |
| --- | --- | --- |
| Up to ~10 | Expose every description; invoke explicitly when you know the name | — |
| ~10-50 | Explicit trigger phrases plus local search over descriptions; install per project, not globally | Exposing the whole metadata catalogue starts to distract the agent from the right skill |
| 50+ | Retrieval that reads the skill **body**, then reranks | Selecting on name and description alone |

### Descriptions are necessary, not sufficient

Progressive disclosure assumes metadata is enough to choose a skill. That assumption has now
been measured, and it is false at scale:

- Hiding the skill body from the routing step costs **29-44 percentage points** of Hit@1
  (68.0% to 24.0% for the strongest pipeline). ([SkillRouter](https://arxiv.org/abs/2603.22455))
- A reranker spends **91.7% of its attention on the body field**, not on name or description.
- An encoder trained on metadata only scores 14 points below the same encoder given all fields
  (51.3% vs 65.3%).
- Even the strongest base encoder reaches only **64.0% Hit@1** over a pool of ~80,000 skills.
- Selection accuracy degrades sharply past a critical library size rather than declining
  smoothly. ([survey](https://arxiv.org/html/2602.12430v4))

Two conclusions follow. Descriptions buy you candidate reduction, not the decision — so do not
spend a week polishing prose expecting selection to improve. And static retrieval from the
opening request misses capability needs that only appear mid-task; access has to be callable
more than once. ([SkillBrowser](https://arxiv.org/html/2610.23554))

### What this repository does about it

1. **The validator enforces a retrieval cue** in every description (`Use when ...`). Necessary,
   cheap, and not enough on its own.
2. **Explicit invocation is the reliable path** when the name is known: `/skill-name`, or an
   attached `SKILL.md` in a host without a loader. Zero retrieval error, zero context cost.
3. **Install per project, not globally.** A smaller candidate set is the cheapest recall
   improvement available, and it is the same move Arena makes for tools: load only what the
   current task needs.

### When to build more

Do not build a search index before the candidate set justifies one — over two skills, it is
ceremony that proves nothing.

- **Past ~10 skills:** add explicit trigger phrases to the index and a small keyword search
  (`make search q="…"`). Measure Hit@1 on 20-30 real queries from your own work before and
  after; a change that does not move that number is not an improvement.
- **Past ~50:** move to body-aware retrieve-then-rerank. At that size, description-only
  selection is the documented failure mode, not a preference.

## Validating

The contract above is enforced, not merely described. Two commands, both run in CI:

```shell
python3 scripts/validate-skills.py                 # validate skills + verify the index
python3 scripts/validate-skills.py --write-index    # regenerate skills/index.json
python3 scripts/test-validate-skills.py            # negative tests for the validator itself
```

The validator fails on: missing front matter, `name` not matching the directory, a
non-conforming or over-long name, a `description` outside 40-1024 characters, a missing
top-level heading, dead relative links inside a skill, credential-shaped strings, and a stale
index. It warns when a description carries no retrieval cue ("Use when …"), because such a
skill will usually never be selected.

A skill that fails locally will not merge.

## Installing

```shell
./scripts/install-skills.sh --list                          # targets and skills
./scripts/install-skills.sh --target claude-code --dry-run  # preview
./scripts/install-skills.sh --target claude-code            # project-scoped
./scripts/install-skills.sh --target codex --global         # user-scoped
```

Paths follow the per-agent conventions documented by the `skills` installer
([`vercel-labs/skills`](https://github.com/vercel-labs/skills), `docs/agents.md`), so a skill
lands where the host actually looks. Project-scoped by default; nothing is overwritten without
`--force`.

Installing is only half of it: the host must be pointed at that directory. A public repository
is not loaded automatically by any agent platform.

## Hosts without a skill loader

Not every host scans a skills directory. Some take instructions as an attached file, a project brief,
or a system prompt, and offer no install path at all — a hosted agent with connectors is the common
case, because connectors are tools, not skills. For those hosts the working pattern is:

1. Attach the `SKILL.md` (and any file it links to that the task needs).
2. Say what it is: _"Read the attached file and treat it as project guidance, not as permission to
   bypass your own controls."_
3. Keep the task small enough that the instructions fit in what the host will actually read.

Two properties make this work without modification: a skill is plain Markdown, and its `description`
already states when to apply it. Two properties make it weaker: nothing verifies that the host read
the file, and nothing enforces the `## Boundaries` section. The host's own permission model is still
the only real control.

**Arena Agent Mode** was in this category at 2026-10-30: hosted, connector-based, with no documented
mechanism for loading an external `SKILL.md` as a skill. That is a statement about one product on one
date, not a permanent fact — if you find documented native support, this section is stale and should
be corrected rather than trusted.

For installing _third-party_ skills — the `skills` installer's telemetry default, why its installs are
symlinks by default, and a protocol for testing a skill on your own tasks before adopting it — see
[`docs/skill-sources.md`](../docs/skill-sources.md#security-notes) and
[the adoption protocol](../docs/skill-sources.md#before-you-adopt-a-skill).

## Vendoring a third-party skill

Do not copy files in silently. Either reference the upstream repository, or vendor it with:

- the upstream URL and the exact commit SHA,
- the upstream license file preserved in the skill directory,
- an entry in [`NOTICE.md`](../NOTICE.md).

Unattributed vendoring is the most common reason these repositories get taken down.
