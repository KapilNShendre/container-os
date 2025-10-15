#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "manifests" / "targets.json"

def load_manifest() -> Dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

def clean_version(version: str) -> str:
    return version.replace(".", "")

def build_channel_map(manifest: Dict) -> Dict[tuple, List[str]]:
    mapping: Dict[tuple, List[str]] = defaultdict(list)
    for alias, cfg in manifest.get("channels", {}).items():
        key = (cfg["os"], cfg.get("version"), cfg.get("engine"))
        mapping[key].append(alias)
    return mapping

def os_alias(os_name: str, version_key: str) -> str:
    if os_name == "ubuntu":
        major = version_key.split(".")[0]
        return f"ubuntu{major}"
    if os_name == "alpine":
        return f"alpine{version_key}"
    raise ValueError(f"Unsupported OS '{os_name}'")

def latest_version_map(manifest: Dict) -> Dict[str, str]:
    latest: Dict[str, str] = {}
    for os_name, versions in manifest.get("targets", {}).items():
        sorted_versions = sorted(versions.keys(), key=lambda v: [int(part) for part in v.split(".")])
        latest[os_name] = sorted_versions[-1]
    return latest

def compose_tags(
    manifest_version: str,
    os_name: str,
    version_key: str,
    alias_patch: str,
    engine: str,
    latest_versions: Dict[str, str],
) -> List[str]:
    tags: List[str] = []
    alias = os_alias(os_name, version_key)

    tags.append(f"{manifest_version}-{os_name}-{alias_patch}-{engine}")

    tags.append(f"{manifest_version}-{alias}-{engine}")

    if engine == "dockerd":
        tags.append(f"{manifest_version}-{alias}")
        tags.append(alias)

        if version_key == latest_versions[os_name]:
            if os_name == "ubuntu":
                tags.append("latest")
            elif os_name == "alpine":
                tags.append("latest-alpine")

    return list(dict.fromkeys(tags))

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate build matrix for Docker images")
    parser.add_argument(
        "--dockerhub-repo",
        default="miget/container-os",
        help="Docker Hub repository namespace (default: miget/container-os)",
    )
    args = parser.parse_args()

    manifest = load_manifest()
    channel_map = build_channel_map(manifest)
    latest_versions = latest_version_map(manifest)
    build_definitions = []

    for os_name, versions in manifest.get("targets", {}).items():
        for version_key, metadata in versions.items():
            alias_patch = metadata.get("alias_patch", version_key)
            for engine in ("dockerd", "podman"):
                dockerfile_path = ROOT / "dockerfiles" / os_name / version_key / f"{engine}.Dockerfile"
                if not dockerfile_path.exists():
                    continue

                base_tags = compose_tags(
                    manifest["version"],
                    os_name,
                    version_key,
                    alias_patch,
                    engine,
                    latest_versions,
                )
                base_tags.extend(channel_map.get((os_name, version_key, engine), []))
                base_tags = list(dict.fromkeys(base_tags))

                dockerhub_tags = [f"{args.dockerhub_repo}:{tag}" for tag in base_tags]
                combined_tags = "\n".join(dockerhub_tags)

                build_definitions.append(
                    {
                        "os": os_name,
                        "version": version_key,
                        "engine": engine,
                        "dockerfile": str(dockerfile_path.relative_to(ROOT)),
                        "tags": base_tags,
                        "dockerhub_tags": dockerhub_tags,
                        "combined_tags": combined_tags,
                        "platforms": "linux/amd64,linux/arm64",
                    }
                )

    matrix = {"include": build_definitions}
    print(json.dumps(matrix))

if __name__ == "__main__":
    main()
