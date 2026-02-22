"""Go: go.sum + GitHub module mapping."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from github_api import lookup_github_license


def _parse_go_sum(project_path: Path) -> list[dict]:
    """Parse go.sum for module dependencies.

    Returns list of {"name": ..., "version": ..., "module_path": ...}.
    Deduplicates module paths (go.sum has hash lines we skip).
    """
    go_sum = project_path / "go.sum"
    if not go_sum.exists():
        return []

    seen = set()
    deps = []

    try:
        for line in go_sum.read_text().splitlines():
            parts = line.strip().split()
            if len(parts) < 3:
                continue
            module_path = parts[0]
            version = parts[1]
            # Skip /go.mod hash lines and duplicates
            if version.endswith("/go.mod"):
                continue
            if module_path in seen:
                continue
            seen.add(module_path)

            deps.append({
                "name": module_path,
                "version": version.lstrip("v"),
                "module_path": module_path,
            })
    except OSError:
        pass

    return deps


def _go_module_to_github(module_path: str) -> Optional[tuple[str, str]]:
    """Convert a Go module path to a GitHub (owner, repo) tuple.

    Handles github.com/org/repo and golang.org/x/... paths.
    """
    if module_path.startswith("github.com/"):
        parts = module_path.split("/")
        if len(parts) >= 3:
            return parts[1], parts[2]
    # golang.org/x/* maps to github.com/golang/*
    if module_path.startswith("golang.org/x/"):
        name = module_path.split("/")[2]
        return "golang", name
    # google.golang.org/* -> github.com/googleapis/*  (approximation)
    # Most other registries don't have a clean mapping
    return None


def extract_licenses_go(project_path: Path) -> tuple[list[dict], bool, int]:
    """Extract licenses from Go project.

    Parses go.sum, extracts GitHub org/repo from module paths, looks up licenses
    via GitHub API.

    Returns (packages, is_monorepo, workspace_count).
    """
    deps = _parse_go_sum(project_path)
    if not deps:
        # Try go.mod only (no go.sum)
        return [], False, 0

    # Filter to external deps (skip stdlib and local modules)
    external = [d for d in deps if "." in d["module_path"].split("/")[0]]

    if not external:
        return [], False, 0

    # Count workspaces via go.work
    workspace_count = 0
    go_work = project_path / "go.work"
    if go_work.exists():
        try:
            for line in go_work.read_text().splitlines():
                stripped = line.strip()
                if stripped.startswith("use ") or (stripped and stripped != ")" and stripped != "use ("):
                    if stripped not in ("use (", ")") and not stripped.startswith("//"):
                        workspace_count += 1
        except OSError:
            pass
    is_monorepo = workspace_count > 1

    print(f"  Looking up {len(external)} Go module licenses via GitHub...", file=sys.stderr)
    packages = []
    resolved_count = 0

    for dep in external:
        license_str = "UNKNOWN"
        gh = _go_module_to_github(dep["module_path"])
        if gh:
            lic = lookup_github_license(gh[0], gh[1])
            if lic:
                license_str = lic
                resolved_count += 1

        packages.append({
            "name": dep["name"],
            "version": dep["version"],
            "license": license_str,
            "is_dev": False,
        })

    print(f"  Resolved {resolved_count}/{len(external)} licenses via GitHub", file=sys.stderr)
    return packages, is_monorepo, workspace_count
