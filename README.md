# arena-skills

A working collection of coding-agent skills, plus a vendored reference for the GitHub Packages registries.

This repository has two halves, and they are deliberately separate:

- **[`skills/`](skills/README.md)** — the actual skills, one directory per skill, each with a `SKILL.md`. This is the part that is meant to be loaded by an agent.
- **[`docs/`](docs/authenticating.md)** — reference material for publishing and consuming packages on GitHub Packages (NuGet, Maven, npm, RubyGems, containers). Useful to humans and to agents, but not itself a skill.
- **[`data/skill-sources.json`](data/skill-sources.json)** — the machine-readable list behind [`docs/skill-sources.md`](docs/skill-sources.md), checked weekly by CI for dead or archived sources.

The two halves are separate because a skill is an instruction set with a defined contract, and copied vendor documentation is not. Mixing them made both harder to use — see [Why this layout](#why-this-layout).

## Contents

### Skills

| Skill | What it does |
| --- | --- |
| [`repo-audit`](skills/repo-audit/SKILL.md) | Audits a repository for licensing, CI, link, metadata, and credential gaps |
| [`skill-authoring`](skills/skill-authoring/SKILL.md) | Writes and repairs `SKILL.md` files so agents actually load them |

`skills/index.json` is the generated manifest; `python3 scripts/validate-skills.py` enforces the
contract and CI runs it on every pull request.

### GitHub Packages reference

| Guide | Covers |
| --- | --- |
| [Authenticating to GitHub Packages](docs/authenticating.md) | Token types, scopes, `GITHUB_TOKEN` permissions, credential hygiene |
| [NuGet](docs/nuget.md) | `dotnet nuget`, `nuget.config`, source mapping, `403` debugging |
| [Apache Maven](docs/maven.md) | `settings.xml`, `distributionManagement`, snapshots, naming rules |
| [npm](docs/npm.md) | Scoped packages, `.npmrc`, `publishConfig`, `npm audit` |
| [RubyGems](docs/rubygems.md) | `~/.gem/credentials`, Bundler sources, gem limits |
| [Container registry](docs/container-registry.md) | `ghcr.io`, digests, labels, multi-arch publishing |
| [Connecting a repository to a package](docs/connecting-a-repository.md) | Linking rules for every registry |
| [Agent Skills: verified source guide](docs/skill-sources.md) | Which skill repositories are worth trusting, with measured metrics and the licensing traps |

## Using a skill

Copy or clone the skill's directory into wherever your agent discovers skills, for example:

```shell
./scripts/install-skills.sh --target claude-code --dry-run   # preview
./scripts/install-skills.sh --target claude-code             # install
```

A skill is self-contained: `SKILL.md` is the entry point, and any supporting files sit beside it.

### What a skill's boundaries mean

Each `SKILL.md` declares `allowed-tools` in its front matter and explains the intent in a
`## Boundaries` section. **These are advisory.** The format has no enforcement mechanism: a
host is free to ignore `allowed-tools` entirely, and none of the agents these skills target
document it as a sandbox. `validate-skills.py` checks that the declaration is well formed and
that a Boundaries section exists and says something specific — it cannot check that anything
honours it.

Treat the boundaries as a statement of what the skill is *designed* to do, and enforce the
real limit at the host: permission prompts, a read-only checkout, or a container. See
[`skills/skill-authoring/SKILL.md`](skills/skill-authoring/SKILL.md#boundaries).

The installer writes to the directory your host actually scans, but installing is not loading —
see [`skills/README.md`](skills/README.md#installing).

## Using the reference docs

Start at [docs/authenticating.md](docs/authenticating.md) — it explains which token you need before any registry-specific step makes sense. Then jump to the registry you are publishing to.

If you are publishing from a workflow, read [the `permissions` block](docs/authenticating.md#using-github_token-in-a-workflow) first; it is the single most common cause of a `403` that looks like a bad token.

## Reference skills

The structure here follows the convention used by [`cloudflare/security-audit-skill`](https://github.com/cloudflare/security-audit-skill) (MIT): a `skills/<name>/` directory with `SKILL.md` front matter, plus supporting documents and optional validators.

If you vendor a third-party skill, record its upstream URL, commit, and license in [NOTICE.md](NOTICE.md) and pin to a specific commit rather than a branch:

```shell
git clone https://github.com/cloudflare/security-audit-skill.git
cd security-audit-skill && git checkout <commit-sha>
```

## Why this layout

The previous revision of this file was a single 1,028-line document: a one-line stub followed by five registry guides copied verbatim from the GitHub Docs, with no license, 73 dead links, and duplicate headings that made every in-page anchor jump to the wrong section. Splitting it fixed those mechanically:

- one page per topic, so anchors are unique;
- links point at `docs.github.com` absolutely instead of resolving to a 404 inside this repository;
- the five copies of the same authentication preamble became one page;
- attribution and license are explicit.

Nothing was thrown away: the previous single-file revision is intact at commit `99eb8cd` (`git show 99eb8cd:README.md`).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Run `make check` before opening a pull request — it runs the same checks as CI, including the skill contract and its test suites.

## License

- Original content in this repository — [`LICENSE`](LICENSE) (MIT).
- Vendored GitHub Docs material under `docs/` — CC BY 4.0, attributed in [NOTICE.md](NOTICE.md). It stays under CC BY 4.0 and is not relicensed by this repository's MIT license.

## Security

Report vulnerabilities privately — see [`SECURITY.md`](SECURITY.md). Conduct expectations are in
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

Do not commit tokens. Every credential file referenced in these docs (`nuget.config`, `settings.xml`, `.npmrc`, `~/.gem/credentials`, Docker credential stores) must stay out of version control — `.gitignore` covers the common cases, and secret scanning with push protection is recommended for any fork of this repository.
