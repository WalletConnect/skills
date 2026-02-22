"""Solidity: .gitmodules + Foundry."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from github_api import extract_github_org_repo, lookup_github_license


def _parse_gitmodules(project_path: Path) -> list[dict]:
    """Parse .gitmodules for git submodule dependencies (common in Foundry projects).

    Returns list of {"name": ..., "url": ..., "path": ...}.
    """
    gitmodules = project_path / ".gitmodules"
    if not gitmodules.exists():
        return []

    modules = []
    current = {}

    try:
        for line in gitmodules.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("[submodule"):
                if current:
                    modules.append(current)
                name = stripped.split('"')[1] if '"' in stripped else ""
                current = {"name": name, "url": "", "path": ""}
            elif "=" in stripped and current is not None:
                key, val = stripped.split("=", 1)
                key = key.strip()
                val = val.strip()
                if key == "url":
                    current["url"] = val
                elif key == "path":
                    current["path"] = val
    except OSError:
        return []

    if current:
        modules.append(current)

    return modules


def extract_licenses_solidity(project_path: Path) -> tuple[list[dict], bool, int]:
    """Extract licenses from Solidity/Foundry projects.

    Checks three sources:
    1. Git submodules (.gitmodules) — common for Foundry lib/ deps
    2. npm (package.json) — some Solidity projects use npm
    3. Foundry remappings (foundry.toml)

    Returns (packages, is_monorepo, 0).
    """
    all_packages = []
    seen = set()

    # 1. Git submodules (Foundry standard)
    # Check both project dir and parent (for monorepo subprojects)
    submodules = _parse_gitmodules(project_path)
    if not submodules and project_path.parent != project_path:
        submodules = _parse_gitmodules(project_path.parent)
    if submodules:
        github_subs = [s for s in submodules if extract_github_org_repo(s.get("url", ""))]
        if github_subs:
            print(f"  Looking up {len(github_subs)} Foundry submodule licenses via GitHub...", file=sys.stderr)
            resolved = 0
            for sub in github_subs:
                gh = extract_github_org_repo(sub["url"])
                license_str = "UNKNOWN"
                if gh:
                    lic = lookup_github_license(gh[0], gh[1])
                    if lic:
                        license_str = lic
                        resolved += 1
                name = sub["name"] or sub["path"] or sub["url"]
                if name not in seen:
                    seen.add(name)
                    all_packages.append({
                        "name": name,
                        "version": "submodule",
                        "license": license_str,
                        "is_dev": False,
                    })
            print(f"  Resolved {resolved}/{len(github_subs)} submodule licenses via GitHub", file=sys.stderr)

    # 2. Check for npm deps (some Solidity projects use npm for OpenZeppelin etc.)
    pkg_json = project_path / "package.json"
    if pkg_json.exists():
        try:
            with open(pkg_json) as f:
                data = json.load(f)
            for dep_section in ("dependencies", "devDependencies"):
                for name in data.get(dep_section, {}):
                    if name not in seen:
                        seen.add(name)
                        # We'll leave these as UNKNOWN — the npm registry lookup
                        # in classify_packages will resolve them
                        all_packages.append({
                            "name": name,
                            "version": data[dep_section][name].lstrip("^~>="),
                            "license": "UNKNOWN",
                            "is_dev": dep_section == "devDependencies",
                        })
        except (json.JSONDecodeError, OSError):
            pass

    return all_packages, False, 0
