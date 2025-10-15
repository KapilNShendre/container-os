#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Tuple

ROOT = Path(__file__).resolve().parent.parent
TARGETS_PATH = ROOT / "manifests" / "targets.json"

def parse_version(version_str: str) -> Tuple[int, int, int]:
    parts = version_str.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version_str}")
    return tuple(int(p) for p in parts)

def bump_patch(version_str: str) -> str:
    major, minor, patch = parse_version(version_str)
    return f"{major}.{minor}.{patch + 1}"

def bump_minor(version_str: str) -> str:
    major, minor, patch = parse_version(version_str)
    return f"{major}.{minor + 1}.0"

def bump_major(version_str: str) -> str:
    major, minor, patch = parse_version(version_str)
    return f"{major + 1}.0.0"

def update_version_in_manifest(bump_type: str = "patch", dry_run: bool = False) -> int:
    with TARGETS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    
    old_version = data.get("version", "1.0.0")
    
    if bump_type == "major":
        new_version = bump_major(old_version)
    elif bump_type == "minor":
        new_version = bump_minor(old_version)
    else:
        new_version = bump_patch(old_version)
    
    print(f"Version: {old_version} → {new_version} ({bump_type} bump)")
    
    if dry_run:
        print("(dry-run mode, not writing)")
        return 0
    
    data["version"] = new_version
    
    with TARGETS_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    
    print(f"Updated {TARGETS_PATH.relative_to(ROOT)}")
    return 0

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Bump version in targets.json"
    )
    parser.add_argument(
        "--minor",
        action="store_true",
        help="Bump minor version (1.0.0 -> 1.1.0)",
    )
    parser.add_argument(
        "--major",
        action="store_true",
        help="Bump major version (1.0.0 -> 2.0.0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )
    args = parser.parse_args(argv)
    
    if args.major:
        bump_type = "major"
    elif args.minor:
        bump_type = "minor"
    else:
        bump_type = "patch"
    
    try:
        return update_version_in_manifest(bump_type=bump_type, dry_run=args.dry_run)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
