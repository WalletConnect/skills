"""Kotlin: Gradle version catalogs + Maven Central POM lookup."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.parse import quote as urlquote
from urllib.request import Request, urlopen


def _parse_versions_toml(toml_path: Path) -> tuple[dict, list[dict]]:
    """Parse a Gradle version catalog (libs.versions.toml).

    Returns (versions_dict, libraries_list) where each library is
    {"name": alias, "group": groupId, "artifact": artifactId, "version": resolvedVersion}.
    """
    versions = {}
    libraries = []
    section = None

    with open(toml_path) as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            # Detect section headers
            if stripped.startswith("[") and not stripped.startswith("[["):
                section = stripped.strip("[] ")
                continue

            if section == "versions" and "=" in stripped:
                key, _, val = stripped.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                versions[key] = val

            elif section == "libraries" and "=" in stripped:
                key, _, val = stripped.partition("=")
                alias = key.strip()
                val = val.strip()

                group = artifact = version = ""

                if val.startswith("{"):
                    # Inline table: { module = "g:a", version.ref = "v" }
                    # or: { group = "g", name = "a", version.ref = "v" }
                    parts = val.strip("{}").split(",")
                    props = {}
                    for part in parts:
                        if "=" in part:
                            k, _, v = part.partition("=")
                            props[k.strip()] = v.strip().strip('"').strip("'")

                    module = props.get("module", "")
                    if module and ":" in module:
                        group, artifact = module.split(":", 1)
                    else:
                        group = props.get("group", "")
                        artifact = props.get("name", "")

                    version_ref = props.get("version.ref", "")
                    version_val = props.get("version", "")
                    if version_ref:
                        version = versions.get(version_ref, version_ref)
                    elif version_val:
                        version = version_val
                elif val.startswith('"') or val.startswith("'"):
                    # Simple string: "group:artifact:version"
                    coord = val.strip('"').strip("'")
                    parts = coord.split(":")
                    if len(parts) >= 3:
                        group, artifact, version = parts[0], parts[1], parts[2]
                    elif len(parts) == 2:
                        group, artifact = parts[0], parts[1]

                if group and artifact:
                    libraries.append({
                        "name": alias,
                        "group": group,
                        "artifact": artifact,
                        "version": version,
                    })

    return versions, libraries


def _parse_gradle_build_files(project_path: Path) -> list[dict]:
    """Scan build.gradle.kts files for direct dependency declarations not in version catalog."""
    deps = []
    seen = set()

    for gradle_file in project_path.glob("**/build.gradle.kts"):
        try:
            content = gradle_file.read_text()
        except OSError:
            continue

        # Match patterns like: implementation("group:artifact:version")
        # or: api("group:artifact:version")
        for match in re.finditer(
            r'(?:implementation|api|compileOnly|runtimeOnly|ksp|kapt)\s*\(\s*"([^"]+)"',
            content
        ):
            coord = match.group(1)
            # Remove @aar, @jar suffixes
            coord = re.sub(r'@\w+$', '', coord)
            parts = coord.split(":")
            if len(parts) >= 3 and not parts[0].startswith("$"):
                key = (parts[0], parts[1])
                if key not in seen:
                    seen.add(key)
                    deps.append({
                        "name": f"{parts[0]}:{parts[1]}",
                        "group": parts[0],
                        "artifact": parts[1],
                        "version": parts[2],
                    })

    return deps


def lookup_maven_license(group: str, artifact: str, version: str) -> Optional[str]:
    """Look up a Maven artifact's license via POM file from Maven Central."""
    # Sanitize: quote each segment after splitting on dots to prevent path traversal
    group_path = "/".join(urlquote(seg, safe='') for seg in group.split("."))
    safe_artifact = urlquote(artifact, safe='')
    safe_version = urlquote(version, safe='')
    pom_url = f"https://repo1.maven.org/maven2/{group_path}/{safe_artifact}/{safe_version}/{safe_artifact}-{safe_version}.pom"

    pom_to_spdx = {
        "The Apache Software License, Version 2.0": "Apache-2.0",
        "Apache License, Version 2.0": "Apache-2.0",
        "Apache-2.0": "Apache-2.0",
        "Apache 2.0": "Apache-2.0",
        "Apache License 2.0": "Apache-2.0",
        "The Apache License, Version 2.0": "Apache-2.0",
        "MIT License": "MIT",
        "The MIT License": "MIT",
        "MIT": "MIT",
        "BSD License": "BSD-3-Clause",
        "BSD 3-Clause License": "BSD-3-Clause",
        "BSD-3-Clause": "BSD-3-Clause",
        "The BSD License": "BSD-2-Clause",
        "Eclipse Public License 1.0": "EPL-1.0",
        "Eclipse Public License v2.0": "EPL-2.0",
        "Eclipse Public License - v 2.0": "EPL-2.0",
        "GNU Lesser General Public License": "LGPL-2.1",
        "LGPL-2.1": "LGPL-2.1",
        "GNU General Public License, version 2": "GPL-2.0",
        "Mozilla Public License 2.0": "MPL-2.0",
        "Mozilla Public License, Version 2.0": "MPL-2.0",
        "Bouncy Castle Licence": "MIT",
        "ISC License": "ISC",
    }

    try:
        req = Request(pom_url, headers={"User-Agent": "license-check-scanner/1.0"})
        with urlopen(req, timeout=10) as resp:
            pom_content = resp.read().decode("utf-8", errors="replace")

        # Parse license from POM XML (simple regex — avoid full XML parser dependency)
        license_block = re.search(r'<licenses>(.*?)</licenses>', pom_content, re.DOTALL)
        if license_block:
            names = re.findall(r'<name>(.*?)</name>', license_block.group(1))
            if names:
                # Return first recognized license, or the raw name
                for name in names:
                    name = name.strip()
                    if name in pom_to_spdx:
                        return pom_to_spdx[name]
                return names[0].strip()
    except (URLError, OSError):
        pass

    # Fallback: try Google Maven (for Android/Google artifacts)
    if group.startswith("com.google.") or group.startswith("com.android.") or group.startswith("androidx."):
        google_pom = f"https://dl.google.com/dl/android/maven2/{group_path}/{artifact}/{version}/{artifact}-{version}.pom"
        try:
            req = Request(google_pom, headers={"User-Agent": "license-check-scanner/1.0"})
            with urlopen(req, timeout=10) as resp:
                pom_content = resp.read().decode("utf-8", errors="replace")
            license_block = re.search(r'<licenses>(.*?)</licenses>', pom_content, re.DOTALL)
            if license_block:
                names = re.findall(r'<name>(.*?)</name>', license_block.group(1))
                if names:
                    google_pom_to_spdx = {
                        "The Apache Software License, Version 2.0": "Apache-2.0",
                        "Apache License, Version 2.0": "Apache-2.0",
                    }
                    for name in names:
                        name = name.strip()
                        if name in google_pom_to_spdx:
                            return google_pom_to_spdx[name]
                    return names[0].strip()
        except (URLError, OSError):
            pass

    return None


