"""License config, normalization, SPDX expression evaluation, and overrides."""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_CONFIG = SCRIPT_DIR.parent / "config" / "default-config.json"


def load_config(config_path: Path) -> dict:
    """Load license classification config."""
    with open(config_path) as f:
        return json.load(f)


def normalize_license(raw: str, config: dict) -> str:
    """Normalize a license string using aliases."""
    if not raw:
        return "UNKNOWN"
    trimmed = raw.strip()
    aliases = config.get("aliases", {})
    return aliases.get(trimmed, trimmed)


def classify_license(license_str: str, config: dict) -> str:
    """Classify a normalized license string into a tier."""
    tiers = config.get("license_tiers", {})
    for tier, licenses in tiers.items():
        if license_str in licenses:
            return tier
    return "unknown"


def evaluate_spdx_expr(expr: str, config: dict) -> tuple[str, str]:
    """Evaluate an SPDX expression, return (best_license, tier).

    OR -> most permissive; AND -> most restrictive.
    Also handles Rust-style slash separators (MIT/Apache-2.0) as OR.
    """
    tier_rank = {"permissive": 0, "weak_copyleft": 1, "restrictive": 2, "unknown": 3}

    if " OR " in expr:
        parts = [p.strip().strip("()") for p in expr.split(" OR ")]
        best_tier = "unknown"
        best_license = expr
        for part in parts:
            norm = normalize_license(part, config)
            tier = classify_license(norm, config)
            if tier_rank.get(tier, 3) < tier_rank.get(best_tier, 3):
                best_tier = tier
                best_license = norm
        return best_license, best_tier

    if " AND " in expr:
        parts = [p.strip().strip("()") for p in expr.split(" AND ")]
        worst_tier = "permissive"
        worst_license = expr
        for part in parts:
            norm = normalize_license(part, config)
            tier = classify_license(norm, config)
            if tier_rank.get(tier, 3) > tier_rank.get(worst_tier, 3):
                worst_tier = tier
                worst_license = norm
        return worst_license, worst_tier

    # Handle Rust-style slash-delimited dual licenses (e.g. "MIT/Apache-2.0",
    # "Apache-2.0/MIT", "Unlicense/MIT"). Treat "/" as OR.
    # Only split if "/" is not part of a known license identifier (e.g. "LGPL-2.1-or-later").
    if "/" in expr and " " not in expr:
        parts = [p.strip() for p in expr.split("/")]
        # Verify at least one part is a known license before treating as dual
        any_known = any(
            classify_license(normalize_license(p, config), config) != "unknown"
            for p in parts
        )
        if any_known:
            best_tier = "unknown"
            best_license = expr
            for part in parts:
                norm = normalize_license(part, config)
                tier = classify_license(norm, config)
                if tier_rank.get(tier, 3) < tier_rank.get(best_tier, 3):
                    best_tier = tier
                    best_license = norm
            return best_license, best_tier

    # Also handle "Apache-2.0 / MIT" (spaces around slash)
    if " / " in expr:
        parts = [p.strip() for p in expr.split(" / ")]
        any_known = any(
            classify_license(normalize_license(p, config), config) != "unknown"
            for p in parts
        )
        if any_known:
            best_tier = "unknown"
            best_license = expr
            for part in parts:
                norm = normalize_license(part, config)
                tier = classify_license(norm, config)
                if tier_rank.get(tier, 3) < tier_rank.get(best_tier, 3):
                    best_tier = tier
                    best_license = norm
            return best_license, best_tier

    norm = normalize_license(expr, config)
    return norm, classify_license(norm, config)


def find_override(pkg_name: str, config: dict) -> Optional[dict]:
    """Check if a package matches a license_overrides entry (supports glob patterns)."""
    overrides = config.get("license_overrides", {})
    for pattern, override in overrides.items():
        if fnmatch.fnmatch(pkg_name, pattern) or pkg_name == pattern:
            return override
    return None
