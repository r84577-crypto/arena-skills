---
name: skill-authoring
description: >
  Writes and repairs SKILL.md files that agents actually discover and load:
  front matter whose name matches the directory, a description written for
  retrieval rather than for style, explicit tool boundaries, and validation
  against the repository checker before the change is proposed. Use when
  creating a new skill, turning existing documentation into a skill, fixing a
  skill that never loads or loads at the wrong time, or reviewing a contributed
  skill. Do not use for writing general documentation or READMEs.
license: MIT
version: 1.0.0
allowed-tools: Read, Write, Bash
---

# Skill authoring

A skill is an instruction set an agent may load mid-task. It competes for attention with
every other skill installed beside it, and it is chosen almost entirely on its
`description`. Write for selection first, style second.

## When to use this

- Creating a new skill directory.
- Converting a runbook, checklist, or doc into a skill.
- A skill exists but never activates, or activates for the wrong requests.

Not for: prose documentation, changelogs, or READMEs.

## The contract

```text
skills/<name>/SKILL.md
```

Front matter, at minimum:

```yaml
---
name: <must equal the directory name>
description: <what it does + exactly when to load it + when not to>
---
```

Rules that break loading when violated:

| Rule | Consequence |
| --- | --- |
| `name` equals the directory name | Discovery by name fails silently |
| `name` is lowercase, digits, hyphens only | Some hosts reject the directory |
| `description` present and specific | The skill is never selected |
| Body starts with an `# H1` | Renders as an untitled fragment |

## Writing the description

The description is the whole retrieval surface. It should contain:

1. **What the skill does** — the artifact or decision it produces.
2. **When to load it** — the phrasings a user would actually type, including near-misses.
3. **When not to** — the adjacent task that belongs to a different skill.

Weak:

```yaml
description: Helps with documentation.
```

Strong:

```yaml
description: >
  Audits a repository for hygiene gaps that block collaboration: license and
  attribution, CI, dead links, stale metadata, credentials. Use when asked to
  review a repository, adopt a dependency, or explain why a project reads as
  abandoned. Do not use for reviewing application code for bugs.
```

The weak version can never win selection: it names no trigger and no boundary. The strong
version names tasks, phrasings, and an explicit exclusion — the exclusion is what stops it
from hijacking adjacent requests.

## Procedure

1. Decide whether this is a skill at all. If it is reference material with no decision or
   procedure, it belongs in `docs/`, not `skills/`.
2. Create `skills/<name>/SKILL.md`. Use `skills/_template/SKILL.md` as the starting point.
3. Write the description using the three-part structure above. Name the near-misses.
4. Write the body for *method*: when to use, procedure, output shape, boundaries.
5. State boundaries explicitly — what may run unattended, what needs confirmation, what it
   must never do. A skill that silently writes files is a defect.
6. Put reference tables and long examples in sibling files and link them relatively.
7. Add the skill to `skills/README.md` and regenerate the index.
8. Validate:

   ```shell
   python3 scripts/validate-skills.py
   ```

9. Fix every error. Read the warnings and fix the ones that matter; a short description or a
   missing retrieval cue usually means the skill will not load.

## Common failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| Never loads | Description has no trigger words | Rewrite with "Use when …" and concrete phrasings |
| Loads for unrelated work | No exclusion clause | Add "Do not use for …" |
| Loads, then ignores instructions | Body is reference prose, not procedure | Convert to ordered steps |
| Validator fails on `name` | Copied template without renaming | Rename directory and front matter together |
| Dead link error | Relative link to a file not shipped | Ship the file or use an absolute URL |

## Boundaries

- May read the repository and write only inside `skills/<name>/`.
- May run the validator and the repository's lint and link checks.
- Must not edit other skills, CI configuration, or `docs/` without being asked.
- Must not add a skill that vendors third-party material without recording its source, commit,
  and license in `NOTICE.md`.

## Validation

`python3 scripts/validate-skills.py` must exit 0 with no errors. CI runs the same command, so a
skill that fails locally will not merge.
