#!/usr/bin/env python3
"""
License Compliance Scanner

Scans JS/TS, Rust, and Python projects for dependency license compliance.
JS/TS: pnpm, npm, yarn. Rust: cargo. Python: poetry, uv, pipenv, pip.
Handles monorepos and workspaces.

Outputs JSON to stdout for downstream formatting.
"""

from __future__ import annotations

import json
import sys
import argparse
import tempfile
import shutil
import time
from pathlib import Path
from typing import Optional

from config import SCRIPT_DIR, DEFAULT_CONFIG, load_config
from util import run_command
from classify import classify_packages
from blame import trace_blame_for_violations
from ecosystems import (
    extract_licenses_pnpm, extract_licenses_node_modules,
    extract_licenses_cargo,
    extract_licenses_python,
    find_package_resolved, extract_licenses_swift,
    extract_licenses_gradle,
    extract_licenses_dart,
    extract_licenses_go,
    extract_licenses_csharp,
    extract_licenses_solidity,
)


def detect_package_manager(project_path: Path) -> Optional[str]:
    """Detect package manager from lockfiles or package.json."""

    # Solidity (Foundry / Hardhat) — check BEFORE JS/TS since Foundry projects
    # often also have package.json for npm deps
    if (project_path / "foundry.toml").exists():
        return "solidity"

    if (project_path / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (project_path / "yarn.lock").exists():
        return "yarn"
    if (project_path / "package-lock.json").exists():
        return "npm"

    # Fallback: packageManager field in package.json
    pkg_json = project_path / "package.json"
    if pkg_json.exists():
        try:
            with open(pkg_json) as f:
                pkg = json.load(f)
            pm = pkg.get("packageManager", "")
            if pm.startswith("pnpm"):
                return "pnpm"
            if pm.startswith("yarn"):
                return "yarn"
            if pm.startswith("npm"):
                return "npm"
        except (json.JSONDecodeError, OSError):
            pass

    # Rust
    if (project_path / "Cargo.lock").exists() or (project_path / "Cargo.toml").exists():
        return "cargo"

    # Kotlin/Gradle (check for version catalog or build files)
    if (project_path / "gradle" / "libs.versions.toml").exists():
        return "gradle"
    if any((project_path / f).exists() for f in ("build.gradle.kts", "build.gradle", "settings.gradle.kts")):
        return "gradle"

    # Swift (SPM)
    if find_package_resolved(project_path):
        return "swift"

    # Dart (pub)
    if (project_path / "pubspec.lock").exists() or (project_path / "pubspec.yaml").exists():
        return "dart"

    # Go (modules)
    if (project_path / "go.sum").exists() or (project_path / "go.mod").exists():
        return "go"

    # C# (NuGet)
    if (project_path / "Directory.Packages.props").exists():
        return "csharp"
    if list(project_path.glob("*.csproj")) or list(project_path.glob("*.sln")):
        return "csharp"

    # Python (check lockfiles in priority order)
    if (project_path / "poetry.lock").exists():
        return "poetry"
    if (project_path / "uv.lock").exists():
        return "uv"
    if (project_path / "Pipfile.lock").exists():
        return "pipenv"
    if (project_path / "requirements.txt").exists():
        return "pip"

    return None


def detect_workspaces(project_path: Path, pm: str) -> list[Path]:
    """Detect workspace directories in a monorepo."""
    globs = []

    if pm == "pnpm":
        ws_file = project_path / "pnpm-workspace.yaml"
        if ws_file.exists():
            with open(ws_file) as f:
                in_packages = False
                for line in f:
                    stripped = line.strip()
                    if stripped == "packages:":
                        in_packages = True
                        continue
                    if in_packages:
                        if stripped.startswith("- "):
                            glob_pattern = stripped[2:].strip().strip("'\"")
                            globs.append(glob_pattern)
                        elif stripped and not stripped.startswith("#"):
                            break
    else:
        pkg_json = project_path / "package.json"
        if pkg_json.exists():
            try:
                with open(pkg_json) as f:
                    pkg = json.load(f)
                ws = pkg.get("workspaces", [])
                if isinstance(ws, dict):
                    ws = ws.get("packages", [])
                globs = ws
            except (json.JSONDecodeError, OSError):
                pass

    # Resolve globs to directories
    workspace_dirs = []
    import glob as globmod
    for pattern in globs:
        # Remove trailing /* or /** if present
        clean = pattern.rstrip("/")
        if clean.endswith("/*"):
            clean = clean[:-2]
            # Expand one level
            for match in sorted(globmod.glob(str(project_path / clean / "*"))):
                p = Path(match)
                if p.is_dir() and (p / "package.json").exists():
                    workspace_dirs.append(p)
        elif "*" in clean:
            for match in sorted(globmod.glob(str(project_path / clean))):
                p = Path(match)
                if p.is_dir() and (p / "package.json").exists():
                    workspace_dirs.append(p)
        else:
            p = project_path / clean
            if p.is_dir() and (p / "package.json").exists():
                workspace_dirs.append(p)

    return workspace_dirs


def clone_and_install(repo: str, ref: Optional[str] = None) -> tuple[Optional[Path], Optional[str]]:
    """Clone a GitHub repo to a temp dir and install deps. Returns (path, pm)."""
    tmpdir = Path(tempfile.mkdtemp(prefix="license-check-"))

    # Normalize repo arg: strip GitHub URL prefixes to get org/repo
    from urllib.parse import urlparse as _urlparse
    parsed = _urlparse(repo if "://" in repo else "https://" + repo)
    if parsed.hostname == "github.com":
        repo = parsed.path.strip("/")
    repo = repo.rstrip("/")

    # Clone
    clone_cmd = ["gh", "repo", "clone", repo, str(tmpdir), "--", "--depth", "1"]
    if ref:
        clone_cmd.extend(["--branch", ref])

    print(f"Cloning {repo}...", file=sys.stderr)
    ok, msg = run_command(clone_cmd, timeout=120)
    if not ok:
        shutil.rmtree(tmpdir, ignore_errors=True)
        print(f"Clone failed: {msg}", file=sys.stderr)
        return None, None

    # Detect PM
    pm = detect_package_manager(tmpdir)
    if not pm:
        shutil.rmtree(tmpdir, ignore_errors=True)
        print("No package manager detected in cloned repo", file=sys.stderr)
        return None, None

    # These PMs don't need install — they parse lockfiles / use metadata / API lookup directly
    if pm in ("cargo", "swift", "gradle", "dart", "go", "csharp", "solidity", "poetry", "uv", "pipenv", "pip"):
        print(f"Detected {pm} project (no install needed)", file=sys.stderr)
        return tmpdir, pm

    # JS/TS: install deps (--ignore-scripts prevents arbitrary code execution from postinstall hooks)
    install_cmds = {
        "pnpm": ["pnpm", "install", "--frozen-lockfile", "--ignore-scripts"],
        "npm": ["npm", "ci", "--ignore-scripts"],
        "yarn": ["yarn", "install", "--frozen-lockfile", "--ignore-scripts"],
    }
    cmd = install_cmds[pm]
    print(f"Installing dependencies with {pm}...", file=sys.stderr)
    ok, msg = run_command(cmd, cwd=str(tmpdir), timeout=600)
    if not ok:
        shutil.rmtree(tmpdir, ignore_errors=True)
        print(f"Install failed: {msg}", file=sys.stderr)
        return None, None

    return tmpdir, pm


def scan_project(project_path: Path, pm: str, prod_only: bool, config: dict, verbose: bool) -> dict:
    """Scan a project and return results dict."""
    start = time.time()

    is_monorepo = False
    workspace_count = 0
    packages = []
    ecosystem = "npm"  # default for classify_packages registry lookup

    if pm == "cargo":
        # Rust: use cargo metadata
        ecosystem = "cargo"
        packages, is_monorepo, workspace_count = extract_licenses_cargo(project_path)
        if not packages:
            if not (project_path / "Cargo.toml").exists():
                return {"error": "No Cargo.toml found.", "project": str(project_path)}
            return {"error": "No packages found via cargo metadata.", "project": str(project_path)}

    elif pm == "swift":
        # Swift: parse Package.resolved + GitHub API lookup
        ecosystem = "github"
        packages = extract_licenses_swift(project_path)
        if not packages:
            return {"error": "No Package.resolved found or no dependencies.", "project": str(project_path)}

    elif pm == "gradle":
        # Kotlin/Gradle: parse version catalog + Maven Central POM lookup
        ecosystem = "maven"
        packages, is_monorepo, workspace_count = extract_licenses_gradle(project_path)
        if not packages:
            return {"error": "No dependencies found in Gradle project.", "project": str(project_path)}

    elif pm == "dart":
        # Dart: parse pubspec.lock/yaml + pub.dev/GitHub API lookup
        ecosystem = "github"
        packages, is_monorepo, workspace_count = extract_licenses_dart(project_path)
        if not packages:
            return {"error": "No pubspec.lock/yaml found or no hosted dependencies.", "project": str(project_path)}

    elif pm == "go":
        # Go: parse go.sum + GitHub API lookup
        ecosystem = "github"
        packages, is_monorepo, workspace_count = extract_licenses_go(project_path)
        if not packages:
            return {"error": "No go.sum found or no external dependencies.", "project": str(project_path)}

    elif pm == "csharp":
        # C#: parse .csproj/Directory.Packages.props + NuGet API lookup
        ecosystem = "nuget"
        packages, is_monorepo, workspace_count = extract_licenses_csharp(project_path)
        if not packages:
            return {"error": "No .csproj files found or no NuGet dependencies.", "project": str(project_path)}

    elif pm == "solidity":
        # Solidity: git submodules (resolved via GitHub) + npm deps (resolved via npm registry)
        # Use "npm" ecosystem so the second-pass lookup resolves npm package licenses
        ecosystem = "npm"
        packages, is_monorepo, workspace_count = extract_licenses_solidity(project_path)
        if not packages:
            return {"error": "No dependencies found in Solidity/Foundry project.", "project": str(project_path)}

    elif pm in ("poetry", "uv", "pipenv", "pip"):
        # Python: parse lockfile + PyPI lookup
        ecosystem = "pypi"
        packages = extract_licenses_python(project_path, pm, prod_only)
        if not packages:
            lockfile_names = {
                "poetry": "poetry.lock", "uv": "uv.lock",
                "pipenv": "Pipfile.lock", "pip": "requirements.txt",
            }
            return {
                "error": f"No packages found in {lockfile_names.get(pm, 'lockfile')}.",
                "project": str(project_path),
            }
        # Check for monorepo indicators
        if pm in ("poetry", "uv"):
            pyproject = project_path / "pyproject.toml"
            if pyproject.exists():
                try:
                    with open(pyproject) as f:
                        content = f.read()
                    if "[tool.poetry.packages]" in content:
                        is_monorepo = True
                except OSError:
                    pass

    else:
        # JS/TS: existing extraction
        workspaces = detect_workspaces(project_path, pm)
        is_monorepo = len(workspaces) > 0
        workspace_count = len(workspaces)

        if pm == "pnpm":
            packages = extract_licenses_pnpm(project_path, prod_only)
            if not packages and verbose:
                print("  pnpm licenses returned no results, falling back to node_modules", file=sys.stderr)
            if not packages:
                packages = extract_licenses_node_modules(project_path, prod_only)
        else:
            packages = extract_licenses_node_modules(project_path, prod_only)

        if not packages:
            if not (project_path / "node_modules").exists():
                return {
                    "error": f"Dependencies not installed. Run `{pm} install` first.",
                    "project": str(project_path),
                }
            return {"error": "No packages found.", "project": str(project_path)}

    if verbose:
        print(f"Package manager: {pm}", file=sys.stderr)
        print(f"Monorepo: {is_monorepo} ({workspace_count} workspaces)", file=sys.stderr)

    # Classify
    classified = classify_packages(packages, config, ecosystem=ecosystem)

    # Enrich HIGH violations with git blame
    if classified["restrictive"] and (project_path / ".git").exists():
        classified["restrictive"] = trace_blame_for_violations(
            project_path, pm, classified["restrictive"], verbose
        )

    elapsed = time.time() - start

    # Build output
    summary = {
        "permissive": len(classified["permissive"]),
        "weak_copyleft": len(classified["weak_copyleft"]),
        "restrictive": len(classified["restrictive"]),
        "custom": len(classified.get("custom", [])),
        "unknown": len(classified["unknown"]),
        "total": len(packages),
    }

    has_violations = len(classified["restrictive"]) > 0

    output = {
        "project": str(project_path),
        "package_manager": pm,
        "is_monorepo": is_monorepo,
        "workspace_count": workspace_count,
        "prod_only": prod_only,
        "elapsed_seconds": round(elapsed, 1),
        "summary": summary,
        "has_violations": has_violations,
        "violations": {
            "high": classified["restrictive"],
            "medium": classified["weak_copyleft"],
        },
        "custom": classified.get("custom", []),
        "unknown": classified["unknown"],
    }

    if verbose:
        output["all_packages"] = classified

    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan JS/TS, Rust, and Python project dependencies for license compliance"
    )
    parser.add_argument(
        "--path", type=Path, default=None,
        help="Project directory to scan (default: cwd)"
    )
    parser.add_argument(
        "--repo", type=str, default=None,
        help="GitHub repo to clone and scan (e.g., org/repo or full URL)"
    )
    parser.add_argument(
        "--ref", type=str, default=None,
        help="Branch or tag to clone (used with --repo)"
    )
    parser.add_argument(
        "--prod-only", action="store_true",
        help="Only scan production dependencies"
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG,
        help="Path to config JSON file"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Include all packages in output (not just violations)"
    )

    args = parser.parse_args()
    config = load_config(args.config)

    tmpdir = None
    try:
        if args.repo:
            tmpdir, pm = clone_and_install(args.repo, args.ref)
            if tmpdir is None:
                sys.exit(1)
            project_path = tmpdir
        else:
            project_path = args.path or Path.cwd()
            pm = detect_package_manager(project_path)
            if not pm:
                print(json.dumps({
                    "error": "No lockfile found. Expected pnpm-lock.yaml, yarn.lock, package-lock.json, Cargo.toml, poetry.lock, uv.lock, Pipfile.lock, or requirements.txt.",
                    "project": str(project_path),
                }))
                sys.exit(1)

        result = scan_project(project_path, pm, args.prod_only, config, args.verbose)
        print(json.dumps(result, indent=2))

        # Exit with non-zero if HIGH violations found
        if result.get("has_violations"):
            sys.exit(2)

    finally:
        if tmpdir and tmpdir.exists():
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
