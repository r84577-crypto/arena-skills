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

| Skill | Description | License | Status |
| --- | --- | --- | --- |
| _none yet_ | — | — | — |

External skills worth referencing (not vendored here):

| Skill | Description | License |
| --- | --- | --- |
| [`cloudflare/security-audit-skill`](https://github.com/cloudflare/security-audit-skill) | Multi-phase security audits with independently verified, machine-readable findings | MIT |

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

## Vendoring a third-party skill

Do not copy files in silently. Either reference the upstream repository, or vendor it with:

- the upstream URL and the exact commit SHA,
- the upstream license file preserved in the skill directory,
- an entry in [`NOTICE.md`](../NOTICE.md).

Unattributed vendoring is the most common reason these repositories get taken down.
