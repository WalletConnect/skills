#!/usr/bin/env python3
"""
Dependabot Security Alerts Report Generator

Scans GitHub organizations for critical/high severity Dependabot alerts
and generates a report grouped by team ownership (GitHub topics).

Uses the organization-level Dependabot API for efficient access.
"""

from __future__ import annotations

import subprocess
import json
import sys
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Optional

ORGS = ["walletconnect", "reown-com", "walletconnectfoundation"]


def run_gh_command(args: list[str], silent: bool = False, timeout: int = 300) -> Optional[str]:
    """Run a gh CLI command and return output."""
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode != 0:
            if not silent:
                print(f"  Warning: {result.stderr.strip()}", file=sys.stderr)
            return None
        return result.stdout
    except subprocess.TimeoutExpired:
        print(f"  Timeout running: gh {' '.join(args)}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
        return None


def get_org_alerts(org: str, include_medium: bool = False) -> tuple[bool, list[dict]]:
    """Get all open Dependabot alerts for an organization.

    Returns (success, alerts) — success is False when the API call failed.
    """
    print(f"  Fetching alerts for {org}...")

    output = run_gh_command([
        "api", f"/orgs/{org}/dependabot/alerts",
        "--paginate"
    ], timeout=300)

    if not output:
        print(f"    ERROR: Failed to fetch alerts for {org} (check token permissions)", file=sys.stderr)
        return False, []

    try:
        all_alerts = json.loads(output)
    except json.JSONDecodeError as e:
        print(f"    ERROR: JSON decode error for {org}: {e}", file=sys.stderr)
        return False, []

    severities = {"critical", "high"}
    if include_medium:
        severities.add("medium")

    alerts = [
        a for a in all_alerts
        if a.get("state") == "open" and
        a.get("security_advisory", {}).get("severity", "").lower() in severities
    ]

    print(f"    Found {len(alerts)} open alerts (critical/high{'/medium' if include_medium else ''})")
    return True, alerts


def get_repo_topics(org: str, repo: str) -> list[str]:
    """Get topics for a specific repository."""
    output = run_gh_command([
        "api", f"/repos/{org}/{repo}/topics",
        "-q", ".names"
    ], silent=True)

    if not output:
        return []

    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return []


def extract_team_topics(topics: list[str]) -> list[str]:
    """Extract team-* topics from a list of topics."""
    return [t for t in topics if t.startswith("team-")]


def generate_report(
    orgs: list[str],
    include_medium: bool = False,
    output_path: Path = None
) -> str:
    """Generate the full Dependabot report."""

    if output_path is None:
        raise ValueError("--output is required")

    team_repos: dict[str, list[dict]] = defaultdict(list)
    unowned_repos: list[dict] = []
    total_by_severity: dict[str, int] = defaultdict(int)
    repo_data_map: dict[str, dict] = {}
    repo_topics_cache: dict[str, list[str]] = {}

    print("Scanning organizations for Dependabot alerts...")

    all_alerts = []
    failed_orgs = []
    for org in orgs:
        success, org_alerts = get_org_alerts(org, include_medium)
        if not success:
            failed_orgs.append(org)
        all_alerts.extend(org_alerts)

    if failed_orgs:
        print(f"\nERROR: Failed to fetch alerts from: {', '.join(failed_orgs)}", file=sys.stderr)
        if len(failed_orgs) == len(orgs):
            print("All organizations failed. This is likely a token permissions issue.", file=sys.stderr)
            print("The GH_TOKEN needs 'security_events' scope (classic) or Dependabot alerts read access (fine-grained).", file=sys.stderr)
            sys.exit(1)

    print(f"\nTotal alerts across all orgs: {len(all_alerts)}")

    if not all_alerts:
        print("No alerts found.")
    else:
        for alert in all_alerts:
            repo_info = alert.get("repository", {})
            full_name = repo_info.get("full_name", "")
            org = repo_info.get("owner", {}).get("login", "")
            repo_name = repo_info.get("name", "")

            if not full_name:
                continue

            if full_name not in repo_data_map:
                if full_name not in repo_topics_cache:
                    print(f"  Fetching topics for {full_name}...")
                    repo_topics_cache[full_name] = get_repo_topics(org, repo_name)

                repo_data_map[full_name] = {
                    "name": repo_name,
                    "full_name": full_name,
                    "org": org,
                    "alerts": [],
                    "severity_counts": defaultdict(int),
                    "total_alerts": 0,
                    "security_url": f"https://github.com/{full_name}/security/dependabot",
                    "topics": repo_topics_cache[full_name]
                }

            sev = alert.get("security_advisory", {}).get("severity", "unknown").lower()
            repo_data_map[full_name]["alerts"].append(alert)
            repo_data_map[full_name]["severity_counts"][sev] += 1
            repo_data_map[full_name]["total_alerts"] += 1
            total_by_severity[sev] += 1

        for full_name, repo_data in repo_data_map.items():
            teams = extract_team_topics(repo_data.get("topics", []))
            if teams:
                for team in teams:
                    team_repos[team].append(repo_data)
            else:
                unowned_repos.append(repo_data)

        print(f"\nRepositories with alerts: {len(repo_data_map)}")
        print(f"  Assigned to teams: {len(set(r['full_name'] for repos in team_repos.values() for r in repos))}")
        print(f"  Unowned: {len(unowned_repos)}")

    today = datetime.now().strftime("%Y-%m-%d")

    lines = [
        "# Dependabot Security Alerts Report",
        "",
        f"> Generated: {today}",
        "",
        "## Executive Summary",
        "",
        "| Severity | Count |",
        "|----------|-------|",
    ]

    for sev in ["critical", "high", "medium"]:
        if sev in total_by_severity or (sev != "medium" or include_medium):
            lines.append(f"| {sev.capitalize()} | {total_by_severity.get(sev, 0)} |")

    total_alerts = sum(total_by_severity.values())
    lines.extend([
        "",
        f"**Total open alerts: {total_alerts}**",
        "",
        f"**Organizations scanned:** {', '.join(orgs)}",
        "",
    ])

    if total_alerts == 0:
        lines.extend([
            "No critical or high severity Dependabot alerts found.",
            ""
        ])
    else:
        lines.append("## Alerts by Team")
        lines.append("")

        for team in sorted(team_repos.keys()):
            repos = team_repos[team]
            team_total = sum(r["total_alerts"] for r in repos)

            lines.append(f"### {team} ({team_total} alerts)")
            lines.append("")
            lines.append("| Repository | Critical | High | Link |")
            lines.append("|------------|----------|------|------|")

            for repo in sorted(repos, key=lambda r: -r["total_alerts"]):
                crit = repo["severity_counts"].get("critical", 0)
                high = repo["severity_counts"].get("high", 0)
                lines.append(
                    f"| {repo['full_name']} | {crit} | {high} | "
                    f"[View]({repo['security_url']}) |"
                )

            lines.append("")

        if unowned_repos:
            unowned_total = sum(r["total_alerts"] for r in unowned_repos)
            lines.append(f"### Unowned Repositories ({unowned_total} alerts)")
            lines.append("")
            lines.append("These repositories have no `team-*` topic assigned:")
            lines.append("")
            lines.append("| Repository | Critical | High | Link |")
            lines.append("|------------|----------|------|------|")

            for repo in sorted(unowned_repos, key=lambda r: -r["total_alerts"]):
                crit = repo["severity_counts"].get("critical", 0)
                high = repo["severity_counts"].get("high", 0)
                lines.append(
                    f"| {repo['full_name']} | {crit} | {high} | "
                    f"[View]({repo['security_url']}) |"
                )

            lines.append("")

    if total_alerts > 0:
        lines.append("## Alert Details")
        lines.append("")

        all_repos = []
        for repos in team_repos.values():
            all_repos.extend(repos)
        all_repos.extend(unowned_repos)

        seen = set()
        unique_repos = []
        for repo in all_repos:
            if repo["full_name"] not in seen:
                seen.add(repo["full_name"])
                unique_repos.append(repo)

        for repo in sorted(unique_repos, key=lambda r: -r["total_alerts"]):
            lines.append(f"### {repo['full_name']}")
            lines.append("")

            for alert in sorted(
                repo["alerts"],
                key=lambda a: (
                    0 if a.get("security_advisory", {}).get("severity") == "critical" else 1,
                    a.get("created_at", "")
                )
            ):
                advisory = alert.get("security_advisory", {})
                vuln = alert.get("security_vulnerability", {})
                pkg = vuln.get("package", {})

                sev = advisory.get("severity", "unknown").upper()
                pkg_name = pkg.get("name", "unknown")
                ecosystem = pkg.get("ecosystem", "")
                summary = advisory.get("summary", "No description")
                html_url = alert.get("html_url", "")
                patched = vuln.get("first_patched_version", {})
                patched_ver = patched.get("identifier", "No patch available") if patched else "No patch available"

                lines.append(f"- **[{sev}]** `{pkg_name}` ({ecosystem})")
                lines.append(f"  - {summary}")
                lines.append(f"  - Patched in: {patched_ver}")
                lines.append(f"  - [View alert]({html_url})")
                lines.append("")

            lines.append("")

    report = "\n".join(lines)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)

    print(f"\nReport written to: {output_path}")
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Generate Dependabot security alerts report"
    )
    parser.add_argument(
        "--org",
        action="append",
        dest="orgs",
        help="Specific org to scan (can be repeated). Default: all three orgs"
    )
    parser.add_argument(
        "--include-medium",
        action="store_true",
        help="Include medium severity alerts"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output file path (required)"
    )

    args = parser.parse_args()

    orgs = args.orgs if args.orgs else ORGS

    generate_report(
        orgs=orgs,
        include_medium=args.include_medium,
        output_path=args.output
    )


if __name__ == "__main__":
    main()
