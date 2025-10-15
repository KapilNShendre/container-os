# Copyright 2025 Miget (https://miget.com)
# Licensed under the Apache License, Version 2.0

.PHONY: help build verify update-versions update-readme update-all clean

help:
	@echo "Miget Container OS - Local Development Commands"
	@echo ""
	@echo "Available targets:"
	@echo "  make build-and-verify  - Build all images, verify packages, update manifests and README"
	@echo "  make update-versions   - Fetch latest package versions from upstream"
	@echo "  make update-readme     - Update README component versions table"
	@echo "  make render            - Render Dockerfiles from templates"
	@echo "  make clean             - Remove test images"
	@echo ""

build-and-verify:
	@python3 scripts/build_and_verify.py

update-versions:
	@echo "Fetching latest package versions..."
	@python3 scripts/update_manifest_versions.py
	@echo "Rendering Dockerfiles..."
	@python3 scripts/render_dockerfiles.py
	@echo "Updating README..."
	@python3 scripts/update_readme_table.py
	@echo "✓ All manifests updated"

update-readme:
	@python3 scripts/update_readme_table.py

render:
	@python3 scripts/render_dockerfiles.py

clean:
	@echo "Removing test images..."
	@docker images | grep "miget/container-os:test-" | awk '{print $$3}' | xargs -r docker rmi -f
	@echo "✓ Cleaned up test images"
