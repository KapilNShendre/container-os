#!/usr/bin/env python3

import json
import sys
from pathlib import Path

def load_json(filepath):
    with open(filepath) as f:
        return json.load(f)

def get_significant_packages():
    return [
        "docker-ce",
        "docker",
        "podman",
        "containerd.io",
        "docker-compose-plugin",
        "docker-cli-compose",
    ]

def check_for_changes():
    base_dir = Path(__file__).parent.parent
    
    versions_file = base_dir / "manifests/package_versions.json"
    current_versions = load_json(versions_file)
    
    targets_file = base_dir / "manifests/targets.json"
    targets = load_json(targets_file)
    
    significant_packages = get_significant_packages()
    changes = []
    
    compose_version = targets.get("docker_compose_version", "")
    if compose_version:
        changes.append({
            "type": "docker-compose",
            "version": compose_version
        })
    
    for os_name, os_versions in current_versions.items():
        if os_name == "docker_compose_version":
            continue
            
        for os_version, sections in os_versions.items():
            for section, packages in sections.items():
                if not isinstance(packages, dict):
                    continue
                    
                for package, version in packages.items():
                    if package in significant_packages:
                        changes.append({
                            "type": "package",
                            "os": os_name,
                            "os_version": os_version,
                            "section": section,
                            "package": package,
                            "version": version
                        })
    
    return changes

def main():
    changes = check_for_changes()
    
    if changes:
        print("Significant changes detected:")
        for change in changes:
            if change["type"] == "docker-compose":
                print(f"  - Docker Compose: {change['version']}")
            else:
                print(f"  - {change['os']} {change['os_version']} ({change['section']}): {change['package']} = {change['version']}")
        sys.exit(0)
    else:
        print("No significant changes detected")
        sys.exit(1)

if __name__ == "__main__":
    main()
