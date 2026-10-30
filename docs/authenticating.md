# Authenticating to GitHub Packages

> **Source:** GitHub Docs — [Authenticating to GitHub Packages](https://docs.github.com/en/packages/working-with-a-github-packages-registry) (CC BY 4.0).
> **Snapshot:** 2026-10-30. Re-check upstream before relying on token scopes or limits.

Every GitHub Packages registry — `nuget.pkg.github.com`, `maven.pkg.github.com`, `npm.pkg.github.com`, `rubygems.pkg.github.com`, and `ghcr.io` — uses the same three pieces: an identity, a token, and a per-client credential file. This page covers the parts that are common to all of them. Each registry guide links back here for the generic rules and documents its own client configuration.

## Which credential should I use?

| Client | `GITHUB_TOKEN` in Actions | PAT (classic) | Fine-grained PAT |
| --- | --- | --- | --- |
| NuGet | Yes — same repository only | Yes | Check current status (see below) |
| Apache Maven | Yes — same repository only | Yes | Check current status (see below) |
| npm | Yes — same repository only | Yes | Check current status (see below) |
| RubyGems | Yes — same repository only | Yes | Check current status (see below) |
| Container registry (`ghcr.io`) | Yes, with `permissions: packages: write` | Yes | Yes, with the `Packages` permission |

The short version: **in a workflow, prefer `GITHUB_TOKEN`**. Outside a workflow, or when you need to read packages owned by a *different* repository, use a classic PAT with `read:packages` — or a fine-grained PAT where the registry supports it.

## Using `GITHUB_TOKEN` in a workflow

`GITHUB_TOKEN` is created per job and expires when the job ends, so nothing long-lived has to be stored. Two rules matter:

1. The workflow must request permission. Add a `permissions:` block — the default token is read-only for packages:

   ```yaml
   permissions:
     contents: read
     packages: write
   ```

2. The token can only reach packages attached to **the repository running the workflow**. For packages owned by another repository, see [Cross-repository access](#cross-repository-access).

Repositories that publish a package from a workflow are automatically granted `admin` permission on that package, which is what allows workflow-driven delete and restore through the REST API. A package pushed from a developer machine is **not** linked to the repository until you connect it, so `GITHUB_TOKEN` will be denied until that link exists. See [Connecting a repository to a package](connecting-a-repository.md).

> [!NOTE]
> Workflow-driven delete and restore of packages through the REST API has been in public preview. Treat it as subject to change and confirm current behaviour upstream before depending on it.

## Using a personal access token (classic)

Create the token at [github.com/settings/tokens](https://github.com/settings/tokens). The scopes that matter here:

| Scope | Grants |
| --- | --- |
| `read:packages` | Download packages and read their metadata |
| `write:packages` | Upload and download packages, read and write metadata |
| `delete:packages` | Delete package versions |

> [!WARNING]
> In the token UI, selecting `write:packages` also selects `repo` — which grants broad read/write access to every repository you can see. That is far more access than publishing a package needs, and it is dangerous in CI. Create the token from this URL instead, which pre-selects only the packages scope: `https://github.com/settings/tokens/new?scopes=write:packages`

If your organization enforces SAML SSO, authorize the token for the organization after creating it, or every registry call returns `401`.

## Fine-grained personal access tokens

Fine-grained PAT support has rolled out registry by registry rather than all at once. The container registry (`ghcr.io`) accepts a fine-grained token carrying the **Packages** permission; the other registries have historically required a classic token. Do not assume — check the registry's own page in the GitHub Docs before you standardize on fine-grained tokens across a pipeline.

## Cross-repository access

`GITHUB_TOKEN` cannot read packages owned by a different repository, even inside the same organization. The options are:

1. Create a classic PAT with `read:packages` and pass it as a secret. This is the documented workaround and the one most teams use.
2. Explicitly grant the consuming repository read access on the package itself, then keep using `GITHUB_TOKEN`.

## Storing credentials safely

Every client below needs the token written to a config file, and every one of those files is a leak waiting to happen. Rules that apply regardless of registry:

- **Never commit** `nuget.config`, `~/.m2/settings.xml`, `.npmrc`, `~/.gem/credentials`, or a `docker login` credential store. Keep the local file out of git and keep the token in an environment variable or secret.
- **Never put a token in a URL** that gets written to a dotfile or printed — `https://user:TOKEN@host/...` ends up in shell history, in `ps` output, and in the config file permanently. Prefer the client's credential helper or an environment variable.
- **Prefer short expiry.** A classic PAT can be set to expire; do it. Rotate on a schedule rather than waiting for an incident.
- **Revoke, don't delete.** If a token leaks, revoke it at [github.com/settings/tokens](https://github.com/settings/tokens) first, then rotate whatever consumed it.

## Registry guides

- [NuGet](nuget.md)
- [Apache Maven](maven.md)
- [npm](npm.md)
- [RubyGems](rubygems.md)
- [Container registry](container-registry.md)

## Further reading

- [About permissions for GitHub Packages](https://docs.github.com/en/packages/learn-github-packages/about-permissions-for-github-packages)
- [Configuring a package's access control and visibility](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility)
- [Deleting and restoring a package](https://docs.github.com/en/packages/learn-github-packages/deleting-and-restoring-a-package)
