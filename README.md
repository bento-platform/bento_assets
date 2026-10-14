# bento_assets


Bento instances are customized with branding, translations and configuration files.

Each instance has specific public assets tailored to its specific needs, this repository is used to maintain, publish 
and distribute these assets as versionned container images in GHCR.

This allows Bento to treat assets as code, and to distribute said assets into container runtimes natively (Docker, Kubernetes).

Each instance gets its own image, `ghcr.io/bento-platform/bento-assets-<instance>`.

## Layout

```
instances/<name>/lib/            mirrors Bento's lib/ and is copied over it as-is
manifest.json                    files each service needs, and where the service reads them
scripts/install.py               the images' entrypoint: copies a service's files into its volume
scripts/validate.py              checks instances against manifest.json and JSON syntax
Dockerfile                       builds one instance's image: --build-arg INSTANCE=<name>
```

To add a client, copy `instances/dev/` (Bento's stock defaults), replace the files and open a PR. CI runs `python3 scripts/validate.py <name>`, which you can also run locally.

Each `manifest.json` entry gives a file's `source` under `lib/`, its `target` in the service's container, and whether it is `optional`.
The entries follow the `lib/` mounts of Bento `main` (bento_public 1.1.0); update them when a Bento release changes those mounts.

> [!NOTE]
> French assets (logos and translations) are optional since these are not needed on 
> every instance.
>
> TODO: to consider adding per-instance manifest overrides so we can mark French assets 
> as required where it applies (e.g. BQC19, PCGL).

## Release

| Event                                            | Instances built               | Tags                  |
| ------------------------------------------------ | ----------------------------- | --------------------- |
| Merge to `main`                                  | changed since the last commit | `edge`, `sha-<short>` |
| PR to `main`                                     | changed by the PR             | `pr-<N>`              |
| Release `<instance>-<x.y.z>` (e.g. `dev-26.0.0`) | that instance                 | `x.y.z`, `x.y`, `x`   |

Changing `Dockerfile`, `LICENSE`, `manifest.json`, `scripts/install.py` or the build workflow rebuilds every instance.

## Versioning

Release tags are `<instance>-<major>.<minor>.<patch>`:
- **major**: the Bento release the assets are for, e.g. `26` for Bento v26
- **minor**: content changes, such as new branding, translations or config
- **patch**: small fixes, such as a typo or a corrected image

For example: `dev-26.0.0`, then `dev-26.1.0` (new logo), `dev-26.1.1` (typo fix), then `dev-27.0.0` once `manifest.json` targets Bento v27.

When a Bento release changes its mounts, update `manifest.json` (and `instances/dev/` if needed) in one PR, then release each instance with the new major.

To patch an older Bento instance after `main` has moved on, fix it on a `bento-v26` branch created from the last v26 commit, and publish the release (e.g. `dev-26.1.2`) with its tag on that branch: the release is built from the tagged commit.

Deployments can pin the major tag (e.g. `bento-assets-dev:26`) to follow the latest assets for their Bento release, or a full version to stay fixed.

## Using the entrypoint to copy files to volumes

The entrypoint copies the given services' files to the `target` paths in `manifest.json`. Run it as an init container, with a volume mounted where the files belong, then mount the same volume in the service's container:

```shell
docker run --rm -v public-assets:/bento-public/dist/public ghcr.io/bento-platform/bento-assets-dev:26 public
```

- It overwrites existing files and skips missing optional ones. It fails on an unknown service or a missing required file.
- Mount a volume at each destination, otherwise the copied files are lost with the init container.
- Bento Public's assets share directories with the image's own files, so mount them one by one (`subpath` / `subPath`). Beacon's `/config` can be mounted whole.

## Deploy

### Docker Compose

```yaml
x-public-asset: &public-asset
  type: volume
  source: public-assets
  read_only: true

services:
  assets:
    image: ghcr.io/bento-platform/bento-assets-dev:26
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

Katsu and Beacon follow the same pattern: add them to the `assets` command (`[public, katsu, beacon]`) with a volume each, mounted at `/app/chord_metadata_service` and `/config`.
`volume.subpath` needs Docker Engine 26 or later. `bentoctl` does not use these images yet.

### Kubernetes

Pod spec of a Bento Public deployment:

```yaml
spec:
  initContainers:
    - name: assets
      image: ghcr.io/bento-platform/bento-assets-dev:26
      args: [public]
      volumeMounts:
        - name: assets
          mountPath: /bento-public/dist/public
  containers:
    - name: bento-public
      image: ghcr.io/bento-platform/bento_public:1.1.0
      volumeMounts:
        - {name: assets, subPath: en_about.html, mountPath: /bento-public/dist/public/en_about.html, readOnly: true}
        - {name: assets, subPath: fr_about.html, mountPath: /bento-public/dist/public/fr_about.html, readOnly: true}
        - {name: assets, subPath: assets/branding.png, mountPath: /bento-public/dist/public/assets/branding.png, readOnly: true}
        - {name: assets, subPath: assets/branding.fr.png, mountPath: /bento-public/dist/public/assets/branding.fr.png, readOnly: true}
        - {name: assets, subPath: assets/branding.lightbg.png, mountPath: /bento-public/dist/public/assets/branding.lightbg.png, readOnly: true}
        - {name: assets, subPath: assets/branding.lightbg.fr.png, mountPath: /bento-public/dist/public/assets/branding.lightbg.fr.png, readOnly: true}
        - {name: assets, subPath: assets/icon_small.png, mountPath: /bento-public/dist/public/assets/icon_small.png, readOnly: true}
        - {name: assets, subPath: styles/instance.css, mountPath: /bento-public/dist/public/styles/instance.css, readOnly: true}
        - {name: assets, subPath: locales/en/translation_en.json, mountPath: /bento-public/dist/public/locales/en/translation_en.json, readOnly: true}
        - {name: assets, subPath: locales/fr/translation_fr.json, mountPath: /bento-public/dist/public/locales/fr/translation_fr.json, readOnly: true}
  volumes:
    - name: assets
      emptyDir: {}
```

The init container runs for each new pod, so changing the image tag rolls out new assets.

With ArgoCD and the image updater controller, we can automatically update the deployed assets for minor and patch versions 
simply by publishing a new assets image.