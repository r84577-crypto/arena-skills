# Publish and install gems with GitHub Packages

> **Source:** GitHub Docs — [Working with the RubyGems registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-rubygems-registry) (CC BY 4.0).
> **Snapshot:** 2026-10-30. Re-check upstream before relying on limits or behaviour.

You can publish a gem to GitHub Packages and consume it with Bundler or `gem`.

## Prerequisites

- RubyGems 3.x and Bundler 2.x are the versions this guide is written against. Older releases may still work; they are not tested here.

  ```shell
  gem --version
  bundle --version
  ```

- A token with `write:packages` — see [Authenticating to GitHub Packages](authenticating.md).
- The feed URL: `https://rubygems.pkg.github.com/NAMESPACE`.

## Authenticate RubyGems and Bundler

### For publishing

`gem push` reads credentials from `~/.gem/credentials` and expects the key name to match the `--key` you pass later:

```yaml
---
:github: Bearer YOUR_GITHUB_TOKEN
```

Set the file to owner-only permissions — RubyGems refuses to use it otherwise:

```shell
chmod 0600 ~/.gem/credentials
```

### For installing

Register the registry as a gem source:

```shell
gem sources --add https://rubygems.pkg.github.com/NAMESPACE/
```

> [!WARNING]
> Do not use the historical `https://USERNAME:TOKEN@rubygems.pkg.github.com/NAMESPACE/` form. It writes the token into `~/.gemrc`, into your shell history, and into the process argument list where any local user can read it with `ps`. If you must authenticate a URL, pass the credentials from an environment variable in a shell that does not record history. The same warning applies to `bundle config` with an inline token — prefer a credential file.

With Bundler, configure credentials out of band:

```shell
bundle config https://rubygems.pkg.github.com/NAMESPACE YOUR_GITHUB_USERNAME:YOUR_GITHUB_TOKEN
```

That writes to `~/.bundle/config`; keep that file out of version control.

## Publish a gem

The first publish is **private** — set visibility and access per package afterwards. See [Configuring a package's access control and visibility](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility).

1. Authenticate as described above.
2. Build the gem from its gemspec:

   ```shell
   gem build GEM_NAME.gemspec
   ```

3. Push it, using the `--key` that matches your credentials file:

   ```shell
   gem push --key github \
     --host https://rubygems.pkg.github.com/NAMESPACE \
     GEM_NAME-0.1.0.gem
   ```

   The version in the filename must match the version in the gemspec.

> [!NOTE]
> The uncompressed size of a gem's `metadata.gz` must be **under 2 MB**. A push that exceeds it fails; this usually means the gemspec is accidentally packaging large files (`spec.files` built from `git ls-files`, for example).

## Connect a package to a repository

Include the repository URL in `gem.metadata` so the gem is linked as soon as it is published:

```ruby
spec.metadata = { "github_repo" => "ssh://github.com/OWNER/REPOSITORY" }
```

Linked packages inherit the repository's access permissions, so workflows in that repository get access automatically unless the organization has disabled inheritance. For gems already published, link them in the UI — see [Connecting a repository to a package](connecting-a-repository.md).

## Install a gem

Add a scoped source block so only the gems you name come from GitHub Packages:

```ruby
source "https://rubygems.org"

gem "rails"

source "https://rubygems.pkg.github.com/NAMESPACE" do
  gem "GEM_NAME"
end
```

Then:

```shell
bundle install
```

Bundler 1.7 and later support per-source blocks. On older versions the only option was a global `source` ordering, which is one reason to be on Bundler 2.x.

With `gem` directly, install from the source you registered earlier:

```shell
gem install GEM_NAME --version "0.1.0"
```

## Further reading

- [Authenticating to GitHub Packages](authenticating.md)
- [Make your own gem](https://guides.rubygems.org/make-your-own-gem/) (RubyGems documentation)
- [Deleting and restoring a package](https://docs.github.com/en/packages/learn-github-packages/deleting-and-restoring-a-package)
