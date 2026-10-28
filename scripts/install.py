#!/usr/bin/env python3
"""
Copies an instance's assets for the given services to the paths those services read them from.

Sources and destinations are determined by the manifest.json file.

By default, files are copied to their manifest `target` paths (init container mode).
If ASSETS_LIB_DIR is set, files are copied under that directory using their `source` paths,
which mirror Bento's lib/ layout (Docker Compose / bentoctl mode).

Every required file is checked before copying, so nothing is copied if one is missing.

Uses Python standard library packages only, making it possible to build ARM arch images
without QEMU emulation for speedup.
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

MANIFEST = Path(os.environ.get("ASSETS_MANIFEST", "/assets/manifest.json"))
SOURCE_DIR = Path(os.environ.get("ASSETS_SOURCE", "/assets/lib"))
ASSETS_LIB_DIR = os.environ.get("ASSETS_LIB_DIR")


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "services",
        # pick 0 or n services by name
        nargs="*",
        choices=manifest.keys(),
        # all services by default
        default=manifest.keys(),
        metavar="SERVICE",
        help=f"Ignore for all, or one of: {', '.join(manifest)}",
    )
    args = parser.parse_args()

    # First pass: resolve copies and check that every required file exists
    copies = []
    issues = []
    for service in args.services:
        for file in manifest[service]:
            source = SOURCE_DIR / file["source"]
            if not source.is_file():
                if not file.get("optional", False):
                    issues.append(
                        f"Error: {service} could not find required file {file['source']}"
                    )
                continue

            if ASSETS_LIB_DIR:
                # mirror Bento's lib/ layout
                target = Path(ASSETS_LIB_DIR) / file["source"]
            else:
                # path in the service's container
                target = Path(file["target"])
            copies.append((source, target))

    if ASSETS_LIB_DIR and not Path(ASSETS_LIB_DIR).is_dir():
        issues.append(
            f"Error: ASSETS_LIB_DIR {ASSETS_LIB_DIR} is not a mounted directory"
        )

    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1

    # Second pass: copy
    for source, target in copies:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        except OSError as e:
            print(
                f"Error: could not copy {source} to {target}: {e.strerror}",
                file=sys.stderr,
            )
            if not ASSETS_LIB_DIR:
                print(
                    "hint: set ASSETS_LIB_DIR to copy under a mounted Bento lib/ directory "
                    "instead of the container target paths",
                    file=sys.stderr,
                )
            return 1
        print(f"{source.relative_to(SOURCE_DIR)} -> {target}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
