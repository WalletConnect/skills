"""Python: poetry/uv/pipenv/pip extractors + PyPI lookup."""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.parse import quote as urlquote
from urllib.request import urlopen


def lookup_pypi_license(pkg_name: str, version: str) -> Optional[str]:
    """Query PyPI for a package's license via classifiers or license field."""
    safe_name = urlquote(pkg_name, safe='')
    safe_ver = urlquote(version, safe='')
    url = f"https://pypi.org/pypi/{safe_name}/{safe_ver}/json" if version else f"https://pypi.org/pypi/{safe_name}/json"
    try:
        with urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        info = data.get("info", {})

        # Prefer classifiers (more structured)
        classifiers = info.get("classifiers", [])
        for classifier in classifiers:
            if classifier.startswith("License :: OSI Approved :: "):
                return classifier.split(" :: ")[-1]

        # Fall back to license field
        lic = info.get("license", "")
        if isinstance(lic, str) and lic and lic.upper() not in ("UNKNOWN", ""):
            return lic
    except (URLError, json.JSONDecodeError, OSError, KeyError):
        pass
    return None


def _parse_poetry_lock(lock_path: Path) -> list[dict]:
    """Parse poetry.lock (TOML-like) for package names and versions."""
    packages = []
    current = {}
    in_package = False

    with open(lock_path) as f:
        for line in f:
            stripped = line.strip()
            if stripped == "[[package]]":
                if current.get("name"):
                    packages.append(current)
                current = {}
                in_package = True
                continue
            # Exit package section on new section header (but not [[package]])
            if in_package and stripped.startswith("[") and not stripped.startswith("[[package]]"):
                if not stripped.startswith("[package."):
                    # New top-level section, save current and stop
                    in_package = False
                continue
            if in_package and "=" in stripped:
                key, _, value = stripped.partition("=")
                key = key.strip()
                value = value.strip().strip('"')
                if key == "name":
                    current["name"] = value
                elif key == "version":
                    current["version"] = value

    if current.get("name"):
        packages.append(current)

    return packages


def _parse_pipfile_lock(lock_path: Path) -> list[dict]:
    """Parse Pipfile.lock (JSON) for packages with dev/prod distinction."""
    try:
        with open(lock_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    packages = []
    for section, is_dev in [("default", False), ("develop", True)]:
        for name, info in data.get(section, {}).items():
            version = info.get("version", "").lstrip("=")
            packages.append({
                "name": name,
                "version": version,
                "is_dev": is_dev,
            })

    return packages


def _parse_requirements_txt(req_path: Path) -> list[dict]:
    """Parse requirements.txt for package names and versions."""
    packages = []
    with open(req_path) as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("-"):
                continue
            # Handle package==version, package>=version, etc.
            matched = False
            for sep in ("==", ">=", "<=", "~=", "!=", ">", "<"):
                if sep in stripped:
                    name, _, version = stripped.partition(sep)
                    name = name.split("[")[0].strip()
                    version = version.strip().split(",")[0].split(";")[0].strip()
                    packages.append({
                        "name": name,
                        "version": version,
                        "is_dev": False,
                    })
                    matched = True
                    break
            if not matched:
                # Package without version pin
                name = stripped.split("[")[0].split(";")[0].strip()
                if name:
                    packages.append({
                        "name": name,
                        "version": "",
                        "is_dev": False,
                    })

    return packages


def extract_licenses_python(project_path: Path, pm: str, prod_only: bool) -> list[dict]:
    """Extract licenses for Python projects by parsing lockfiles + PyPI lookup.

    Supports poetry.lock, uv.lock, Pipfile.lock, and requirements.txt.
    """
    # Parse lockfile to get package list
    if pm == "poetry":
        raw_packages = _parse_poetry_lock(project_path / "poetry.lock")
    elif pm == "uv":
        # uv.lock uses same [[package]] format as poetry.lock
        raw_packages = _parse_poetry_lock(project_path / "uv.lock")
    elif pm == "pipenv":
        raw_packages = _parse_pipfile_lock(project_path / "Pipfile.lock")
    elif pm == "pip":
        raw_packages = _parse_requirements_txt(project_path / "requirements.txt")
    else:
        return []

    if not raw_packages:
        return []

    # Poetry/uv don't have dev info in lockfile — try to detect from pyproject.toml
    dev_deps = set()
    if pm in ("poetry", "uv"):
        pyproject = project_path / "pyproject.toml"
        if pyproject.exists():
            try:
                with open(pyproject) as f:
                    content = f.read()
                # Simple regex extraction for dev dependencies
                # poetry: [tool.poetry.group.dev.dependencies] or [tool.poetry.dev-dependencies]
                # uv: [tool.uv.dev-dependencies]
                in_dev = False
                for line in content.splitlines():
                    stripped = line.strip()
                    if re.match(r'\[tool\.poetry\.(dev-dependencies|group\.dev\.dependencies)\]', stripped):
                        in_dev = True
                        continue
                    if re.match(r'\[tool\.uv\.dev-dependencies\]', stripped):
                        in_dev = True
                        continue
                    if in_dev and stripped.startswith("["):
                        in_dev = False
                        continue
                    if in_dev and "=" in stripped:
                        dep_name = stripped.split("=")[0].strip().strip('"')
                        dev_deps.add(dep_name.lower())
            except OSError:
                pass

    # Look up licenses via PyPI
    packages = []
    total = len(raw_packages)
    print(f"  Looking up {total} Python package licenses via PyPI...", file=sys.stderr)

    for i, raw in enumerate(raw_packages, 1):
        name = raw.get("name", "")
        version = raw.get("version", "")
        is_dev = raw.get("is_dev", name.lower() in dev_deps)

        if prod_only and is_dev:
            continue

        license_str = lookup_pypi_license(name, version)

        packages.append({
            "name": name,
            "version": version,
            "license": license_str if license_str else "UNKNOWN",
            "is_dev": is_dev,
        })

        if i % 50 == 0:
            print(f"  Looked up {i}/{total}...", file=sys.stderr)
            time.sleep(0.2)  # Small delay to be respectful to PyPI

    return packages
