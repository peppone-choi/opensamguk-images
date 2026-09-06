#!/usr/bin/env python3
"""Verify every top-level entry has a declared license boundary.

Fails when:
  - a tracked top-level entry is missing from .license-boundaries.json
  - a declared entry no longer exists
  - a third-party or owner-accepted entry is missing its directory-local notice file
  - an owner-accepted entry is missing accepted_by / accepted_on
  - an entry uses an unknown classification

Run: python3 tools/check-license-boundaries.py
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# 'mit'            : the repository's own work, covered by the root LICENSE.
# 'third-party'    : not covered by the root LICENSE and not used by the product.
# 'owner-accepted' : third-party material the repository owner has explicitly accepted
#                    responsibility for using in the OpenSamguk product (opensamguk
#                    ADR-LITE-048). Still not covered by the root LICENSE.
CLASSIFICATIONS = {"mit", "third-party", "owner-accepted"}


def main() -> int:
    manifest = json.loads((ROOT / ".license-boundaries.json").read_text())
    declared = {e["path"]: e for e in manifest["entries"]}

    tracked = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    ).stdout.decode()
    actual = {p.split("/", 1)[0] for p in tracked.split("\0") if p}

    errors = []
    for path in sorted(actual - declared.keys()):
        errors.append(
            f"{path}: undeclared top-level entry — add it to .license-boundaries.json "
            f"as 'mit' (own work), 'third-party' or 'owner-accepted' (both with a notice file)"
        )
    for path in sorted(declared.keys() - actual):
        errors.append(f"{path}: declared in .license-boundaries.json but not tracked in git")

    for path, entry in sorted(declared.items()):
        classification = entry["classification"]
        if classification not in CLASSIFICATIONS:
            errors.append(
                f"{path}: unknown classification {classification!r} "
                f"(expected one of {sorted(CLASSIFICATIONS)})"
            )
            continue
        if classification == "mit":
            continue
        notice = entry.get("notice")
        if not notice:
            errors.append(f"{path}: {classification} entry must declare a 'notice' file")
        elif not (ROOT / notice).exists():
            errors.append(f"{path}: notice file missing: {notice}")
        if classification == "owner-accepted":
            for key in ("accepted_by", "accepted_on"):
                if not entry.get(key):
                    errors.append(f"{path}: owner-accepted entry must declare '{key}'")

    if errors:
        print("license boundary check FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"license boundary check OK ({len(declared)} top-level entries declared)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