def extract_licenses_gradle(project_path: Path) -> tuple[list[dict], bool, int]:
    """Extract licenses from Gradle projects via version catalog + Maven POM lookup.

    Returns (packages, is_monorepo, module_count).
    """
    toml_path = project_path / "gradle" / "libs.versions.toml"

    catalog_libs = []
    if toml_path.exists():
        _, catalog_libs = _parse_versions_toml(toml_path)

    # Also scan build files for direct declarations
    build_deps = _parse_gradle_build_files(project_path)

    # Merge, dedup by (group, artifact)
    seen = set()
    all_deps = []
    for lib in catalog_libs:
        key = (lib["group"], lib["artifact"])
        if key not in seen:
            seen.add(key)
            all_deps.append(lib)
    for lib in build_deps:
        key = (lib["group"], lib["artifact"])
        if key not in seen:
            seen.add(key)
            all_deps.append(lib)

    if not all_deps:
        return [], False, 0

    # Count modules (settings.gradle.kts includes)
    module_count = 0
    for settings_file in ("settings.gradle.kts", "settings.gradle"):
        sf = project_path / settings_file
        if sf.exists():
            try:
                content = sf.read_text()
                module_count = len(re.findall(r'include\s*\(', content))
            except OSError:
                pass
            break
    is_monorepo = module_count > 1

    # Look up licenses via Maven Central POM
    print(f"  Looking up {len(all_deps)} Gradle dependency licenses via Maven Central...", file=sys.stderr)
    packages = []
    resolved_count = 0

    for dep in all_deps:
        coord = f"{dep['group']}:{dep['artifact']}"
        license_str = "UNKNOWN"

        if dep["version"]:
            lic = lookup_maven_license(dep["group"], dep["artifact"], dep["version"])
            if lic:
                license_str = lic
                resolved_count += 1

        packages.append({
            "name": coord,
            "version": dep["version"] or "unknown",
            "license": license_str,
            "is_dev": False,
        })

    print(f"  Resolved {resolved_count}/{len(all_deps)} licenses via Maven Central", file=sys.stderr)
    return packages, is_monorepo, module_count
