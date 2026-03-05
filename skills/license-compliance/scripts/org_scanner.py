#!/usr/bin/env python3
"""
Org-Wide License Discovery & Tracking

Discovers JS/TS, Rust, and Python repos across GitHub orgs, tracks what's been
scanned, and resumes from where it left off. Orchestrates license_check.py for
individual repo scans.

Outputs JSON to stdout, progress to stderr.
"""

from __future__ import annotations

import subprocess
import json
import sys
import os
import argparse
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent.resolve()
LICENSE_CHECK = SCRIPT_DIR / "license_check.py"

SUPPORTED_LANGUAGES = {"JavaScript", "TypeScript", "Rust", "Python", "Dart", "Go", "C#", "Kotlin", "Swift", "Solidity"}


def run_command(args: list[str], timeout: int = 60, ok_codes: set[int] | None = None) -> tuple[bool, str]:
    """Run a command and return (success, output).

    ok_codes: set of return codes to treat as success (default: {0}).
    """
    if ok_codes is None:
        ok_codes = {0}
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode not in ok_codes:
            return False, result.stderr.strip() or result.stdout.strip()
        return True, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, f"Timeout after {timeout}s: {' '.join(args)}"
    except FileNotFoundError:
        return False, f"Command not found: {args[0]}"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_tracker(path: Path) -> dict:
    """Load tracker file or return empty structure."""
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"orgs": [], "last_discovery": None, "repos": {}}


