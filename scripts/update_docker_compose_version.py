#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

try:
    import requests
except ImportError:
    print("Error: requests library not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
TARGETS_PATH = ROOT / "manifests" / "targets.json"
PACKAGE_VERSIONS_PATH = ROOT / "manifests" / "package_versions.json"

def get_latest_docker_compose_version() -> str:
    url = "https://api.github.com/repos/docker/compose/releases/latest"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data["tag_name"]

def update_manifest_file(path: Path, version: str) -> bool:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    
    old_version = data.get("docker_compose_version", "")
    if old_version == version:
        print(f"{path.name}: Already at {version}")
        return False
    
    data["docker_compose_version"] = version
    
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    
    print(f"{path.name}: Updated {old_version} → {version}")
    return True

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Update docker-compose version from GitHub releases"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check for updates without modifying files",
    )
    args = parser.parse_args(argv)
    
    try:
        latest_version = get_latest_docker_compose_version()
        print(f"Latest docker-compose version: {latest_version}")
        
        if args.check_only:
            return 0
        
        updated = False
        for path in [TARGETS_PATH, PACKAGE_VERSIONS_PATH]:
            if path.exists():
                if update_manifest_file(path, latest_version):
                    updated = True
        
        if updated:
            print("\nVersion updated successfully!")
            return 0
        else:
            print("\nNo updates needed.")
            return 0
            
    except requests.RequestException as e:
        print(f"Error fetching latest version: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
