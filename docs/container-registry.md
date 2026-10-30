# Publish and install container images with the GitHub Packages container registry

> **Source:** GitHub Docs — [Working with the container registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry) (CC BY 4.0).
> **Snapshot:** 2026-10-30. Re-check upstream before relying on limits or behaviour.

The container registry stores Docker and OCI images at `ghcr.io`, scoped to an organization or personal account, and optionally linked to a repository.

## About the registry

- Images live under `ghcr.io/NAMESPACE/IMAGE_NAME`.
- Visibility, access, and permission inheritance work like every other GitHub Packages registry.
- **Public images can be pulled anonymously** — no token at all.
- Image names must be **lowercase**. An owner or repository with uppercase letters will fail the push; lowercase the whole path.

Supported formats:

- [Docker Image Manifest V2, Schema 2](https://docs.docker.com/registry/spec/manifest-v2-2/)
- [Open Container Initiative (OCI) specifications](https://github.com/opencontainers/image-spec)

Foreign layers, such as those in Windows base images, are supported.

## Authenticate with `docker login`

1. Create a token with `read:packages` (pull), `write:packages` (push), and `delete:packages` (delete) — see [Authenticating to GitHub Packages](authenticating.md).
2. Export it rather than pasting it into a command:

   ```shell
   export CR_PAT=YOUR_TOKEN
   ```

3. Log in, reading the token from stdin so it stays out of shell history:

   ```shell
   echo "$CR_PAT" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
   ```

## Push an image

Tag and push. The image must already be tagged with the full `ghcr.io` path:

```shell
docker tag hello_docker ghcr.io/NAMESPACE/IMAGE_NAME:latest
docker push ghcr.io/NAMESPACE/IMAGE_NAME:latest
docker push ghcr.io/NAMESPACE/IMAGE_NAME:2.5
```

The first publish is **private**. Set visibility per package afterwards — see [Configuring a package's access control and visibility](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility).

> [!IMPORTANT]
> Pushing from the command line does **not** link the image to a repository by default, even when the namespace matches the repository name. An unlinked package will not accept `GITHUB_TOKEN` from a workflow. The fix is the `org.opencontainers.image.source` label described under [Link an image to a repository](#link-an-image-to-a-repository).

## Pull an image

### By tag

```shell
docker pull ghcr.io/NAMESPACE/IMAGE_NAME:1.14.1
docker pull ghcr.io/NAMESPACE/IMAGE_NAME:latest
```

### By digest

A digest pins the exact image content, which is what you want for reproducibility. It is always `sha256:` followed by **64 lowercase hexadecimal characters**.

1. Find the digest:

   ```shell
   docker inspect --format='{{index .RepoDigests 0}}' ghcr.io/NAMESPACE/IMAGE_NAME:1.14.1
   ```

   The output ends in `@sha256:<digest>`.

2. Pull using the digest — substitute the real value, which must be 64 hex characters:

   ```shell
   docker pull ghcr.io/NAMESPACE/IMAGE_NAME@sha256:<digest>
   ```

   Placeholders in angle brackets are not valid input. A digest copied from documentation, truncated, or containing anything other than `0-9a-f` produces `invalid reference format`.

## Build an image

```shell
docker build -t ghcr.io/NAMESPACE/IMAGE_NAME:latest .
```

The trailing `.` is the build context — `docker build` requires exactly one argument, and omitting it fails with `"docker build" requires exactly 1 argument`.

## Tag an image

```shell
docker images
docker tag 38f737a91f39 ghcr.io/NAMESPACE/NEW_IMAGE_NAME:latest
```

## Label an image

Labels populate the package page and, critically, link the package to its source repository.

| Key | Purpose |
| --- | --- |
| `org.opencontainers.image.source` | URL of the repository the package belongs to — this is what creates the repository link |
| `org.opencontainers.image.description` | Text-only description, 512 characters max, shown on the package page |
| `org.opencontainers.image.licenses` | SPDX license identifier such as `MIT`, 256 characters max; shown in the Details sidebar |

Add them in the `Dockerfile` so they survive every build:

```dockerfile
LABEL org.opencontainers.image.source=https://github.com/octocat/my-repo
LABEL org.opencontainers.image.description="My container image"
LABEL org.opencontainers.image.licenses=MIT
```

Or at build time:

```shell
docker build \
  -t ghcr.io/octocat/my-repo:latest \
  --label "org.opencontainers.image.source=https://github.com/octocat/my-repo" \
  --label "org.opencontainers.image.description=My container image" \
  --label "org.opencontainers.image.licenses=MIT" \
  .
```

### Describe a multi-arch image

A multi-arch image is an index that references one manifest per architecture. The description shown on the package page comes from the `annotations` field of the index, not from Docker labels:

```json
{
  "annotations": {
    "org.opencontainers.image.description": "My multi-arch image"
  }
}
```

The following workflow builds and pushes a multi-arch image with that annotation. It is complete and runnable — including the `permissions` block, without which the push is denied:

```yaml
name: Publish image

on:
  push:
    tags: ["v*"]

permissions:
  contents: read
  packages: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Compute lowercase image name
        id: image
        run: echo "name=ghcr.io/${GITHUB_REPOSITORY,,}" >> "$GITHUB_OUTPUT"

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: docker/build-push-action@v6
        with:
          context: .
          file: ./Dockerfile
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ steps.image.outputs.name }}:${{ github.ref_name }}
          labels: |
            org.opencontainers.image.source=${{ github.server_url }}/${{ github.repository }}
            org.opencontainers.image.description=My multi-arch image
            org.opencontainers.image.licenses=MIT
```

> [!TIP]
> The examples above reference actions by major-version tag for readability. For production workflows, pin them to a full commit SHA with the version in a trailing comment — that is the mitigation GitHub recommends for supply-chain risk in [Security hardening for GitHub Actions](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#using-third-party-actions).

## Link an image to a repository

You can link a package in the UI, or implicitly by publishing from a workflow that uses `GITHUB_TOKEN` (the running repository is linked automatically). From the command line, the `org.opencontainers.image.source` label does it.

One caveat: if a package already exists under a namespace but was never linked, `GITHUB_TOKEN` will not have permission to push a new version to it. Link it once, or push with a PAT, and subsequent workflow pushes work normally.

## Limits

- **10 GB** maximum per layer.
- **10 minute** timeout for uploads.

Layers approaching 10 GB or transfers approaching 10 minutes usually indicate an image that needs splitting or a runner with insufficient upload bandwidth.

## Further reading

- [Authenticating to GitHub Packages](authenticating.md)
- [Publishing and installing a package with GitHub Actions](https://docs.github.com/en/packages/managing-github-packages-using-github-actions-workflows/publishing-and-installing-a-package-with-github-actions)
- [Connecting a repository to a package](connecting-a-repository.md)
