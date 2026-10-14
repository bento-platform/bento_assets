#!/usr/bin/env python3
"""
Checks instances against manifest.json: valid name, required files present, no unlisted files, valid JSON.

Usage: scripts/validate.py [INSTANCE...]   (default: every instance)

Uses Python standard library packages only atm for simplicity.
We may want to include dependencies later, e.g. to validate discovery configs.
Would not impact ARM QEMU builds since this script only validates the assets 
before the build occurs.
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTANCES_DIR = REPO_ROOT / "instances"

# Instance names end up in image names, which GHCR requires to be lowercase
NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def validate(name: str, files: list[dict]) -> list[str]:
    if not NAME_PATTERN.match(name):
        return ["the name may only contain lowercase letters, digits and single hyphens"]

    lib = INSTANCES_DIR / name / "lib"
    if not lib.is_dir():
        return [f"{lib.relative_to(REPO_ROOT)} does not exist"]

    problems = []

    for file in files:
        if not file.get("optional", False) and not (lib / file["source"]).is_file():
            problems.append(f"missing required file lib/{file['source']}")

    listed = {file["source"] for file in files}
    present = {path.relative_to(lib).as_posix() for path in lib.rglob("*") if path.is_file()}
    for path in sorted(present - listed):
        problems.append(f"lib/{path} is not listed in manifest.json")

    for path in sorted(lib.rglob("*.json")):
        try:
            json.loads(path.read_text())
        except ValueError as e:
            problems.append(f"lib/{path.relative_to(lib).as_posix()} is not valid JSON: {e}")

    return problems


def main() -> int:
    manifest = json.loads((REPO_ROOT / "manifest.json").read_text())
    files = [file for service_files in manifest.values() for file in service_files]

    names = sys.argv[1:] or sorted(path.name for path in INSTANCES_DIR.iterdir() if path.is_dir())

    failed = False
    for name in names:
        problems = validate(name, files)
        print(f"{name}: {'OK' if not problems else 'FAILED'}")
        for problem in problems:
            print(f"  {problem}")
        failed = failed or bool(problems)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
