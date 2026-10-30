# Publish and install npm packages with GitHub Packages

> **Source:** GitHub Docs — [Working with the npm registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-npm-registry) (CC BY 4.0).
> **Snapshot:** 2026-10-30. Re-check upstream before relying on limits or behaviour.

You can configure npm to publish packages to GitHub Packages and to consume them as dependencies in a project.

## Prerequisites

> [!NOTE]
> Package names and scopes must be **lowercase only**, and the published tarball for a single version must be **smaller than 256 MB**.

GitHub Packages only accepts **scoped** npm packages, in the form `@NAMESPACE/PACKAGE-NAME`. If your package is currently named `test` and your account is `octocat`, it becomes `@octocat/test`:

```json
{
  "name": "@octocat/test"
}
```

The scope is not cosmetic — it is how npm routes the request to the right registry.

## Authenticate npm

### Per-user credentials

Add the token to `~/.npmrc`:

```shell
//npm.pkg.github.com/:_authToken=${GITHUB_PAT}
```

Referencing an environment variable keeps the literal token out of the file. Do not commit an `.npmrc` containing a real token.

### Interactive login

On npm CLI 9 and newer, the default login flow opens a browser and does not work against a private registry. Use `--auth-type=legacy` to be prompted instead:

```shell
npm login --scope=@NAMESPACE --auth-type=legacy --registry=https://npm.pkg.github.com
```

You will be prompted for your GitHub username, your token as the password, and an email address.

> [!TIP]
> Scoping the login matters if GitHub Packages is not your default registry and you still want `npm audit` to work. Without `--scope`, the audit calls are sent to GitHub Packages and fail.

## Publish a package

Set the scope mapping in **either** a project `.npmrc` **or** `publishConfig` in `package.json`. A project `.npmrc` is the safer choice: it stops a stray `npm publish` from shipping your private package to the public npmjs.org registry.

Either way, the `repository` field must match your GitHub repository URL — `github.com/my-org/test` must be written as `https://github.com/my-org/test.git` — otherwise the package is published but not linked to the repository.

### Using a local `.npmrc`

1. In the directory containing `package.json`, create `.npmrc`:

   ```ini
   @NAMESPACE:registry=https://npm.pkg.github.com
   ```

2. Commit that file. It contains no secret — only the routing rule.
3. Verify `package.json` has the scoped `name` and the correct `repository`.
4. Publish:

   ```shell
   npm publish
   ```

### Using `publishConfig`

Add the registry to `package.json`:

```json
{
  "name": "@my-org/test",
  "publishConfig": {
    "registry": "https://npm.pkg.github.com"
  }
}
```

This must be valid JSON — no trailing comma after the closing brace, and the entry belongs inside the existing `package.json` object, not in its own snippet file. Then verify `repository` and run `npm publish`.

## Publish multiple packages to one repository

Put the same `repository` value in every `package.json`. GitHub matches packages to the repository by URL:

```json
{
  "repository": "https://github.com/OWNER/REPOSITORY"
}
```

## Install a package

1. Authenticate as described above.
2. Add the scope mapping to the project `.npmrc`:

   ```ini
   @NAMESPACE:registry=https://npm.pkg.github.com
   ```

3. Add the dependency using the **full scoped name**, including the leading `@`:

   ```json
   {
     "dependencies": {
       "@NAMESPACE/PACKAGE_NAME": "1.0.0"
     }
   }
   ```

   Unscoped packages from npmjs.org (`lodash`) and scoped packages from other registries (`@babel/core`) keep their normal names.

4. Install:

   ```shell
   npm install
   ```

### Installing packages from other organizations

By default a single `.npmrc` scope mapping reaches one organization. Add one line per scope:

```ini
@NAMESPACE1:registry=https://npm.pkg.github.com
@NAMESPACE2:registry=https://npm.pkg.github.com
```

## Troubleshooting

- **`404 Not Found` on publish** — the package name is not scoped, or the scope mapping points at npmjs.org.
- **`401 Unauthorized`** — the token is missing, expired, or not authorized for the organization under SAML SSO.
- **`403 Forbidden`, package not linked** — the package exists but the repository is not connected to it. See [Connecting a repository to a package](connecting-a-repository.md).
- **`npm audit` fails with a registry error** — the login was not scoped. Re-run `npm login` with `--scope=@NAMESPACE`.

## Further reading

- [Authenticating to GitHub Packages](authenticating.md)
- [Deleting and restoring a package](https://docs.github.com/en/packages/learn-github-packages/deleting-and-restoring-a-package)
- [Creating a package.json file](https://docs.npmjs.com/creating-a-package-json-file) (npm documentation)
