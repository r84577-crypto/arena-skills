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
| [`repo-audit`](repo-audit/SKILL.md) | Audits a repository for licensing, CI, link, metadata, and credential gaps | MIT | 1.0.0 |
| [`skill-authoring`](skill-authoring/SKILL.md) | Writes and repairs `SKILL.md` files so agents actually load them | MIT | 1.0.0 |

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
