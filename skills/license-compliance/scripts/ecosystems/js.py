"""JS/TS: pnpm/npm/yarn license extractors."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.parse import quote as urlquote
from urllib.request import urlopen


def lookup_npm_license(pkg_name: str, version: str) -> Optional[str]:
    """Query the npm registry for a package's license field."""
    # Scoped packages need encoding: @scope/pkg -> @scope%2Fpkg
    encoded = urlquote(pkg_name, safe="@")
    safe_ver = urlquote(version, safe='')
    spec = f"{encoded}/{safe_ver}" if version else encoded
    url = f"https://registry.npmjs.org/{spec}"
    try:
        with urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        lic = data.get("license", "")
        if isinstance(lic, dict):
            lic = lic.get("type", "")
        if isinstance(lic, str) and lic and lic not in ("UNLICENSED", "UNKNOWN", "Unknown"):
            return lic
    except (URLError, json.JSONDecodeError, OSError, KeyError):
        pass
    return None


def extract_licenses_pnpm(project_path: Path, prod_only: bool) -> list[dict]:
    """Extract licenses using pnpm licenses list --json."""
    cmd = ["pnpm", "licenses", "list", "--json"]
    if prod_only:
        cmd.append("--prod")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(project_path), timeout=120
        )
    except subprocess.TimeoutExpired:
        print("  Timeout running pnpm licenses list", file=sys.stderr)
        return []
    except FileNotFoundError:
        print("  pnpm not found in PATH", file=sys.stderr)
        return []

    output = result.stdout.strip()
    if not output:
        # pnpm sometimes outputs to stderr on error
        if result.stderr:
            print(f"  pnpm licenses error: {result.stderr.strip()}", file=sys.stderr)
        return []

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        print("  Failed to parse pnpm licenses JSON output", file=sys.stderr)
        return []

    # pnpm returns {"error": {...}} when deps aren't installed
    if "error" in data and isinstance(data["error"], dict):
        msg = data["error"].get("message", "unknown error")
        print(f"  pnpm licenses error: {msg}", file=sys.stderr)
        return []

    # pnpm licenses list --json returns { "license_id": [{ "name": ..., "version": ... }, ...] }
    packages = []
    seen = set()
    for license_id, pkgs in data.items():
        if not isinstance(pkgs, list):
            continue
        for pkg in pkgs:
            name = pkg.get("name", "")
            # pnpm uses "versions" (array) not "version" (string)
            versions = pkg.get("versions", [])
            version = versions[0] if versions else pkg.get("version", "")
            key = (name, version)
            if key in seen:
                continue
            seen.add(key)
            packages.append({
                "name": name,
                "version": version,
                "license": license_id,
                "is_dev": False,  # pnpm --prod handles filtering
            })

    return packages


def extract_licenses_node_modules(project_path: Path, prod_only: bool) -> list[dict]:
    """Extract licenses by walking node_modules directories."""
    nm = project_path / "node_modules"
    if not nm.exists():
        return []

    # Load root devDependencies for dev/prod classification
    dev_deps = set()
    root_pkg = project_path / "package.json"
    if root_pkg.exists():
        try:
            with open(root_pkg) as f:
                pkg = json.load(f)
            dev_deps = set(pkg.get("devDependencies", {}).keys())
        except (json.JSONDecodeError, OSError):
            pass

    packages = []
    seen = set()

    def scan_dir(base: Path) -> None:
        if not base.exists():
            return
        for entry in sorted(base.iterdir()):
            if not entry.is_dir():
                continue
            name = entry.name
            if name.startswith("."):
                continue

            if name.startswith("@"):
                # Scoped package — go one level deeper
                for sub in sorted(entry.iterdir()):
                    if sub.is_dir() and not sub.name.startswith("."):
                        process_pkg(sub, f"{name}/{sub.name}")
            else:
                process_pkg(entry, name)

    def process_pkg(pkg_dir: Path, name: str) -> None:
        pkg_json = pkg_dir / "package.json"
        if not pkg_json.exists():
            return

        try:
            with open(pkg_json) as f:
                pkg = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        # Skip private/workspace packages
        if pkg.get("private", False):
            return

        version = pkg.get("version", "")
        key = (name, version)
        if key in seen:
            return
        seen.add(key)

        # Extract license
        lic = pkg.get("license", "")
        if not lic:
            # Legacy licenses array
            licenses_arr = pkg.get("licenses", [])
            if isinstance(licenses_arr, list) and licenses_arr:
                types = [l.get("type", "") for l in licenses_arr if isinstance(l, dict)]
                lic = " OR ".join(t for t in types if t)

        if isinstance(lic, dict):
            lic = lic.get("type", "")

        is_dev = name in dev_deps
        if prod_only and is_dev:
            return

        packages.append({
            "name": name,
            "version": version,
            "license": str(lic) if lic else "UNKNOWN",
            "is_dev": is_dev,
        })

    scan_dir(nm)
    return packages
