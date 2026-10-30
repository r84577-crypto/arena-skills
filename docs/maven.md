# Publish and install Maven packages with GitHub Packages

> **Source:** GitHub Docs — [Working with the Apache Maven registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-apache-maven-registry) (CC BY 4.0).
> **Snapshot:** 2026-10-30. Re-check upstream before relying on limits or behaviour.

You can configure Apache Maven to publish packages to GitHub Packages and to resolve them as dependencies in a Java project.

## Prerequisites

- Maven installed and a project with a `pom.xml`.
- A token — see [Authenticating to GitHub Packages](authenticating.md).
- The feed URL: `https://maven.pkg.github.com/OWNER/REPOSITORY`.

> [!IMPORTANT]
> The `OWNER` segment must be **lowercase**. Uppercase letters are rejected even when the GitHub account or organization legitimately contains them.

## Authenticate Maven

Edit `~/.m2/settings.xml` (create it if missing). Credentials live in `<servers>`; the repository is declared in a profile and mapped to those credentials by `id`:

```xml
<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.0.0
                      http://maven.apache.org/xsd/settings-1.0.0.xsd">

  <activeProfiles>
    <activeProfile>github</activeProfile>
  </activeProfiles>

  <profiles>
    <profile>
      <id>github</id>
      <repositories>
        <repository>
          <id>central</id>
          <url>https://repo.maven.apache.org/maven2</url>
        </repository>
        <repository>
          <id>github</id>
          <url>https://maven.pkg.github.com/OWNER/REPOSITORY</url>
          <snapshots>
            <enabled>true</enabled>
          </snapshots>
        </repository>
      </repositories>
    </profile>
  </profiles>

  <servers>
    <server>
      <id>github</id>
      <username>YOUR_GITHUB_USERNAME</username>
      <password>${env.GITHUB_PAT}</password>
    </server>
  </servers>
</settings>
```

Two things to keep right:

- The `<server><id>` **must** equal the `<repository><id>` it authenticates. A typo produces a `401` that looks like a bad token.
- Passing the token as `${env.GITHUB_PAT}` keeps it out of the file. If you inline it instead, keep `settings.xml` out of version control.

To consume packages from more than one owner, add a `<repository>` per owner, each with a matching `<server>` entry.

## Publish a package

GitHub publishes to the repository whose name matches the package by default — a package named `com.example:test` lands in `OWNER/test`. To publish to a different repository, set `distributionManagement` in the `pom.xml`; GitHub matches on that element, so multiple packages can share one repository with no extra configuration.

> [!WARNING]
> The `artifactId` must contain **only lowercase letters, digits, or hyphens**. Uppercase letters fail the publish with `422 Unprocessable Entity`. This is a Maven naming-convention rule, not a GitHub quirk — see [Naming conventions](https://maven.apache.org/guides/mini/guide-naming-conventions.html).

1. Add the distribution target:

   ```xml
   <distributionManagement>
     <repository>
       <id>github</id>
       <name>GitHub OWNER Apache Maven Packages</name>
       <url>https://maven.pkg.github.com/OWNER/REPOSITORY</url>
     </repository>
   </distributionManagement>
   ```

2. Deploy:

   ```shell
   mvn deploy
   ```

As with every registry here, the first publish is **private**; set visibility and access per package — see [Configuring a package's access control and visibility](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility).

## Install a package

1. Authenticate as described above.
2. Add the dependency:

   ```xml
   <dependencies>
     <dependency>
       <groupId>com.example</groupId>
       <artifactId>test</artifactId>
       <version>1.0.0-SNAPSHOT</version>
     </dependency>
   </dependencies>
   ```

3. Resolve:

   ```shell
   mvn install
   ```

To pull from any repository owned by one account, use the wildcard feed URL `https://maven.pkg.github.com/OWNER/*`.

## `SNAPSHOT` versions

`SNAPSHOT` artifacts are supported. Enable snapshots on the consuming side — either `<snapshots><enabled>true</enabled></snapshots>` on the repository in the POM, or in the profile inside `settings.xml` as shown above. Snapshots that are disabled on the consumer produce a resolution failure that looks like a missing artifact rather than a policy problem.

## Further reading

- [Working with the Gradle registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-gradle-registry)
- [Deleting and restoring a package](https://docs.github.com/en/packages/learn-github-packages/deleting-and-restoring-a-package)
- [Authenticating to GitHub Packages](authenticating.md)
