"""Rust: cargo extractor + crates.io lookup."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.parse import quote as urlquote
from urllib.request import Request, urlopen


def lookup_crates_io_license(name: str, version: str) -> Optional[str]:
    """Query crates.io API for a crate's license field."""
    url = f"https://crates.io/api/v1/crates/{urlquote(name, safe='')}/{urlquote(version, safe='')}"
    try:
        req = Request(url, headers={"User-Agent": "license-check-scanner/1.0"})
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        lic = data.get("version", {}).get("license", "")
        if isinstance(lic, str) and lic and lic not in ("UNKNOWN", "Unknown"):
            return lic
    except (URLError, json.JSONDecodeError, OSError, KeyError):
        pass
    return None


def extract_licenses_cargo(project_path: Path) -> tuple[list[dict], bool, int]:
    """Extract licenses using cargo metadata.

    Returns (packages, is_workspace, workspace_member_count).
    """
    cmd = ["cargo", "metadata", "--format-version=1"]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(project_path), timeout=120
        )
    except subprocess.TimeoutExpired:
        print("  Timeout running cargo metadata", file=sys.stderr)
        return [], False, 0
    except FileNotFoundError:
        print("  cargo not found in PATH", file=sys.stderr)
        return [], False, 0

    if result.returncode != 0:
        print(f"  cargo metadata failed: {result.stderr.strip()[:200]}", file=sys.stderr)
        return [], False, 0

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("  Failed to parse cargo metadata JSON output", file=sys.stderr)
        return [], False, 0

    # Identify workspace members (source is null for local packages)
    workspace_members = set()
    for pkg in data.get("packages", []):
        if pkg.get("source") is None:
            workspace_members.add(pkg.get("id", ""))

    is_workspace = len(workspace_members) > 1
    packages = []
    seen = set()

    for pkg in data.get("packages", []):
        # Skip workspace members (local packages, not third-party deps)
        if pkg.get("source") is None:
            continue

        name = pkg.get("name", "")
        version = pkg.get("version", "")
        key = (name, version)
        if key in seen:
            continue
        seen.add(key)

        license_str = pkg.get("license") or ""
        packages.append({
            "name": name,
            "version": version,
            "license": license_str if license_str else "UNKNOWN",
            "is_dev": False,  # cargo metadata doesn't distinguish dev deps
        })

    return packages, is_workspace, len(workspace_members)
