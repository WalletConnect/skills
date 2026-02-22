"""Dart: pubspec + pub.dev API."""

from __future__ import annotations

import glob as globmod
import json
import sys
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.parse import quote as urlquote
from urllib.request import Request, urlopen

from github_api import extract_github_org_repo, lookup_github_license


def lookup_pub_dev_repo(package_name: str) -> Optional[tuple[str, str]]:
    """Look up a Dart package's GitHub repo via pub.dev API.

    Returns (owner, repo) or None.
    """
    url = f"https://pub.dev/api/packages/{urlquote(package_name, safe='')}"
    headers = {"User-Agent": "license-check-scanner/1.0"}
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        # Get repository or homepage URL
        pubspec = data.get("latest", {}).get("pubspec", {})
        for key in ("repository", "homepage"):
            repo_url = pubspec.get(key, "")
            if repo_url and "github.com/" in repo_url:
                gh = extract_github_org_repo(repo_url)
                if gh:
                    return gh
    except (URLError, json.JSONDecodeError, OSError, KeyError):
        pass
    return None


def _parse_pubspec_lock(lock_path: Path) -> list[dict]:
    """Parse pubspec.lock (YAML-like) and extract hosted packages.

    Returns list of {"name": ..., "version": ..., "url": ..., "source": ...}.
    We do minimal YAML parsing to avoid a PyYAML dependency.
    """
    packages = []
    current_name = None
    current = {}

    try:
        lines = lock_path.read_text().splitlines()
    except OSError:
        return []

    in_packages = False

    for line in lines:
        stripped = line.rstrip()
        if stripped == "packages:":
            in_packages = True
            continue
        if not in_packages:
            continue

        # Top-level package name (2-space indent)
        if len(line) > 2 and line[:4] != "    " and line[0] == " " and ":" in stripped:
            # Save previous
            if current_name and current:
                packages.append(current)
            name = stripped.strip().rstrip(":")
            current_name = name
            current = {"name": name, "version": "", "url": "", "source": ""}
            continue

        # Package properties (4+ space indent)
        if current_name and stripped.startswith("    "):
            kv = stripped.strip()
            if kv.startswith("version:"):
                current["version"] = kv.split(":", 1)[1].strip().strip('"')
            elif kv.startswith("source:"):
                current["source"] = kv.split(":", 1)[1].strip().strip('"')
            elif kv.startswith("url:"):
                current["url"] = kv.split(":", 1)[1].strip().strip('"')

    # Last package
    if current_name and current:
        packages.append(current)

    return packages


def _parse_pubspec_yaml_deps(yaml_path: Path) -> list[dict]:
    """Parse a pubspec.yaml for dependency names (minimal YAML parsing).

    Returns list of {"name": ..., "version": ..., "is_dev": bool}.
    """
    deps = []
    try:
        lines = yaml_path.read_text().splitlines()
    except OSError:
        return []

    section = None  # "dependencies" or "dev_dependencies"
    for line in lines:
        stripped = line.rstrip()
        # Top-level section headers
        if stripped == "dependencies:":
            section = "dependencies"
            continue
        elif stripped == "dev_dependencies:":
            section = "dev_dependencies"
            continue
        elif stripped and not stripped[0].isspace() and ":" in stripped:
            section = None
            continue

        if section and stripped.startswith("  ") and not stripped.startswith("    "):
            # This is a dependency entry at 2-space indent
            name_part = stripped.strip()
            if name_part.startswith("#"):
                continue
            if ":" in name_part:
                name = name_part.split(":")[0].strip()
                version_part = name_part.split(":", 1)[1].strip()
                # Skip sdk deps (flutter:, sdk: flutter)
                if name in ("flutter", "flutter_test", "flutter_web_plugins"):
                    continue
                # Version might be inline or a complex spec
                version = version_part.strip("'^~>= \"") if version_part else "latest"
                deps.append({
                    "name": name,
                    "version": version or "latest",
                    "is_dev": section == "dev_dependencies",
                })

    return deps


def extract_licenses_dart(project_path: Path) -> tuple[list[dict], bool, int]:
    """Extract licenses from Dart project.

    First tries pubspec.lock. If not available, falls back to parsing
    pubspec.yaml files (all packages in a workspace).

    Returns (packages, is_monorepo, workspace_count).
    """
    lock_path = project_path / "pubspec.lock"
    all_dep_names = {}  # name -> {"version": ..., "is_dev": bool}
    workspace_count = 0

    if lock_path.exists():
        # Prefer lock file
        raw_pkgs = _parse_pubspec_lock(lock_path)
        hosted = [p for p in raw_pkgs if p["source"] == "hosted"]
        for p in hosted:
            all_dep_names[p["name"]] = {"version": p["version"], "is_dev": False}
    else:
        # No lock file — parse pubspec.yaml files
        # Collect all pubspec.yaml files (root + packages/*)
        yaml_files = []
        root_yaml = project_path / "pubspec.yaml"
        if root_yaml.exists():
            yaml_files.append(root_yaml)
        # Find workspace packages
        for pattern in ("packages/*/pubspec.yaml", "*/pubspec.yaml"):
            for match in sorted(globmod.glob(str(project_path / pattern))):
                p = Path(match)
                if p.exists() and p not in yaml_files:
                    yaml_files.append(p)
                    workspace_count += 1

        for yf in yaml_files:
            for dep in _parse_pubspec_yaml_deps(yf):
                if dep["name"] not in all_dep_names:
                    all_dep_names[dep["name"]] = {
                        "version": dep["version"],
                        "is_dev": dep["is_dev"],
                    }

    if not all_dep_names:
        return [], False, 0

    is_monorepo = workspace_count > 1

    # Filter out internal workspace packages (packages that exist as directories)
    internal_names = set()
    for pattern in ("packages/*/pubspec.yaml", "*/pubspec.yaml"):
        for match in globmod.glob(str(project_path / pattern)):
            try:
                for line in Path(match).read_text().splitlines()[:5]:
                    if line.startswith("name:"):
                        internal_names.add(line.split(":", 1)[1].strip())
                        break
            except OSError:
                pass

    external_deps = {k: v for k, v in all_dep_names.items() if k not in internal_names}

    if not external_deps:
        return [], is_monorepo, workspace_count

    print(f"  Looking up {len(external_deps)} Dart package licenses via pub.dev + GitHub...", file=sys.stderr)
    packages = []
    resolved_count = 0

    for name, info in external_deps.items():
        license_str = "UNKNOWN"
        gh = lookup_pub_dev_repo(name)
        if gh:
            lic = lookup_github_license(gh[0], gh[1])
            if lic:
                license_str = lic
                resolved_count += 1

        packages.append({
            "name": name,
            "version": info["version"],
            "license": license_str,
            "is_dev": info["is_dev"],
        })

    print(f"  Resolved {resolved_count}/{len(external_deps)} licenses via GitHub", file=sys.stderr)
    return packages, is_monorepo, workspace_count
