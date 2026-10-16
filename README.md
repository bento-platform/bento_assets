# bento_assets


Bento instances are customized with branding, translations and configuration files.

Each instance has specific public assets tailored to its specific needs, this repository is used to maintain, publish 
and distribute these assets as versionned container images in GHCR.

This allows Bento to treat assets as code, and to distribute said assets into container runtimes natively (Docker, Kubernetes).

Each instance gets its own image, `ghcr.io/bento-platform/bento-assets-<instance>`.

## Layout

```
.
├── Dockerfile                builds one instance's image: --build-arg INSTANCE=<name>
├── instances                 mirrors Bento's lib/ for specific instances
│   ├── dev
│   ├── pcgl
│   └── ...
├── manifest.json             source -> destination file mappings for specific services
└── scripts
    ├── install.py            the images' entrypoint: copies a service's files into its volume
    └── validate.py           CI validation script, checks instances against manifest.json and JSON syntax
```

**TODO:** remove redudant `/lib` subdir under instance dirs

To add a client, copy `instances/dev/` (Bento's stock defaults), replace the files and open a PR. CI runs `python3 scripts/validate.py <name>`, which you can also run locally.

Each `manifest.json` entry gives a file's `source` under `lib/`, its `target` in the service's container, and whether it is `optional`.

> [!NOTE]
> French assets (logos and translations) are optional since these are not needed on 
> every instance.
>
> TODO: consider adding per-instance manifest overrides so we can mark French assets 
> as required where it applies (e.g. BQC19, PCGL).

## Creating a new instance

Adding a new `bento_assets` image for an instance can be done quickly by following these steps:

1. Create a feature branch from `main` for the new instance's assets
2. Checkout to the branch locally
3. Create a new directory at `instances/<name>`
4. Copy the contents of Bento's `lib/` directory in `instances/<name>`
   -  Can be done via SCP over SSH
5. Run `./scripts/validate.py`, it will print out the files that need to be deleted
   - e.g. service Docker-Compose files
6. Delete files until `./scripts/validate.py` returns no errors
   - Means that the contents of `instances/<name>` matches required files defined in `manifest.json`
7. Commit, push changes and open a PR
8. (Recommended) use the PR build of the image to validate before merging (`bento-assets-<name>:pr-<number>`)
9. Merge once PR is approved
   - Triggers build for `bento-assets-<name>:edge`
10. (Optional) Tag merge commit with semver, see [versioning](#versioning)

## Release

| Event                                                         | Instances built               | Image tags            |
| ------------------------------------------------------------- | ----------------------------- | --------------------- |
| Merge to `main`                                               | changed since the last commit | `edge`, `sha-<short>` |
| Open PR to `main`                                             | changed in the PR             | `pr-<N>`              |
| Release with git tag `<instance>-<x.y.z>` (e.g. `dev-26.0.0`) | tagged instance (e.g. `dev`)  | `x.y.z`, `x.y`, `x`   |

Changing `Dockerfile`, `LICENSE`, `manifest.json`, `scripts/install.py` or the build workflow rebuilds every instance.

## Versioning

Release tags follow the `<instance>-<major>.<minor>.<patch>` pattern:
- **major**: the Bento release the assets are for, e.g. `26` for Bento v26
- **minor**: content changes, such as new branding, translations or config
- **patch**: small fixes, such as a typo or a corrected image

For example: `dev-26.0.0`, then `dev-26.1.0` (new logo), `dev-26.1.1` (typo fix), then `dev-27.0.0` once `manifest.json` targets Bento v27.

When a Bento release changes its mounts, update `manifest.json` (and `instances/dev/` if needed) in one PR, then release each instance with the new major.

Deployments can pin the major tag (e.g. `bento-assets-dev:26`) to follow the latest assets for their Bento release, or a full version to stay fixed.

## Using the entrypoint to copy files to volumes

The entrypoint copies the given services' files to the `target` paths in `manifest.json`. Run it as an init container, with a volume mounted where the files belong, then mount the same volume in the service's container:

```shell
docker run --rm -v public-assets:/bento-public/dist/public ghcr.io/bento-platform/bento-assets-dev:edge public
```

- Overwrites existing files and skips missing optional ones.
- Fails on an unknown service or a missing required file.
- Mount a volume at each destination, otherwise the copied files are lost with the init container.
  - Bento Public's assets share directories with the image's own files, so mount them one by one with sub paths.
  - Beacon's `/config` can be mounted whole.

## Deploy

Katsu and Beacon follow the same pattern: add them to the `assets` command (`[public, katsu, beacon]`) with a volume each, mounted at `/app/chord_metadata_service` and `/config`.

### Kubernetes

Starting with `v0.6.0`, the `stateless-svc` Helm Chart in [bento-helm-charts](https://github.com/bento-platform/bento-helm-charts) has first 
class support for `bento_assets` images in the Helm values' `assets` block.

This block simply templates `initContainers` with volume mounts and entrypoint arguments, offering a simple interface 
to declaratively manage assets with Helm Charts.

```yaml
# stateless-svc values.yaml snippet
assets:
  enabled: true
  image:
    repository: "ghcr.io/bento-platform/bento-assets-dev"
    tag: "edge"
  # Service name for entrypoint script argument (python /assets/install.py <service> )
  # Must be a key in manifest.json, e.g. "public"
  service: "public"
  # Directory the init container writes the service's files into
  mountPath: "/bento-public/dist/public"
  # Files destinations relative to mountPath
  files:
    - en_about.html
    - fr_about.html
    - assets/branding.png
    - assets/branding.fr.png
    - assets/branding.lightbg.png
    - assets/branding.lightbg.fr.png
    - assets/icon_small.png
    - styles/instance.css
    - locales/en/translation_en.json
    - locales/fr/translation_fr.json
```

The init container runs for each new pod, so changing the image tag rolls out new assets automatically.

With ArgoCD and the image updater controller, we can automatically update the deployed assets for minor and patch versions 
simply by publishing a new assets image.

### Docker Compose

```yaml
x-public-asset: &public-asset
  type: volume
  source: public-assets
  read_only: true

services:
  assets:
    image: ghcr.io/bento-platform/bento-assets-dev:edge
    command: [public]
    volumes:
      - public-assets:/bento-public/dist/public

  public:
    image: ghcr.io/bento-platform/bento_public:1.1.0
    depends_on:
      assets:
        condition: service_completed_successfully
    volumes:
      - {<<: *public-asset, volume: {subpath: en_about.html}, target: /bento-public/dist/public/en_about.html}
      - {<<: *public-asset, volume: {subpath: fr_about.html}, target: /bento-public/dist/public/fr_about.html}
      - {<<: *public-asset, volume: {subpath: assets/branding.png}, target: /bento-public/dist/public/assets/branding.png}
      - {<<: *public-asset, volume: {subpath: assets/branding.fr.png}, target: /bento-public/dist/public/assets/branding.fr.png}
      - {<<: *public-asset, volume: {subpath: assets/branding.lightbg.png}, target: /bento-public/dist/public/assets/branding.lightbg.png}
      - {<<: *public-asset, volume: {subpath: assets/branding.lightbg.fr.png}, target: /bento-public/dist/public/assets/branding.lightbg.fr.png}
      - {<<: *public-asset, volume: {subpath: assets/icon_small.png}, target: /bento-public/dist/public/assets/icon_small.png}
      - {<<: *public-asset, volume: {subpath: styles/instance.css}, target: /bento-public/dist/public/styles/instance.css}
      - {<<: *public-asset, volume: {subpath: locales/en/translation_en.json}, target: /bento-public/dist/public/locales/en/translation_en.json}
      - {<<: *public-asset, volume: {subpath: locales/fr/translation_fr.json}, target: /bento-public/dist/public/locales/fr/translation_fr.json}

volumes:
  public-assets:
```