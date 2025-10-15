#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
MANIFEST_PATH = ROOT / "manifests" / "targets.json"
PACKAGE_VERSIONS_PATH = ROOT / "manifests" / "package_versions.json"

def load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)

def read_changelog(path: Path) -> List[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()

def write_changelog(path: Path, lines: List[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def format_entry(version: str, notes: List[str]) -> List[str]:
    ts = datetime.utcnow().strftime("%Y-%m-%d")
    entry = [f"## {version} - {ts}"]
    entry.extend(f"- {note}" for note in notes)
    entry.append("")
    return entry

def gather_notes(manifest: Dict, package_versions: Dict) -> List[str]:
    notes: List[str] = []
    
    docker_compose_version = manifest.get("docker_compose_version")
    if docker_compose_version:
        notes.append(f"Standalone docker-compose updated to {docker_compose_version}")
    
    for os_name, versions in manifest.get("targets", {}).items():
        for version_key, metadata in versions.items():
            alias_patch = metadata.get("alias_patch")
            notes.append(
                f"{os_name} {version_key} base updated to {alias_patch}"
            )
            packages = package_versions.get(os_name, {}).get(version_key, {})
            for bucket, pkg_map in packages.items():
                for package, pkg_version in pkg_map.items():
                    notes.append(
                        f"{os_name} {version_key} {bucket}: {package} -> {pkg_version}"
                    )
    return notes

def update_changelog(manifest: Dict, package_versions: Dict, auto: bool) -> None:
    notes = gather_notes(manifest, package_versions)
    if not notes:
        return

    version = manifest.get("version", "0.0.0")
    new_entry = format_entry(version, notes)

    lines = read_changelog(CHANGELOG_PATH)
    if not lines:
        lines = ["# Changelog", ""]

    if auto:
        base = lines[:2]
        rest = lines[2:]
        lines = base + new_entry + rest
    else:
        lines = new_entry + lines

    write_changelog(CHANGELOG_PATH, lines)

def main() -> int:
    parser = argparse.ArgumentParser(description="Update changelog with manifest changes")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    parser.add_argument("--package-versions", default=str(PACKAGE_VERSIONS_PATH))
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args()

    manifest = load_json(Path(args.manifest))
    package_versions = load_json(Path(args.package_versions))

    update_changelog(manifest, package_versions, auto=args.auto)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
