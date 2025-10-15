#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "manifests" / "targets.json"

def load_manifest(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)

def retag(source: str, target: str, repo: str, dry_run: bool = False) -> None:
    command = [
        "docker",
        "buildx",
        "imagetools",
        "create",
        "--tag",
        f"{repo}:{target}",
        f"{repo}:{source}",
    ]
    if dry_run:
        print("DRY-RUN:", " ".join(command))
        return

    subprocess.run(command, check=True)

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Update Docker Hub channel alias tags")
    parser.add_argument("--repo", default="miget/container-os")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    manifest = load_manifest(MANIFEST_PATH)

    for alias, cfg in manifest.get("channels", {}).items():
        os_name = cfg.get("os")
        version = cfg.get("version")
        engine = cfg.get("engine")

        os_versions = manifest.get("targets", {}).get(os_name, {})
        if not version or version not in os_versions:
            print(f"Skipping alias {alias}: version {version} not found")
            continue

        alias_patch = os_versions[version]["alias_patch"]
        source_tag = f"{manifest['version']}-{os_name}-{alias_patch}-{engine}"
        retag(source_tag, alias, args.repo, dry_run=args.dry_run)

    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
