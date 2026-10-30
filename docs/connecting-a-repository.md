# Connecting a repository to a package

> **Source:** GitHub Docs — [Connecting a repository to a package](https://docs.github.com/en/packages/learn-github-packages/connecting-a-repository-to-a-package) (CC BY 4.0).
> **Snapshot:** 2026-10-30.

Linking a package to a repository is what makes permission inheritance, the package sidebar, and `GITHUB_TOKEN` access work. An unlinked package is invisible to workflows in the repository you would expect to own it.

## Why the link matters

- A linked package **inherits the repository's access permissions**, so anyone who can read the repo can install the package — and workflows in that repo can publish to it.
- Without a link, `GITHUB_TOKEN` is denied even for a package whose namespace matches the repository name.
- The package page gains a source link, README, and release history.

Automatic inheritance can be disabled by an organization administrator. If a package does not inherit as expected, check the organization setting before debugging tokens.

## Link at publish time

Set the field the registry uses to match package to repository:

| Registry | Field | Example |
| --- | --- | --- |
| NuGet | `RepositoryUrl` in the `.csproj` | `<RepositoryUrl>https://github.com/OWNER/REPOSITORY</RepositoryUrl>` |
| npm | `repository` in `package.json` | `"https://github.com/OWNER/REPOSITORY.git"` |
| Apache Maven | `distributionManagement` URL in `pom.xml` | `https://maven.pkg.github.com/OWNER/REPOSITORY` |
| RubyGems | `github_repo` in `gem.metadata` | `ssh://github.com/OWNER/REPOSITORY` |
| Container | `org.opencontainers.image.source` label | `https://github.com/OWNER/REPOSITORY` |

The match is on the **URL**, so all packages that share one repository must carry an identical value.

## Link an existing package

1. Open the package page: `https://github.com/OWNER?tab=packages`, then select the package.
2. **Package settings** → **Manage repository** (or **Connect repository**).
3. Choose the repository and confirm.

For container images there is also a command-line path: pushing with the `org.opencontainers.image.source` label set links the package on the next publish.

## Verify

```shell
gh api "users/OWNER/packages/container/IMAGE_NAME/versions" --jq '.[0].metadata.container.tags'
```

If the package detail page shows a repository name under the title, the link exists. If it does not, workflows will keep failing with `403` no matter how the token is scoped.
