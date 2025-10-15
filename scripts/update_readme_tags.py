#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
README_PATH = ROOT / "README.md"
MANIFEST_PATH = ROOT / "manifests" / "targets.json"
DOCKERFILES_DIR = ROOT / "dockerfiles"

HEADER = "## Supported tags and respective Dockerfiles"

@dataclass
class Flavor:
    os_name: str
    version: str
    engine: str
    tags: List[str]
    dockerfile: Path

def load_manifest() -> Dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

def build_tags(manifest: Dict, os_name: str, version: str, engine: str, alias_patch: str) -> List[str]:
    def os_alias() -> str:
        if os_name == "ubuntu":
            return f"ubuntu{version.split('.')[0]}"
        if os_name == "alpine":
            return f"alpine{version}"
        raise ValueError(f"Unsupported OS {os_name}")

    manifest_version = manifest["version"]
    latest_versions = {
        name: sorted(versions.keys(), key=lambda v: [int(part) for part in v.split('.')])[-1]
        for name, versions in manifest["targets"].items()
    }

    alias = os_alias()
    tags = [
        f"{manifest_version}-{os_name}-{alias_patch}-{engine}",
        f"{manifest_version}-{alias}-{engine}",
    ]

    if engine == "dockerd":
        tags.extend([
            f"{manifest_version}-{alias}",
            alias,
        ])
        if version == latest_versions[os_name]:
            if os_name == "ubuntu":
                tags.append("latest")
            elif os_name == "alpine":
                tags.append("latest-alpine")

    for alias_name, cfg in manifest.get("channels", {}).items():
        if (
            cfg.get("os") == os_name
            and cfg.get("version") == version
            and cfg.get("engine") == engine
        ):
            tags.append(alias_name)

    seen = set()
    ordered: List[str] = []
    for tag in tags:
        if tag not in seen:
            ordered.append(tag)
            seen.add(tag)
    return ordered

def collect_flavors(manifest: Dict) -> List[Flavor]:
    flavors: List[Flavor] = []
    for os_name, versions in manifest["targets"].items():
        for version, info in versions.items():
            alias_patch = info["alias_patch"]
            for engine in ("dockerd", "podman"):
                dockerfile = DOCKERFILES_DIR / os_name / version / f"{engine}.Dockerfile"
                if not dockerfile.exists():
                    continue
                tags = build_tags(manifest, os_name, version, engine, alias_patch)
                flavors.append(Flavor(os_name, version, engine, tags, dockerfile.relative_to(ROOT)))
    return flavors

def render_flavor(flavor: Flavor) -> str:
    title_os = flavor.os_name.capitalize()
    title_engine = flavor.engine
    if flavor.os_name == "alpine":
        title_os = "Alpine"
    elif flavor.os_name == "ubuntu":
        title_os = "Ubuntu"

    title = f"**{title_os} {flavor.version} {title_engine}**"
    tags_line = ", ".join(f"`{tag}`" for tag in flavor.tags)
    dockerfile_link = f"[`{flavor.dockerfile}`]({flavor.dockerfile})"
    return f"- {title}\n\n  {tags_line}\n  ({dockerfile_link})\n"

def update_readme(flavors: List[Flavor]) -> None:
    content = README_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"{re.escape(HEADER)}\n(?:.*\n)*?(?=\n## )",
        re.MULTILINE,
    )

    flavors_text = "\n".join(render_flavor(flavor) for flavor in flavors)
    replacement = f"{HEADER}\n\n{flavors_text}\n"

    if pattern.search(content):
        updated = pattern.sub(replacement, content)
    else:
        updated = content.replace(HEADER, replacement)

    README_PATH.write_text(updated, encoding="utf-8")

def main() -> None:
    manifest = load_manifest()
    flavors = collect_flavors(manifest)
    update_readme(flavors)

if __name__ == "__main__":
    main()
