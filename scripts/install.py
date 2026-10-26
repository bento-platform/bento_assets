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
USE_LIB_TARGET = os.environ.get("USE_LIB_TARGET", "False").lower() in ("true", "1", "yes")


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "services",
        # pick 0 or n services by name
        nargs="*",
        choices=manifest.keys(),
        # all services by default
        default=manifest.keys(),
        metavar="SERVICE",
        help=f"Ignore for all, or one of: {', '.join(manifest)}")
    args = parser.parse_args()

    # If USE_LIB_TARGET (default False), copy the files in the structure expected by Bento's ./lib directory.
    # Otherwise, copies the assets to the path that the service container expects.
    # Defined in manifest.json
    target_key = "target_lib" if USE_LIB_TARGET else "target"
    print(f"Target key: {target_key}")

    for service in args.services:
        for file in manifest[service]:
            source = SOURCE_DIR / file["source"]
            target = Path(file[target_key])

            if not source.is_file():
                if file.get("optional", False):
                    continue
                print(f"error: this instance is missing {file['source']}", file=sys.stderr)
                return 1

            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            print(f"{file['source']} -> {target}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
