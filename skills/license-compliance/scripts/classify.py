"""Classification engine — classify_packages() second-pass resolution."""

from __future__ import annotations

from config import evaluate_spdx_expr, find_override
from ecosystems import lookup_npm_license, lookup_pypi_license, lookup_crates_io_license

import sys


def classify_packages(packages: list[dict], config: dict, resolve_unknowns: bool = True, ecosystem: str = "npm") -> dict:
    """Classify all packages and return structured results."""
    severity_map = config.get("severity_map", {})
    dev_reduction = config.get("dev_severity_reduction", {})

    results = {
        "permissive": [],
        "weak_copyleft": [],
        "restrictive": [],
        "custom": [],
        "unknown": [],
    }

    # First pass: classify everything
    unknown_pkgs = []
    for pkg in packages:
        raw_license = pkg.get("license", "UNKNOWN")
        name = pkg["name"]

        # Check overrides first (for custom/known licenses)
        override = find_override(name, config)
        if override:
            entry = {
                "name": name,
                "version": pkg["version"],
                "license": override["license"],
                "raw_license": raw_license,
                "tier": override["tier"],
                "severity": severity_map.get(override["tier"], "REVIEW"),
                "is_dev": pkg.get("is_dev", False),
                "note": override.get("note", ""),
            }
            if pkg.get("is_dev"):
                entry["severity"] = dev_reduction.get(entry["severity"], entry["severity"])
            results[override["tier"]].append(entry)
            continue

        # Handle SEE LICENSE IN <file>
        if raw_license.upper().startswith("SEE LICENSE IN"):
            tier = "unknown"
            normalized = raw_license
        elif raw_license == "UNLICENSED":
            tier = "unknown"
            normalized = "UNLICENSED"
        elif raw_license in ("Unknown", "UNKNOWN", ""):
            tier = "unknown"
            normalized = "UNKNOWN"
        else:
            normalized, tier = evaluate_spdx_expr(raw_license, config)

        severity = severity_map.get(tier, "LOW")
        if pkg.get("is_dev"):
            severity = dev_reduction.get(severity, severity)

        entry = {
            "name": name,
            "version": pkg["version"],
            "license": normalized,
            "raw_license": raw_license,
            "tier": tier,
            "severity": severity,
            "is_dev": pkg.get("is_dev", False),
        }

        if tier == "unknown":
            unknown_pkgs.append((entry, pkg))
        else:
            results[tier].append(entry)

    # Second pass: resolve unknowns via package registry
    # Skip for github (Swift/Dart/Go/Solidity), maven (Gradle), nuget (C#) — already looked up during extraction
    if resolve_unknowns and unknown_pkgs and ecosystem not in ("github", "maven", "nuget"):
        count = len(unknown_pkgs)
        registry_name = {"npm": "npm", "cargo": "crates.io", "pypi": "PyPI"}.get(ecosystem, ecosystem)
        print(f"  Resolving {count} unknown licenses via {registry_name}...", file=sys.stderr)
        resolved = 0
        for entry, pkg in unknown_pkgs:
            if ecosystem == "cargo":
                reg_license = lookup_crates_io_license(entry["name"], entry["version"])
                source_tag = "crates.io"
            elif ecosystem == "pypi":
                reg_license = lookup_pypi_license(entry["name"], entry["version"])
                source_tag = "pypi"
            else:
                reg_license = lookup_npm_license(entry["name"], entry["version"])
                source_tag = "npm"

            if reg_license:
                normalized, tier = evaluate_spdx_expr(reg_license, config)
                entry["license"] = normalized
                entry["raw_license"] = f"{entry['raw_license']} -> {source_tag}:{reg_license}"
                entry["tier"] = tier
                entry["severity"] = severity_map.get(tier, "LOW")
                if entry["is_dev"]:
                    entry["severity"] = dev_reduction.get(entry["severity"], entry["severity"])
                entry["resolved_via"] = f"{source_tag}_registry"
                results[tier].append(entry)
                resolved += 1
            else:
                results["unknown"].append(entry)
        if resolved:
            print(f"  Resolved {resolved}/{count} via {registry_name}", file=sys.stderr)

    else:
        for entry, _ in unknown_pkgs:
            results["unknown"].append(entry)

    return results
