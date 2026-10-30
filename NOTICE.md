# Notices and attribution

This repository contains two kinds of material under two licenses. The MIT
license in `LICENSE` covers the repository's original content. It does **not**
relicense the GitHub Docs material vendored under `docs/`.

## Vendored documentation

The pages below are derived from GitHub Docs, which is dual-licensed: prose is
CC BY 4.0 and code samples are MIT. They are redistributed here under CC BY 4.0
with attribution. They remain under CC BY 4.0 and are not relicensed by this
repository's MIT license.

| File | Upstream source | License |
| --- | --- | --- |
| `docs/authenticating.md` | [Working with a GitHub Packages registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry) | CC BY 4.0 |
| `docs/nuget.md` | [Working with the NuGet registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-nuget-registry) | CC BY 4.0 |
| `docs/maven.md` | [Working with the Apache Maven registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-apache-maven-registry) | CC BY 4.0 |
| `docs/npm.md` | [Working with the npm registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-npm-registry) | CC BY 4.0 |
| `docs/rubygems.md` | [Working with the RubyGems registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-rubygems-registry) | CC BY 4.0 |
| `docs/container-registry.md` | [Working with the container registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry) | CC BY 4.0 |
| `docs/connecting-a-repository.md` | [Connecting a repository to a package](https://docs.github.com/en/packages/learn-github-packages/connecting-a-repository-to-a-package) | CC BY 4.0 |

**Snapshot date:** 2026-10-30.

> [!IMPORTANT]
> These pages were reorganised and corrected for consistency with this
> repository, but they were **not** re-verified line by line against upstream in
> that pass. Treat upstream as authoritative. Verify token scopes, size limits,
> and API behaviour before relying on them in a pipeline.

## Referenced projects

Not vendored here; linked only.

| Project | License | Usage |
| --- | --- | --- |
| [`cloudflare/security-audit-skill`](https://github.com/cloudflare/security-audit-skill) | MIT | Source of the `skills/<name>/SKILL.md` layout convention |

## Re-syncing a vendored page

1. Open the upstream page listed above and compare it with the local copy.
2. Apply changes, keeping the corrections listed in the pull request that
   introduced this layout (see `git log --follow` on the file).
3. Update the snapshot date in this file and in the page's own header.

## Attribution requirements when reusing this repository

If you redistribute the `docs/` material, keep this file and the source links
with it, and credit GitHub Docs under CC BY 4.0. The `skills/` content and
repository tooling are MIT.
