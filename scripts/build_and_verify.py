#!/usr/bin/env python3

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log_step(msg: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}==> {msg}{Colors.ENDC}")

def log_success(msg: str):
    print(f"{Colors.OKGREEN}✓ {msg}{Colors.ENDC}")

def log_warning(msg: str):
    print(f"{Colors.WARNING}⚠ {msg}{Colors.ENDC}")

def log_error(msg: str):
    print(f"{Colors.FAIL}✗ {msg}{Colors.ENDC}")

def run_command(cmd: List[str], capture=True, check=True) -> Tuple[int, str]:
    try:
        if capture:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            return result.returncode, result.stdout.strip()
        else:
            result = subprocess.run(cmd, check=check)
            return result.returncode, ""
    except subprocess.CalledProcessError as e:
        if capture:
            return e.returncode, e.stdout.strip() if e.stdout else ""
        return e.returncode, ""

def load_targets():
    base_dir = Path(__file__).parent.parent
    with open(base_dir / "manifests/targets.json") as f:
        return json.load(f)

def get_image_variants(targets):
    variants = []
    for os_name in ["ubuntu", "alpine"]:
        if os_name not in targets["targets"]:
            continue
        for os_version in sorted(targets["targets"][os_name].keys()):
            for engine in ["dockerd", "podman"]:
                variants.append({
                    "os": os_name,
                    "version": os_version,
                    "engine": engine,
                    "dockerfile": f"dockerfiles/{os_name}/{os_version}/{engine}.Dockerfile",
                    "tag": f"miget/container-os:test-{os_name}-{os_version}-{engine}"
                })
    return variants

def build_image(variant: Dict) -> bool:
    log_step(f"Building {variant['os']} {variant['version']} {variant['engine']}")
    
    base_dir = Path(__file__).parent.parent
    dockerfile = base_dir / variant["dockerfile"]
    
    if not dockerfile.exists():
        log_error(f"Dockerfile not found: {dockerfile}")
        return False
    
    cmd = [
        "docker", "build",
        "-f", str(dockerfile),
        "-t", variant["tag"],
        "."
    ]
    
    returncode, _ = run_command(cmd, capture=False)
    
    if returncode == 0:
        log_success(f"Built {variant['tag']}")
        return True
    else:
        log_error(f"Failed to build {variant['tag']}")
        return False

def get_package_version_ubuntu(container_id: str, package: str) -> str:
    cmd = [
        "docker", "exec", container_id,
        "dpkg-query", "-W", "-f", "${Version}", package
    ]
    returncode, output = run_command(cmd, check=False)
    return output if returncode == 0 else None

def get_package_version_alpine(container_id: str, package: str) -> str:
    cmd = [
        "docker", "exec", container_id,
        "sh", "-c", f"apk list --installed {package} 2>/dev/null | cut -d' ' -f1"
    ]
    returncode, output = run_command(cmd, check=False)
    
    if returncode == 0 and output:
        parts = output.split('-')
        for i, part in enumerate(parts):
            if any(c.isdigit() for c in part):
                return '-'.join(parts[i:])
    return None

def verify_image(variant: Dict, targets: Dict) -> Dict[str, str]:
    log_step(f"Verifying {variant['os']} {variant['version']} {variant['engine']}")
    
    container_name = f"verify-{variant['os']}-{variant['version']}-{variant['engine']}"
    
    run_command(["docker", "rm", "-f", container_name], check=False)
    
    cmd = [
        "docker", "run", "-d",
        "--name", container_name,
        "--privileged",
        variant["tag"],
        "sleep", "infinity"
    ]
    
    returncode, container_id = run_command(cmd)
    if returncode != 0:
        log_error(f"Failed to start container")
        return {}
    
    import time
    time.sleep(2)
    
    os_target = targets["targets"][variant["os"]][variant["version"]]
    packages_to_check = {}
    
    for pkg in os_target["packages"]["common"]:
        packages_to_check[pkg] = "common"
    
    for pkg in os_target["packages"][variant["engine"]]:
        packages_to_check[pkg] = variant["engine"]
    
    verified_versions = {}
    is_ubuntu = variant["os"] == "ubuntu"
    
    for package, section in packages_to_check.items():
        if is_ubuntu:
            version = get_package_version_ubuntu(container_id, package)
        else:
            version = get_package_version_alpine(container_id, package)
        
        if version:
            verified_versions[package] = version
            log_success(f"{package}: {version}")
        else:
            log_warning(f"{package}: not found or failed to query")
    
    run_command(["docker", "rm", "-f", container_name], check=False)
    
    return verified_versions

def update_package_versions(all_versions: Dict):
    base_dir = Path(__file__).parent.parent
    versions_file = base_dir / "manifests/package_versions.json"
    
    with open(versions_file, "r") as f:
        current = json.load(f)
    
    for key, versions in all_versions.items():
        os_name, os_version, section = key.split(":")
        
        if os_name not in current:
            current[os_name] = {}
        if os_version not in current[os_name]:
            current[os_name][os_version] = {}
        if section not in current[os_name][os_version]:
            current[os_name][os_version][section] = {}
        
        current[os_name][os_version][section].update(versions)
    
    with open(versions_file, "w") as f:
        json.dump(current, f, indent=2)
        f.write("\n")
    
    log_success("Updated package_versions.json")

def main():
    base_dir = Path(__file__).parent.parent
    
    print(f"{Colors.BOLD}Miget Container OS - Build and Verify{Colors.ENDC}")
    print(f"Working directory: {base_dir}\n")
    
    log_step("Loading targets")
    targets = load_targets()
    variants = get_image_variants(targets)
    log_success(f"Found {len(variants)} image variants to build")
    
    log_step("Building all images")
    build_failures = []
    for variant in variants:
        if not build_image(variant):
            build_failures.append(variant)
    
    if build_failures:
        log_error(f"Failed to build {len(build_failures)} images")
        for v in build_failures:
            print(f"  - {v['os']} {v['version']} {v['engine']}")
        sys.exit(1)
    
    log_success(f"Successfully built all {len(variants)} images")
    
    log_step("Verifying package versions in containers")
    all_versions = {}
    
    for variant in variants:
        verified = verify_image(variant, targets)
        
        for package, version in verified.items():
            os_target = targets["targets"][variant["os"]][variant["version"]]
            if package in os_target["packages"]["common"]:
                section = "common"
            else:
                section = variant["engine"]
            
            key = f"{variant['os']}:{variant['version']}:{section}"
            if key not in all_versions:
                all_versions[key] = {}
            all_versions[key][package] = version
    
    log_step("Updating package_versions.json")
    update_package_versions(all_versions)
    
    log_step("Updating README component versions table")
    returncode, _ = run_command(["python3", "scripts/update_readme_table.py"])
    if returncode == 0:
        log_success("Updated README.md")
    else:
        log_error("Failed to update README.md")
    
    log_step("Cleaning up test images")
    for variant in variants:
        run_command(["docker", "rmi", variant["tag"]], check=False)
    log_success("Cleaned up test images")
    
    print(f"\n{Colors.BOLD}{Colors.OKGREEN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKGREEN}All tasks completed successfully!{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKGREEN}{'='*60}{Colors.ENDC}\n")
    
    print("Next steps:")
    print("  1. Review changes: git diff")
    print("  2. Commit changes: git add -A && git commit -m 'chore: update package versions'")
    print("  3. Push to remote: git push")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Interrupted by user{Colors.ENDC}")
        sys.exit(130)
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