def save_tracker(tracker: dict, path: Path) -> None:
    """Save tracker to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(tracker, f, indent=2)
        f.write("\n")


def discover_repos(orgs: list[str], tracker: dict) -> dict:
    """Discover repos across orgs via gh CLI. Returns updated tracker."""
    timestamp = now_iso()
    new_count = 0
    total_discovered = 0

    for org in orgs:
        if org not in tracker["orgs"]:
            tracker["orgs"].append(org)

        print(f"Discovering repos in {org}...", file=sys.stderr)
        ok, output = run_command([
            "gh", "repo", "list", org,
            "--no-archived",
            "--json", "name,nameWithOwner,primaryLanguage,pushedAt",
            "--limit", "1000",
        ], timeout=30)

        if not ok:
            print(f"  Failed to list repos for {org}: {output}", file=sys.stderr)
            continue

        try:
            repos = json.loads(output)
        except json.JSONDecodeError:
            print(f"  Failed to parse repo list for {org}", file=sys.stderr)
            continue

        total_discovered += len(repos)
        for repo in repos:
            full_name = repo["nameWithOwner"]
            lang = repo.get("primaryLanguage")
            primary_language = lang.get("name", "") if isinstance(lang, dict) else ""

            if full_name not in tracker["repos"]:
                tracker["repos"][full_name] = {
                    "discovered_at": timestamp,
                    "primary_language": primary_language,
                    "pushed_at": repo.get("pushedAt"),
                    "has_lockfile": None,
                    "package_manager": None,
                    "is_monorepo": None,
                    "last_scanned": None,
                    "last_result_summary": None,
                    "scan_error": None,
                    "skip_reason": None,
                }
                new_count += 1
            else:
                # Update language and push date for existing entries
                tracker["repos"][full_name]["primary_language"] = primary_language
                tracker["repos"][full_name]["pushed_at"] = repo.get("pushedAt")

        print(f"  {org}: {len(repos)} repos found", file=sys.stderr)

    # Migrate repos previously skipped as unsupported that are now supported
    migrated = 0
    for name, info in tracker["repos"].items():
        skip = info.get("skip_reason", "")
        if skip and skip.startswith("language:"):
            lang = skip.split(":", 1)[1]
            if lang in SUPPORTED_LANGUAGES:
                info["skip_reason"] = None
                info["has_lockfile"] = None  # Re-check lockfile
                migrated += 1
    if migrated:
        print(f"Migrated {migrated} repos from unsupported to supported (will re-check lockfiles)", file=sys.stderr)

    tracker["last_discovery"] = timestamp
    print(f"Discovery complete: {total_discovered} total, {new_count} new", file=sys.stderr)
    return tracker


def check_lockfiles(tracker: dict) -> dict:
    """Check for lockfiles in repos that haven't been checked yet.

    Supports JS/TS (package.json), Rust (Cargo.toml), and Python
    (poetry.lock, uv.lock, Pipfile.lock, requirements.txt).
    """
    unchecked = [
        name for name, info in tracker["repos"].items()
        if info["has_lockfile"] is None
    ]

    if not unchecked:
        return tracker

    print(f"Checking {len(unchecked)} repos for lockfiles...", file=sys.stderr)
    checked = 0

    # Map language to the primary file to check via GitHub API
    LANGUAGE_LOCKFILES = {
        "JavaScript": "package.json",
        "TypeScript": "package.json",
        "Rust": "Cargo.toml",
        "Python": "pyproject.toml",  # Check pyproject.toml first; poetry.lock/uv.lock/etc are optional
        "Dart": "pubspec.yaml",
        "Go": "go.mod",
        "C#": "Directory.Packages.props",
        "Kotlin": "gradle/libs.versions.toml",
        "Swift": "Package.resolved",
        "Solidity": "foundry.toml",
    }
    # Fallback files for Python (if pyproject.toml not found)
    PYTHON_FALLBACKS = ["poetry.lock", "uv.lock", "Pipfile.lock", "requirements.txt"]
    # Fallback files for languages where the primary may not be at root
    KOTLIN_FALLBACKS = ["build.gradle.kts", "build.gradle", "settings.gradle.kts"]
    CSHARP_FALLBACKS = ["*.sln"]  # Can't glob via API, but we can try the .sln pattern
    SWIFT_FALLBACKS = [".package.resolved", "Package.swift"]
    SOLIDITY_FALLBACKS = ["hardhat.config.js", "hardhat.config.ts"]

    for name in unchecked:
        info = tracker["repos"][name]
        lang = info.get("primary_language", "")

        # Skip unsupported languages
        if lang and lang not in SUPPORTED_LANGUAGES:
            info["has_lockfile"] = False
            info["skip_reason"] = f"language:{lang}"
            checked += 1
            continue

        # Determine which file to check
        check_file = LANGUAGE_LOCKFILES.get(lang, "package.json")

        ok, output = run_command([
            "gh", "api", f"/repos/{name}/contents/{check_file}",
            "--jq", ".name",
        ], timeout=10)

        if ok:
            info["has_lockfile"] = True
            info["skip_reason"] = None
        else:
            # Try language-specific fallback files
            fallbacks = {
                "Python": PYTHON_FALLBACKS,
                "Kotlin": KOTLIN_FALLBACKS,
                "Swift": SWIFT_FALLBACKS,
                "Solidity": SOLIDITY_FALLBACKS,
            }.get(lang, [])
            found = False
            for fallback in fallbacks:
                ok2, _ = run_command([
                    "gh", "api", f"/repos/{name}/contents/{fallback}",
                    "--jq", ".name",
                ], timeout=10)
                if ok2:
                    found = True
                    break
            if found:
                info["has_lockfile"] = True
                info["skip_reason"] = None
            else:
                info["has_lockfile"] = False
                skip_map = {
                    "Rust": "no_cargo_toml",
                    "Python": "no_python_lockfile",
                    "Dart": "no_pubspec",
                    "Go": "no_go_mod",
                    "C#": "no_csproj",
                    "Kotlin": "no_gradle",
                    "Swift": "no_package_resolved",
                    "Solidity": "no_foundry_toml",
                }
                info["skip_reason"] = skip_map.get(lang, "no_package_json")

        checked += 1
        if checked % 20 == 0:
            print(f"  Checked {checked}/{len(unchecked)}...", file=sys.stderr)
            time.sleep(0.5)

    print(f"  Lockfile check complete: {checked} repos checked", file=sys.stderr)
    return tracker


def get_scan_candidates(tracker: dict, stale_days: Optional[int], only: Optional[list[str]]) -> list[str]:
    """Get list of repos that need scanning."""
    candidates = []

    for name, info in tracker["repos"].items():
        # If --only specified, filter to those repos
        if only is not None:
            if name not in only:
                continue

        # Must have a lockfile
        if not info.get("has_lockfile"):
            continue

        # Not yet scanned
        if info["last_scanned"] is None:
            candidates.append(name)
            continue

        # Stale check
        if stale_days is not None:
            last = datetime.fromisoformat(info["last_scanned"].replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - last).days
            if age >= stale_days:
                candidates.append(name)

    return candidates


def _pkg_fields(pkg: dict) -> dict:
    """Extract standard fields from a package dict."""
    return {
        "name": pkg.get("name"),
        "version": pkg.get("version"),
        "license": pkg.get("license"),
        "is_dev": pkg.get("is_dev", False),
    }


def _fetch_descriptions(packages: list[dict], repo_language: str = "") -> dict[str, str]:
    """Fetch descriptions from the appropriate registry for a list of packages.

    Routes to npm, crates.io, or PyPI based on repo_language.
    Returns {package_name: description}.
    """
    import urllib.request
    import urllib.error

    descriptions: dict[str, str] = {}
    unique_names = list({p["name"] for p in packages if p.get("name")})

    if not unique_names:
        return descriptions

    registry = "npm"
    if repo_language == "Rust":
        registry = "crates.io"
    elif repo_language == "Python":
        registry = "PyPI"

    print(f"  Fetching descriptions for {len(unique_names)} packages from {registry}...", file=sys.stderr)
    for name in unique_names:
        try:
            if registry == "crates.io":
                url = f"https://crates.io/api/v1/crates/{name}"
                req = urllib.request.Request(url, headers={
                    "User-Agent": "license-check-scanner/1.0",
                    "Accept": "application/json",
                })
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read())
                    desc = data.get("crate", {}).get("description", "")
                    if desc:
                        descriptions[name] = desc
            elif registry == "PyPI":
                url = f"https://pypi.org/pypi/{name}/json"
                with urllib.request.urlopen(url, timeout=5) as resp:
                    data = json.loads(resp.read())
                    desc = data.get("info", {}).get("summary", "")
                    if desc:
                        descriptions[name] = desc
            else:
                url = f"https://registry.npmjs.org/{name}"
                req = urllib.request.Request(url, headers={"Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read())
                    desc = data.get("description", "")
                    if desc:
                        descriptions[name] = desc
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
            pass  # Skip failures silently

    return descriptions


# Curated knowledge base for common non-permissive packages.
# Keys are package name prefixes or exact names.
# "purpose": what it does (overrides npm description if present)
# "alternative": permissive alternative, or why there isn't one
# "removable": ease of removal assessment
PACKAGE_NOTES: dict[str, dict[str, str]] = {
    # MPL-2.0 packages
    "@ethereumjs/rlp": {
        "alternative": "rlp (MIT) — drop-in replacement",
        "removable": "Easy — swap import",
    },
    "@ethereumjs/tx": {
        "alternative": "ethers.js Transaction (MIT) or viem (MIT)",
        "removable": "Moderate — API differences",
    },
    "@ethereumjs/util": {
        "alternative": "ethers.js utils (MIT) or viem (MIT)",
        "removable": "Moderate — widely used utility",
    },
    "axe-core": {
        "alternative": "No permissive alternative for a11y testing",
        "removable": "No — industry standard for accessibility",
    },
    "turbo": {
        "alternative": "nx (MIT) or wireit (Apache-2.0)",
        "removable": "Hard — build system migration required",
    },
    "turbo-darwin-arm64": {
        "alternative": "See turbo — platform binary",
        "removable": "See turbo",
    },
    "turbo-darwin-x64": {
        "alternative": "See turbo — platform binary",
        "removable": "See turbo",
    },
    "turbo-linux-64": {
        "alternative": "See turbo — platform binary",
        "removable": "See turbo",
    },
    "@vercel/style-guide": {
        "alternative": "eslint-config-airbnb (MIT) or custom ESLint config",
        "removable": "Easy — dev dependency, swap ESLint config",
    },
    "webextension-polyfill": {
        "alternative": "No permissive alternative (Mozilla standard)",
        "removable": "No — required for browser extension compat",
    },
    "rpc-websockets": {
        "alternative": "ws (MIT) + custom RPC layer, or jayson (MIT)",
        "removable": "Moderate — transitive dep from Solana libs",
    },
    # LGPL packages
    "@img/sharp-libvips-darwin-arm64": {
        "alternative": "sharp links to libvips (LGPL) — dynamic linking OK",
        "removable": "Easy — only matters if distributing binaries",
    },
    # Custom licenses
    "@metamask/sdk": {
        "alternative": "No — required for MetaMask wallet integration",
        "removable": "No — core wallet connector",
    },
    "@metamask/sdk-communication-layer": {
        "alternative": "See @metamask/sdk — sub-package",
        "removable": "See @metamask/sdk",
    },
    "@metamask/sdk-install-modal-web": {
        "alternative": "See @metamask/sdk — sub-package",
        "removable": "See @metamask/sdk",
    },
    # Unknown licenses
    "@braze/web-sdk": {
        "alternative": "No — proprietary analytics SDK",
        "removable": "Yes if Braze not needed — check product requirements",
    },
    "@sentry/cli": {
        "alternative": "FSL-1.1-MIT converts to MIT after 2 years; or use Sentry self-hosted",
        "removable": "Easy — dev/CI tooling only",
    },
    "@sentry/cli-darwin": {
        "alternative": "See @sentry/cli — platform binary",
        "removable": "See @sentry/cli",
    },
}

# Prefix-based matches for package families
PACKAGE_PREFIX_NOTES: dict[str, dict[str, str]] = {
    "@reown/": {
        "alternative": "First-party — Reown Community License is self-issued",
        "removable": "N/A — own packages",
    },
}


def scan_repo(repo_name: str) -> tuple[Optional[dict], Optional[str]]:
    """Scan a single repo using license_check.py. Returns (result_dict, error).

    result_dict includes summary counts plus package_manager and is_monorepo.
    """
    print(f"  Scanning {repo_name}...", file=sys.stderr)

    # license_check.py exits with code 2 for violations — that's not an error
    # Large monorepos (e.g. appkit) need more time: clone + install + scan
    ok, output = run_command(
        ["python3", str(LICENSE_CHECK), "--repo", repo_name, "--verbose"],
        timeout=900,
        ok_codes={0, 2},
    )

    if not ok:
        return None, classify_error(output[:500])

    # Parse whatever JSON it produced
    try:
        result = json.loads(output)
    except json.JSONDecodeError:
        return None, f"Invalid JSON output: {output[:200]}"

    if "error" in result:
        return None, result["error"]

    summary = result.get("summary", {})
    summary["has_violations"] = result.get("has_violations", False)
    # Capture top-level fields that aren't in summary
    summary["package_manager"] = result.get("package_manager")
    summary["is_monorepo"] = result.get("is_monorepo")

    # Extract non-permissive packages for appendix detail
    non_permissive = []
    # Restrictive/weak copyleft are in violations.high and violations.medium
    violations = result.get("violations", {})
    for pkg in violations.get("high", []):
        non_permissive.append({**_pkg_fields(pkg), "classification": "restrictive"})
    for pkg in violations.get("medium", []):
        non_permissive.append({**_pkg_fields(pkg), "classification": "weak_copyleft"})
    # Custom and unknown are top-level lists
    for pkg in result.get("custom", []):
        non_permissive.append({**_pkg_fields(pkg), "classification": "custom"})
    for pkg in result.get("unknown", []):
        non_permissive.append({**_pkg_fields(pkg), "classification": "unknown"})
    # Also grab weak_copyleft from all_packages if not already in violations
    all_pkgs = result.get("all_packages", {})
    existing_names = {p["name"] for p in non_permissive}
    for pkg in all_pkgs.get("weak_copyleft", []):
        if pkg.get("name") not in existing_names:
            non_permissive.append({**_pkg_fields(pkg), "classification": "weak_copyleft"})
    # Enrich with descriptions from appropriate registry and curated notes
    if non_permissive:
        # Determine ecosystem from package_manager
        pm = result.get("package_manager", "")
        if pm == "cargo":
            repo_lang = "Rust"
        elif pm in ("poetry", "uv", "pipenv", "pip"):
            repo_lang = "Python"
        else:
            repo_lang = ""
        descriptions = _fetch_descriptions(non_permissive, repo_lang)
        for pkg in non_permissive:
            name = pkg.get("name", "")
            # npm description
            pkg["description"] = descriptions.get(name, "")
            # Curated notes (exact match first, then prefix)
            notes = PACKAGE_NOTES.get(name)
            if not notes:
                for prefix, prefix_notes in PACKAGE_PREFIX_NOTES.items():
                    if name.startswith(prefix):
                        notes = prefix_notes
                        break
            if notes:
                pkg["alternative"] = notes.get("alternative", "")
                pkg["removable"] = notes.get("removable", "")
    summary["non_permissive_packages"] = non_permissive

    return summary, None


def classify_error(raw: str) -> str:
    """Classify raw error output into a clean category."""
    lower = raw.lower()
    if "no package manager detected" in lower:
        return "No lockfile detected in repo"
    if "err_pnpm_outdated_lockfile" in lower:
        return "Outdated lockfile (pnpm-lock.yaml out of sync with package.json)"
    if "frozen-lockfile" in lower or "yn0050" in lower:
        return "Outdated lockfile (yarn.lock out of sync)"
    if "corepack" in lower:
        return "Corepack version conflict (packageManager field requires different version)"
    if "dep0169" in lower:
        return "Node.js deprecation breaking install"
    if "timeout" in lower:
        return "Install timed out (likely large monorepo)"
    if "clone failed" in lower:
        return "Failed to clone repo"
    if "install failed" in lower:
        return "Dependency install failed"
    if "no packages found" in lower:
        return "No packages found (deps installed but license extraction returned empty)"
    if "dependencies not installed" in lower:
        return "Dependencies not installed"
    if "resolving" in lower and "unknown licenses" in lower:
        return "Scan stalled during license resolution (likely timeout)"
    if "monorepo: true" in lower and raw.rstrip().endswith("workspaces)"):
        return "Scan stalled after detecting monorepo (likely timeout during install)"
    # Fallback: strip newlines and truncate
    return raw.replace("\n", " ").strip()[:120]


def run_scans(tracker: dict, candidates: list[str], tracker_path: Optional[Path] = None) -> tuple[dict, dict]:
    """Scan candidates and update tracker. Returns (tracker, scan_results).

    If tracker_path is provided, saves after each repo for crash-safe resume.
    """
    results = {"scanned": 0, "errors": 0, "skipped": 0, "violations": []}

    if not candidates:
        print("No repos to scan.", file=sys.stderr)
        return tracker, results

    print(f"Scanning {len(candidates)} repos...", file=sys.stderr)
    for i, name in enumerate(candidates, 1):
        print(f"[{i}/{len(candidates)}] {name}", file=sys.stderr)

        summary, error = scan_repo(name)
        info = tracker["repos"][name]

        if error:
            info["scan_error"] = error
            info["last_scanned"] = now_iso()
            results["errors"] += 1
            print(f"  Error: {error[:100]}", file=sys.stderr)
        else:
            info["last_scanned"] = now_iso()
            info["non_permissive_packages"] = summary.pop("non_permissive_packages", [])
            info["last_result_summary"] = summary
            info["scan_error"] = None
            info["package_manager"] = summary.get("package_manager")
            info["is_monorepo"] = summary.get("is_monorepo")
            results["scanned"] += 1

            if summary.get("has_violations"):
                results["violations"].append(name)
                print(f"  Violations found!", file=sys.stderr)
            else:
                print(f"  Clean", file=sys.stderr)

        # Save after each repo for crash-safe resume
        if tracker_path:
            save_tracker(tracker, tracker_path)

    return tracker, results


def build_output(tracker: dict, results: dict, discover_only: bool) -> dict:
    """Build final JSON output for Claude to format."""
    repos = tracker["repos"]

    # Count by status
    scannable_repos = [n for n, i in repos.items() if i.get("has_lockfile")]
    skipped_repos = [n for n, i in repos.items() if i.get("skip_reason")]
    scanned_repos = [n for n, i in repos.items() if i.get("last_scanned") and not i.get("scan_error")]
    error_repos = [n for n, i in repos.items() if i.get("scan_error")]
    unscanned_repos = [n for n, i in repos.items() if i.get("has_lockfile") and not i.get("last_scanned")]

    # Aggregate violation stats across all scanned repos
    total_stats = {
        "permissive": 0, "weak_copyleft": 0, "restrictive": 0,
        "custom": 0, "unknown": 0, "total": 0,
    }
    repos_with_violations = []
    repos_with_unknowns = []

    for name, info in repos.items():
        s = info.get("last_result_summary")
        if not s:
            continue
        for key in total_stats:
            total_stats[key] += s.get(key, 0)
        if s.get("has_violations"):
            repos_with_violations.append(name)
        if s.get("unknown", 0) > 0:
            repos_with_unknowns.append(name)

    # Language breakdown across all repos (for prioritizing next ecosystem support)
    language_counts: dict[str, int] = {}
    for name, info in repos.items():
        lang = info.get("primary_language") or "Unknown"
        language_counts[lang] = language_counts.get(lang, 0) + 1
    # Sort by count descending
    language_breakdown = dict(sorted(language_counts.items(), key=lambda x: -x[1]))

    output = {
        "orgs": tracker["orgs"],
        "last_discovery": tracker["last_discovery"],
        "discover_only": discover_only,
        "counts": {
            "total_repos": len(repos),
            "scannable_repos": len(scannable_repos),
            "skipped_repos": len(skipped_repos),
            "scanned_repos": len(scanned_repos),
            "error_repos": len(error_repos),
            "unscanned_repos": len(unscanned_repos),
        },
        "language_breakdown": language_breakdown,
        "aggregate_licenses": total_stats,
        "repos_with_violations": repos_with_violations,
        "repos_with_unknowns": repos_with_unknowns,
        "error_repos": {n: repos[n].get("scan_error") for n in error_repos},
        "unscanned_repos": unscanned_repos,
    }

    if not discover_only:
        output["scan_session"] = results

    return output


def _short_date(iso: Optional[str]) -> str:
    """Format ISO date as short date string."""
    if not iso:
        return "never"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return "?"


def _repo_org(name: str) -> str:
    """Extract org from 'org/repo' name."""
    return name.split("/")[0] if "/" in name else ""


def _repo_short(name: str) -> str:
    """Extract short repo name from 'org/repo'."""
    return name.split("/", 1)[1] if "/" in name else name


def generate_report(tracker: dict, report_path: Path) -> None:
    """Generate a markdown compliance report from tracker data."""
    repos = tracker["repos"]
    scanned = [(n, i) for n, i in repos.items() if i.get("last_scanned") and not i.get("scan_error")]
    errors = [(n, i) for n, i in repos.items() if i.get("scan_error")]
    scannable_count = sum(1 for n, i in repos.items() if i.get("has_lockfile"))
    skipped_count = sum(1 for n, i in repos.items() if i.get("skip_reason"))

    # Aggregate
    total = {"permissive": 0, "weak_copyleft": 0, "restrictive": 0, "custom": 0, "unknown": 0, "total": 0}
    for name, info in scanned:
        s = info["last_result_summary"]
        for k in total:
            total[k] += s.get(k, 0)

    # Split repos into notable (has non-permissive) vs clean (100% permissive)
    notable = []
    clean = []
    for name, info in scanned:
        s = info["last_result_summary"]
        if s.get("weak_copyleft", 0) > 0 or s.get("restrictive", 0) > 0 or s.get("custom", 0) > 0 or s.get("unknown", 0) > 0:
            notable.append((name, info))
        else:
            clean.append((name, info))
    notable.sort(key=lambda x: -(x[1]["last_result_summary"].get("total", 0)))
    clean.sort(key=lambda x: -(x[1]["last_result_summary"].get("total", 0)))

    # Language breakdown
    langs: dict[str, int] = {}
    for n, i in repos.items():
        lang = i.get("primary_language") or "Unknown"
        langs[lang] = langs.get(lang, 0) + 1

    # Group scanned repos by org
    orgs_in_tracker = tracker.get("orgs", [])

    lines: list[str] = []

    # --- Header ---
    lines.append("# Org-Wide License Compliance Report")
    lines.append("")

    # --- Executive summary ---
    if total["restrictive"] > 0:
        verdict = "FAIL — restrictive licenses (GPL/AGPL/SSPL) detected"
    elif total["unknown"] > 20:
        verdict = "REVIEW NEEDED — no restrictive licenses, but significant unknowns"
    elif total["unknown"] > 0:
        verdict = "PASS (with minor unknowns to review)"
    else:
        verdict = "PASS — all dependencies use permissive or documented licenses"
    lines.append(f"**Verdict: {verdict}**")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Orgs:** {', '.join(orgs_in_tracker)}")
    lines.append(f"**Total repos:** {len(repos)} | **Scannable repos:** {scannable_count} | **Scanned:** {len(scanned)} | **Errors:** {len(errors)} | **Skipped:** {skipped_count}")
    lines.append("")

    # --- Aggregate summary ---
    lines.append("## Aggregate License Summary")
    lines.append("")
    lines.append("| Classification | Count | Status |")
    lines.append("|:---------------|------:|:-------|")
    lines.append(f"| Permissive     | {total['permissive']:,} | OK |")
    lines.append(f"| Weak Copyleft  | {total['weak_copyleft']:,} | MEDIUM |")
    status = "HIGH" if total["restrictive"] > 0 else "OK"
    lines.append(f"| Restrictive    | {total['restrictive']:,} | {status} |")
    lines.append(f"| Custom         | {total['custom']:,} | Review |")
    lines.append(f"| Unknown        | {total['unknown']:,} | Review |")
    lines.append(f"| **Total**      | **{total['total']:,}** | |")
    lines.append("")

    # --- Repos needing attention (grouped by org) ---
    if notable:
        lines.append("## Repos Needing Attention")
        lines.append("")
        # Group notable by org (case-insensitive match)
        notable_by_org: dict[str, list] = {}
        org_display: dict[str, str] = {}  # lowercase -> actual casing
        for name, info in notable:
            org = _repo_org(name)
            notable_by_org.setdefault(org.lower(), []).append((name, info))
            org_display[org.lower()] = org

        for org in orgs_in_tracker:
            org_repos = notable_by_org.get(org.lower(), [])
            if not org_repos:
                continue
            lines.append(f"### {org_display.get(org.lower(), org)}")
            lines.append("")
            lines.append("| Repo | Package Manager | Total | Weak Copyleft | Restrictive | Custom | Unknown | Last Scanned |")
            lines.append("|:-----|:----------------|------:|--------------:|------------:|-------:|--------:|:-------------|")
            for name, info in org_repos:
                s = info["last_result_summary"]
                pm = s.get("package_manager") or info.get("package_manager") or "?"
                scanned_date = _short_date(info.get("last_scanned"))
                lines.append(f"| {_repo_short(name)} | {pm} | {s.get('total', 0):,} | {s.get('weak_copyleft', 0)} | {s.get('restrictive', 0)} | {s.get('custom', 0)} | {s.get('unknown', 0)} | {scanned_date} |")
            lines.append("")

    # --- Clean repos (grouped by org) ---
    if clean:
        lines.append("## Clean Repos")
        lines.append("")
        lines.append(f"{len(clean)} repos with only permissive licenses.")
        lines.append("")
        clean_by_org: dict[str, list] = {}
        clean_org_display: dict[str, str] = {}
        for name, info in clean:
            org = _repo_org(name)
            clean_by_org.setdefault(org.lower(), []).append((name, info))
            clean_org_display[org.lower()] = org

        for org in orgs_in_tracker:
            org_repos = clean_by_org.get(org.lower(), [])
            if not org_repos:
                continue
            lines.append(f"### {clean_org_display.get(org.lower(), org)}")
            lines.append("")
            lines.append("| Repo | Package Manager | Total Dependencies | Last Scanned |")
            lines.append("|:-----|:----------------|-------------------:|:-------------|")
            for name, info in org_repos:
                s = info["last_result_summary"]
                pm = s.get("package_manager") or info.get("package_manager") or "?"
                scanned_date = _short_date(info.get("last_scanned"))
                lines.append(f"| {_repo_short(name)} | {pm} | {s.get('total', 0):,} | {scanned_date} |")
            lines.append("")

    # --- Errors ---
    if errors:
        lines.append("## Scan Errors")
        lines.append("")
        lines.append("| Repo | Error |")
        lines.append("|:-----|:------|")
        for name, info in errors:
            err = classify_error(info["scan_error"])
            lines.append(f"| {name} | {err} |")
        lines.append("")

    # --- Unsupported languages ---
    non_scannable = [(l, c) for l, c in sorted(langs.items(), key=lambda x: -x[1])
                     if l not in SUPPORTED_LANGUAGES and l not in ("Unknown", "HCL", "Shell", "MDX", "TeX", "Jsonnet", "Dockerfile", "CSS", "Jupyter Notebook")]
    if non_scannable:
        lines.append("## Unsupported Languages")
        lines.append("")
        lines.append("Ranked by repo count — informs which ecosystem to add license scanning support for next.")
        lines.append("")
        lines.append("| Language | Repos |")
        lines.append("|:---------|------:|")
        for lang, count in non_scannable:
            lines.append(f"| {lang} | {count} |")
        lines.append("")

    # --- Action items ---
    lines.append("## Action Items")
    lines.append("")
    item = 1
    if total["restrictive"] > 0:
        lines.append(f"{item}. **{total['restrictive']} restrictive licenses** — must be replaced or receive legal approval")
        item += 1
    if total["unknown"] > 0:
        unknowns_count = sum(1 for n, i in notable if i["last_result_summary"].get("unknown", 0) > 0)
        lines.append(f"{item}. **{total['unknown']} unknown licenses** across {unknowns_count} repos need manual review or config overrides")
        item += 1
    if total["weak_copyleft"] > 0:
        lines.append(f"{item}. **{total['weak_copyleft']} weak copyleft** (MPL-2.0, LGPL) — likely acceptable but worth documenting")
        item += 1
    if errors:
        lines.append(f"{item}. **{len(errors)} scan errors** — repos with outdated lockfiles, missing lockfiles, or install failures")
        item += 1
    if non_scannable:
        top = non_scannable[0]
        lines.append(f"{item}. **{top[0]} ({top[1]} repos)** is the largest unsupported ecosystem — add support next")
    lines.append("")

    # --- Appendix: per-repo package detail ---
    repos_with_detail = [(n, i) for n, i in notable if i.get("non_permissive_packages")]
    if repos_with_detail:
        lines.append("---")
        lines.append("")
        lines.append("## Appendix: Package Detail")
        lines.append("")
        for name, info in repos_with_detail:
            s = info["last_result_summary"]
            pm = s.get("package_manager") or info.get("package_manager") or "?"
            mono = "Yes" if s.get("is_monorepo") else "No"
            lines.append(f"### {name}")
            lines.append("")
            lines.append(f"**Package Manager:** {pm} | **Monorepo:** {mono} | **Total Dependencies:** {s.get('total', 0):,}")
            lines.append("")

            pkgs = info["non_permissive_packages"]
            # Group by classification
            by_class: dict[str, list] = {}
            for pkg in pkgs:
                cls = pkg.get("classification", "unknown")
                by_class.setdefault(cls, []).append(pkg)

            class_order = ["restrictive", "weak_copyleft", "custom", "unknown"]
            class_labels = {
                "restrictive": "Restrictive",
                "weak_copyleft": "Weak Copyleft",
                "custom": "Custom",
                "unknown": "Unknown",
            }

            for cls in class_order:
                cls_pkgs = by_class.get(cls, [])
                if not cls_pkgs:
                    continue
                label = class_labels.get(cls, cls)
                lines.append(f"#### {label} ({len(cls_pkgs)})")
                lines.append("")
                lines.append("| Package | Version | License | Purpose | Permissive Alternative | Removable? |")
                lines.append("|:--------|:--------|:--------|:--------|:-----------------------|:-----------|")
                for pkg in sorted(cls_pkgs, key=lambda p: p.get("name", "")):
                    desc = pkg.get("description", "") or "—"
                    alt = pkg.get("alternative", "") or "Needs review"
                    removable = pkg.get("removable", "") or "Needs review"
                    # Escape pipes in descriptions
                    desc = desc.replace("|", "\\|")
                    alt = alt.replace("|", "\\|")
                    lines.append(f"| {pkg.get('name', '?')} | {pkg.get('version', '?')} | {pkg.get('license', '?')} | {desc} | {alt} | {removable} |")
                lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        f.write("\n".join(lines))

    print(f"Report written to {report_path}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Org-wide license discovery and tracking"
    )
    parser.add_argument(
        "--orgs", type=str, default=None,
        help="Comma-separated GitHub orgs to discover (e.g., reown-com,walletconnect)"
    )
    parser.add_argument(
        "--tracker", type=Path, required=True,
        help="Path to tracker JSON file"
    )
    parser.add_argument(
        "--stale-days", type=int, default=None,
        help="Re-scan repos not scanned in N days"
    )
    parser.add_argument(
        "--discover-only", action="store_true",
        help="Only discover repos, don't scan"
    )
    parser.add_argument(
        "--only", type=str, default=None,
        help="Comma-separated repos to scan (e.g., reown-com/appkit,reown-com/web-monorepo)"
    )
    parser.add_argument(
        "--report", type=Path, default=None,
        help="Path to write markdown report (e.g., ./license-compliance-report.md)"
    )

    args = parser.parse_args()

    # Load or create tracker
    tracker = load_tracker(args.tracker)

    # Discover repos if --orgs provided
    if args.orgs:
        orgs = [o.strip() for o in args.orgs.split(",")]
        tracker = discover_repos(orgs, tracker)
        tracker = check_lockfiles(tracker)
        save_tracker(tracker, args.tracker)

    # If discover-only, output stats and exit
    if args.discover_only:
        output = build_output(tracker, {}, discover_only=True)
        print(json.dumps(output, indent=2))
        if args.report:
            generate_report(tracker, args.report)
        return

    # Determine scan candidates
    only = [o.strip() for o in args.only.split(",")] if args.only else None
    candidates = get_scan_candidates(tracker, args.stale_days, only)

    # Scan
    tracker, results = run_scans(tracker, candidates, tracker_path=args.tracker)
    save_tracker(tracker, args.tracker)

    # Output
    output = build_output(tracker, results, discover_only=False)
    print(json.dumps(output, indent=2))

    # Generate markdown report if requested
    if args.report:
        generate_report(tracker, args.report)

    # Exit with 2 if any violations found
    if results.get("violations"):
        sys.exit(2)


if __name__ == "__main__":
    main()
