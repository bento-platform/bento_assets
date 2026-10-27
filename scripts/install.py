#!/usr/bin/env python3
"""
Copies an instance's assets for the given services to the paths those services read them from.

Sources and destinations are determined by the manifest.json file.

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
USE_TARGET_LIB = os.environ.get("USE_LIB_TARGET", "False").lower() in (
    "true",
    "1",
    "yes",
)
TARGET_LIB_DIR = Path("/target-lib")


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

    issues = []
    for service in args.services:
        for file in manifest[service]:
            source = SOURCE_DIR / file["source"]
            if USE_TARGET_LIB:
                # preserve source structure
                target = TARGET_LIB_DIR / file["source"]
            else:
                # use container target path
                target = Path(file["target"])

            if not source.is_file():
                if file.get("optional", False):
                    continue
                issues.append(
                    f"Error: {service} could not find required file {file['source']}"
                )

            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            print(f"{file['source']} -> {target}")

    # Print issues and return 1 if any
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
