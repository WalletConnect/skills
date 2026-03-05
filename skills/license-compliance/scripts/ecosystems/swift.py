"""Swift: Package.resolved extractor + GitHub lookup."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

from github_api import extract_github_org_repo, lookup_github_license


def find_package_resolved(project_path: Path) -> Optional[Path]:
    """Find Swift Package.resolved in common locations."""
    candidates = [
        project_path / "Package.resolved",
        project_path / ".package.resolved",
    ]
    # Also search in Xcode workspace locations
    for xcodeproj in project_path.glob("**/*.xcodeproj"):
        candidates.append(
            xcodeproj / "project.xcworkspace" / "xcshareddata" / "swiftpm" / "Package.resolved"
        )
    for xcworkspace in project_path.glob("**/*.xcworkspace"):
        candidates.append(
            xcworkspace / "xcshareddata" / "swiftpm" / "Package.resolved"
        )
    # Return the first existing file
    for c in candidates:
        if c.exists():
            return c
    return None


def extract_licenses_swift(project_path: Path) -> list[dict]:
    """Extract licenses from Swift Package.resolved (v1/v2/v3).

    Parses all Package.resolved files found, deduplicates, and looks up
    licenses via the GitHub API.
    """
    resolved_files = []
    # Collect all Package.resolved files
    candidates = [
        project_path / "Package.resolved",
        project_path / ".package.resolved",
    ]
    for xcodeproj in project_path.glob("**/*.xcodeproj"):
        candidates.append(
            xcodeproj / "project.xcworkspace" / "xcshareddata" / "swiftpm" / "Package.resolved"
        )
    for xcworkspace in project_path.glob("**/*.xcworkspace"):
        candidates.append(
            xcworkspace / "xcshareddata" / "swiftpm" / "Package.resolved"
        )
    for c in candidates:
        if c.exists():
            resolved_files.append(c)

    if not resolved_files:
        return []

    # Parse all resolved files and collect unique pins
    seen = set()
    pins = []  # list of (identity, version, url)

    for rf in resolved_files:
        try:
            with open(rf) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        version_num = data.get("version", 0)
        raw_pins = []

        if version_num == 1:
            # V1: pins are under "object.pins"
            raw_pins = data.get("object", {}).get("pins", [])
        else:
            # V2/V3: pins at top level
            raw_pins = data.get("pins", [])

        for pin in raw_pins:
            if version_num == 1:
                identity = pin.get("package", "").lower()
                url = pin.get("repositoryURL", "")
            else:
                identity = pin.get("identity", "")
                url = pin.get("location", "")

            state = pin.get("state", {})
            version = state.get("version", "") or ""
            branch = state.get("branch", "")

            key = (identity, version or branch or "unknown")
            if key in seen:
                continue
            seen.add(key)
            pins.append({
                "identity": identity,
                "version": version or branch or "unknown",
                "url": url,
            })

    if not pins:
        return []

    # Look up licenses via GitHub API
    packages = []
    print(f"  Looking up {len(pins)} Swift package licenses via GitHub API...", file=sys.stderr)
    resolved_count = 0

    for pin in pins:
        gh = extract_github_org_repo(pin["url"])
        license_str = "UNKNOWN"
        if gh:
            lic = lookup_github_license(gh[0], gh[1])
            if lic:
                license_str = lic
                resolved_count += 1

        packages.append({
            "name": pin["identity"],
            "version": pin["version"],
            "license": license_str,
            "is_dev": False,  # SPM doesn't distinguish dev deps in Package.resolved
        })

    print(f"  Resolved {resolved_count}/{len(pins)} licenses via GitHub", file=sys.stderr)
    return packages
