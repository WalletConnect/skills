"""C#: csproj/Directory.Packages.props + NuGet."""

from __future__ import annotations

import gzip as gzip_mod
import json
import re
import sys
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.parse import quote as urlquote, urlparse
from urllib.request import Request, urlopen


def _parse_csproj_packages(project_path: Path) -> list[dict]:
    """Parse .csproj and Directory.Packages.props for PackageReference entries.

    Returns list of {"name": ..., "version": ...}.
    """
    packages = []
    seen = set()

    # Collect all .csproj files and Directory.Packages.props
    files_to_scan = list(project_path.glob("**/*.csproj"))
    dir_packages = project_path / "Directory.Packages.props"
    if dir_packages.exists():
        files_to_scan.append(dir_packages)

    pkg_ref_re = re.compile(
        r'<PackageReference\s+Include="([^"]+)".*?Version="([^"]+)"',
        re.IGNORECASE,
    )
    pkg_version_re = re.compile(
        r'<PackageVersion\s+Include="([^"]+)".*?Version="([^"]+)"',
        re.IGNORECASE,
    )

    for f in files_to_scan:
        try:
            content = f.read_text()
        except OSError:
            continue
        for match in pkg_ref_re.finditer(content):
            name, version = match.group(1), match.group(2)
            if name not in seen:
                seen.add(name)
                packages.append({"name": name, "version": version})
        for match in pkg_version_re.finditer(content):
            name, version = match.group(1), match.group(2)
            if name not in seen:
                seen.add(name)
                packages.append({"name": name, "version": version})

    return packages


def lookup_nuget_license(package_name: str, version: str) -> Optional[str]:
    """Look up a NuGet package license via the NuGet API.

    Tries the registration endpoint which returns license info.
    """
    # NuGet v3 registration endpoint (gzip-compressed responses)
    url = f"https://api.nuget.org/v3/registration5-gz-semver2/{urlquote(package_name.lower(), safe='')}/{urlquote(version, safe='')}.json"
    headers = {
        "User-Agent": "license-check-scanner/1.0",
        "Accept-Encoding": "gzip",
    }
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=10) as resp:
            raw = resp.read()
            # Decompress gzip if needed
            if raw[:2] == b'\x1f\x8b':
                raw = gzip_mod.decompress(raw)
            data = json.loads(raw)
        catalog = data.get("catalogEntry", {})
        # catalogEntry may be a URL string — if so, fetch it (only from NuGet domains)
        if isinstance(catalog, str):
            parsed = urlparse(catalog)
            if parsed.hostname not in ("api.nuget.org", "nuget.org", "www.nuget.org"):
                catalog = {}
            else:
                try:
                    req2 = Request(catalog, headers={"User-Agent": "license-check-scanner/1.0"})
                    with urlopen(req2, timeout=10) as resp2:
                        raw2 = resp2.read()
                        if raw2[:2] == b'\x1f\x8b':
                            raw2 = gzip_mod.decompress(raw2)
                        catalog = json.loads(raw2)
                except (URLError, json.JSONDecodeError, OSError):
                    catalog = {}
        if not isinstance(catalog, dict):
            catalog = {}
        # Try licenseExpression first (SPDX)
        expr = catalog.get("licenseExpression", "")
        if expr:
            return expr
        # Try licenseUrl as fallback
        lic_url = catalog.get("licenseUrl", "")
        if lic_url:
            # Common known license URLs
            url_map = {
                "apache.org/licenses/LICENSE-2.0": "Apache-2.0",
                "opensource.org/licenses/MIT": "MIT",
                "opensource.org/licenses/BSD": "BSD-3-Clause",
                "mozilla.org/MPL/2.0": "MPL-2.0",
                "gnu.org/licenses/lgpl": "LGPL-2.1",
                "gnu.org/licenses/gpl": "GPL-3.0",
            }
            for pattern, spdx in url_map.items():
                if pattern in lic_url:
                    return spdx
    except (URLError, json.JSONDecodeError, OSError, KeyError):
        pass
    return None


def extract_licenses_csharp(project_path: Path) -> tuple[list[dict], bool, int]:
    """Extract licenses from C# (NuGet) projects.

    Parses .csproj and Directory.Packages.props, looks up licenses via NuGet API.

    Returns (packages, is_monorepo, project_count).
    """
    deps = _parse_csproj_packages(project_path)
    if not deps:
        return [], False, 0

    # Count .csproj files as project count
    csproj_count = len(list(project_path.glob("**/*.csproj")))
    is_monorepo = csproj_count > 1

    print(f"  Looking up {len(deps)} NuGet package licenses...", file=sys.stderr)
    packages = []
    resolved_count = 0

    for dep in deps:
        license_str = "UNKNOWN"
        lic = lookup_nuget_license(dep["name"], dep["version"])
        if lic:
            license_str = lic
            resolved_count += 1

        packages.append({
            "name": dep["name"],
            "version": dep["version"],
            "license": license_str,
            "is_dev": False,
        })

    print(f"  Resolved {resolved_count}/{len(deps)} licenses via NuGet", file=sys.stderr)
    return packages, is_monorepo, csproj_count
