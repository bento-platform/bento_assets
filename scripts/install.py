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


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("services", nargs="+", choices=manifest.keys(), metavar="SERVICE",
                        help=f"one of: {', '.join(manifest)}")
    args = parser.parse_args()

    for service in args.services:
        for file in manifest[service]:
            source = SOURCE_DIR / file["source"]
            target = Path(file["target"])

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
