# Publish and install NuGet packages with GitHub Packages

> **Source:** GitHub Docs — [Working with the NuGet registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-nuget-registry) (CC BY 4.0).
> **Snapshot:** 2026-10-30. Re-check upstream before relying on limits or behaviour.

You can configure the `dotnet` CLI to publish NuGet packages to GitHub Packages and to consume packages from it as dependencies, exactly like `nuget.org`.

## Prerequisites

- A .NET SDK. The examples below use `net8.0`; substitute your current target framework.
- A token — see [Authenticating to GitHub Packages](authenticating.md) for which one to use.
- The feed URL for your account or organization: `https://nuget.pkg.github.com/NAMESPACE/index.json`.

## Authenticate the `dotnet` CLI

Add the feed as a named source. This writes the credential into your user-level NuGet config, so the token stays out of the repository:

```shell
dotnet nuget add source \
  --username YOUR_GITHUB_USERNAME \
  --password "$GITHUB_PAT" \
  --store-password-in-clear-text \
  --name github \
  "https://nuget.pkg.github.com/NAMESPACE/index.json"
```

> [!WARNING]
> `--store-password-in-clear-text` writes the token to `~/.nuget/NuGet/NuGet.Config` in plaintext. That is tolerable on an ephemeral CI runner and a poor idea on a shared workstation. On a workstation, prefer a credential provider or scope the token to `read:packages` only. On a runner, always pass the token through an environment variable or secret — never inline it in a committed file.

If you would rather scope credentials to one repository, commit a `nuget.config` like this one instead — but keep the token out of it (this example reads an environment variable, substituted before the file is used):

```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <add key="github" value="https://nuget.pkg.github.com/NAMESPACE/index.json" />
  </packageSources>
  <packageSourceCredentials>
    <github>
      <add key="Username" value="YOUR_GITHUB_USERNAME" />
      <add key="ClearTextPassword" value="%GITHUB_PAT%" />
    </github>
  </packageSourceCredentials>
</configuration>
```

> [!NOTE]
> Do not add `<clear />` unless you intend to make GitHub Packages your only feed. Clearing the source list removes `nuget.org`, which breaks restore for every public dependency — and produces the intermittent `403` behaviour described under [Troubleshooting](#intermittent-403s-when-restoring-public-packages).

## Publish a package

The `nupkg` archive for a single version must be **smaller than 2.147 GB**.

When you first publish, the package is **private**. Visibility and access are configured per package — see [Configuring a package's access control and visibility](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility).

If your `.csproj` sets `RepositoryUrl`, the published package is linked to that repository automatically, and the link is how GitHub matches packages to repos. The owner in `RepositoryUrl` must match the `NAMESPACE` in your feed URL.

### With a token as the API key

1. Create and pack the project:

   ```shell
   dotnet new console --name PROJECT_NAME
   dotnet pack --configuration Release
   ```

2. Push, using the token as the API key:

   ```shell
   dotnet nuget push "bin/Release/PROJECT_NAME.1.0.0.nupkg" \
     --api-key "$GITHUB_PAT" \
     --source "github"
   ```

   `--source "github"` refers to the source name you registered above. If you skipped that step, pass the feed URL directly instead.

### With a `nuget.config` source

1. Set the package identity and the repository link in the `.csproj`:

   ```xml
   <Project Sdk="Microsoft.NET.Sdk">

     <PropertyGroup>
       <OutputType>Exe</OutputType>
       <TargetFramework>net8.0</TargetFramework>
       <PackageId>PROJECT_NAME</PackageId>
       <Version>1.0.0</Version>
       <Authors>AUTHORS</Authors>
       <Company>COMPANY_NAME</Company>
       <PackageDescription>PACKAGE_DESCRIPTION</PackageDescription>
       <RepositoryUrl>https://github.com/OWNER/REPOSITORY</RepositoryUrl>
     </PropertyGroup>

   </Project>
   ```

2. Pack and push:

   ```shell
   dotnet pack --configuration Release
   dotnet nuget push "bin/Release/PROJECT_NAME.1.0.0.nupkg" --source "github"
   ```

## Publish multiple packages to one repository

GitHub matches a package to a repository through the `RepositoryUrl` field, so give every project the **same** URL:

```xml
<PropertyGroup>
  <TargetFramework>net8.0</TargetFramework>
  <PackageId>MY_APP</PackageId>
  <Version>1.0.0</Version>
  <RepositoryUrl>https://github.com/my-org/my-repo</RepositoryUrl>
</PropertyGroup>
```

Repeat with a different `PackageId` for each package you want attached to `my-org/my-repo`.

## Install a package

1. Authenticate as described above.
2. Add a `PackageReference` to the consuming `.csproj`:

   ```xml
   <ItemGroup>
     <PackageReference Include="PACKAGE_NAME" Version="X.X.X" />
   </ItemGroup>
   ```

3. Restore:

   ```shell
   dotnet restore
   ```

## Troubleshooting

### Intermittent 403s when restoring public packages

If you use GitHub Packages alongside `nuget.org`, you may see intermittent `403 Forbidden` responses while restoring unrelated public packages such as `Microsoft.Extensions.*`. NuGet queries **every** configured source for **every** package, so a transient GitHub Packages auth failure can block a restore that needs nothing from GitHub.

The fix is [package source mapping](https://learn.microsoft.com/en-us/nuget/consume-packages/package-source-mapping), which routes each package pattern to exactly one source:

```xml
<configuration>
  <packageSources>
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" />
    <add key="github" value="https://nuget.pkg.github.com/NAMESPACE/index.json" />
  </packageSources>
  <packageSourceMapping>
    <packageSource key="nuget.org">
      <package pattern="*" />
    </packageSource>
    <packageSource key="github">
      <package pattern="PACKAGE-ID-PREFIX.*" />
    </packageSource>
  </packageSourceMapping>
</configuration>
```

NuGet applies the [most specific matching pattern](https://learn.microsoft.com/en-us/nuget/consume-packages/package-source-mapping#package-pattern-precedence), so `PACKAGE-ID-PREFIX.*` resolves only from GitHub Packages and everything else only from `nuget.org`. Add one `<package>` entry per prefix you host. As a side effect this also closes the dependency-confusion hole where a public feed could satisfy a private package name.

### `GITHUB_TOKEN` cannot see another repository's packages

Expected. A workflow token only reaches packages belonging to the repository that runs the workflow. Use a classic PAT with `read:packages`, or grant the repository read access on the package — see [Cross-repository access](authenticating.md#cross-repository-access).

## Further reading

- [Deleting and restoring a package](https://docs.github.com/en/packages/learn-github-packages/deleting-and-restoring-a-package)
- [Connecting a repository to a package](https://docs.github.com/en/packages/learn-github-packages/connecting-a-repository-to-a-package)
