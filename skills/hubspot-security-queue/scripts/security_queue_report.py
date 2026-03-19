#!/usr/bin/env python3
"""
HubSpot Security Pipeline Queue Report Generator

Fetches tickets from the HubSpot security pipeline and generates a markdown
report with queue status, unassigned tickets, stage breakdown, and AI triage summary.

Uses only Python stdlib (urllib.request, json, etc.) — no pip dependencies.
"""

from __future__ import annotations

import json
import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

DEFAULT_PIPELINE_ID = "638418092"
HUBSPOT_API_BASE = "https://api.hubapi.com"

# AI triage classification constants
AI_IN_SCOPE = "in_scope"
AI_OUT_OF_SCOPE = "out_of_scope"
AI_NEEDS_REVIEW = "needs_review"
AI_NOT_TRIAGED = "not_triaged"

TICKET_PROPERTIES = [
    "subject",
    "content",
    "hs_pipeline_stage",
    "hubspot_owner_id",
    "createdate",
    "hs_lastmodifieddate",
    "hs_ticket_priority",
    "security_pipeline_ai_assessment",
]


def hubspot_request(
    path: str,
    api_key: str,
    method: str = "GET",
    body: Optional[dict] = None,
    max_retries: int = 3,
) -> Optional[dict]:
    """Make a HubSpot API request with retry on 429."""
    url = f"{HUBSPOT_API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    data = json.dumps(body).encode("utf-8") if body else None

    for attempt in range(max_retries):
        try:
            req = Request(url, data=data, headers=headers, method=method)
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 429:
                wait = 2 ** (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            body_text = e.read().decode("utf-8", errors="replace") if e.fp else ""
            print(f"  HTTP {e.code}: {body_text[:200]}", file=sys.stderr)
            return None
        except URLError as e:
            print(f"  Network error: {e.reason}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)
            return None

    print("  Max retries exceeded", file=sys.stderr)
    return None


def fetch_pipeline_stages(pipeline_id: str, api_key: str) -> dict[str, dict]:
    """Fetch pipeline stage definitions. Returns {stage_id: {"label": str, "displayOrder": int}}."""
    print(f"  Fetching pipeline stages for {pipeline_id}...")
    result = hubspot_request(f"/crm/v3/pipelines/tickets/{pipeline_id}", api_key)
    if not result:
        print("    ERROR: Failed to fetch pipeline stages", file=sys.stderr)
        return {}

    stages = {}
    for stage in result.get("stages", []):
        metadata = stage.get("metadata", {})
        stages[stage["id"]] = {
            "label": stage.get("label", stage["id"]),
            "displayOrder": stage.get("displayOrder", 0),
            "isClosed": metadata.get("isClosed", "false") == "true",
        }

    print(f"    Found {len(stages)} stages")
    return stages


def fetch_owners(api_key: str) -> dict[str, str]:
    """Fetch all owners (paginated). Returns {owner_id: "First Last"}."""
    print("  Fetching owners...")
    owners = {}
    after = None

    while True:
        path = "/crm/v3/owners/?limit=100"
        if after:
            path += f"&after={after}"

        result = hubspot_request(path, api_key)
        if not result:
            break

        for owner in result.get("results", []):
            owner_id = str(owner.get("id", ""))
            first = owner.get("firstName", "")
            last = owner.get("lastName", "")
            name = f"{first} {last}".strip() or owner.get("email", owner_id)
            owners[owner_id] = name

        paging = result.get("paging", {})
        next_page = paging.get("next", {})
        after = next_page.get("after")
        if not after:
            break

    print(f"    Found {len(owners)} owners")
    return owners


def fetch_all_tickets(
    pipeline_id: str, api_key: str, exclude_stage_ids: Optional[set[str]] = None
) -> list[dict]:
    """Fetch open tickets in the pipeline via search API (paginated). Returns list of ticket dicts."""
    print(f"  Fetching tickets for pipeline {pipeline_id}...")
    tickets = []
    after = None
    max_pages = 50

    filters = [
        {
            "propertyName": "hs_pipeline",
            "operator": "EQ",
            "value": pipeline_id,
        }
    ]
    if exclude_stage_ids:
        filters.append({
            "propertyName": "hs_pipeline_stage",
            "operator": "NOT_IN",
            "values": list(exclude_stage_ids),
        })

    for page in range(max_pages):
        body = {
            "filterGroups": [{"filters": filters}],
            "properties": TICKET_PROPERTIES,
            "limit": 100,
        }
        if after:
            body["after"] = after

        result = hubspot_request(
            "/crm/v3/objects/tickets/search", api_key, method="POST", body=body
        )
        if not result:
            print("    ERROR: Failed to fetch tickets page", file=sys.stderr)
            break

        page_results = result.get("results", [])
        tickets.extend(page_results)

        paging = result.get("paging", {})
        next_page = paging.get("next", {})
        after = next_page.get("after")
        if not after:
            break

        print(f"    Page {page + 1}: {len(page_results)} tickets (total: {len(tickets)})")

    print(f"    Total tickets fetched: {len(tickets)}")
    return tickets


def parse_ai_assessment(text: Optional[str]) -> str:
    """Extract a one-line summary from the freeform AI assessment field."""
    if not text or not text.strip():
        return "Not triaged"

    text = text.strip()

    # Try to extract the first meaningful line
    first_line = text.split("\n")[0].strip()

    # Truncate if too long
    if len(first_line) > 120:
        first_line = first_line[:117] + "..."

    return first_line


def classify_ai_assessment(text: Optional[str]) -> str:
    """Classify AI assessment into a category for the summary."""
    if not text or not text.strip():
        return AI_NOT_TRIAGED

    lower = text.lower()
    if "in scope" in lower or "in-scope" in lower:
        return AI_IN_SCOPE
    elif "out of scope" in lower or "out-of-scope" in lower:
        return AI_OUT_OF_SCOPE
    elif "needs review" in lower or "needs human" in lower or "uncertain" in lower:
        return AI_NEEDS_REVIEW
    else:
        return AI_NEEDS_REVIEW


def generate_report(
    tickets: list[dict],
    stage_map: dict[str, dict],
    owner_map: dict[str, str],
    output_path: Path,
) -> str:
    """Build markdown report and write to output_path. Tickets should already be filtered to open only."""
    today = datetime.now().strftime("%Y-%m-%d")

    # Single pass: organize tickets by stage, track unassigned, and count AI categories
    by_stage: dict[str, list[dict]] = defaultdict(list)
    unassigned: list[dict] = []
    ai_counts = defaultdict(int)

    for ticket in tickets:
        props = ticket.get("properties", {})
        stage_id = props.get("hs_pipeline_stage", "")
        owner_id = props.get("hubspot_owner_id", "")

        by_stage[stage_id].append(ticket)

        if not owner_id or owner_id.strip() == "":
            unassigned.append(ticket)

        ai_counts[classify_ai_assessment(props.get("security_pipeline_ai_assessment", ""))] += 1

    total = len(tickets)
    unassigned_count = len(unassigned)

    # Sort stages by display order
    sorted_stages = sorted(
        by_stage.keys(),
        key=lambda sid: stage_map.get(sid, {}).get("displayOrder", 999),
    )

    lines = [
        "# 🔒 Security Pipeline Queue Report",
        "",
        f"> Generated: {today}",
        "",
        "## 📊 Executive Summary",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Total tickets | {total} |",
    ]

    for stage_id in sorted_stages:
        stage_name = stage_map.get(stage_id, {}).get("label", stage_id)
        count = len(by_stage[stage_id])
        lines.append(f"| {stage_name} | {count} |")

    lines.extend([
        f"| **Unassigned** | **{unassigned_count}** |",
        f"| AI triaged | {total - ai_counts.get(AI_NOT_TRIAGED, 0)} |",
        f"| Pending triage | {ai_counts.get(AI_NOT_TRIAGED, 0)} |",
        "",
    ])

    # Unassigned tickets section
    lines.extend([
        "## ⚠️ Unassigned Tickets",
        "",
    ])

    if unassigned:
        lines.extend([
            "| Subject | Stage | Priority | Created | AI Summary |",
            "|---------|-------|----------|---------|------------|",
        ])

        for ticket in unassigned:
            props = ticket.get("properties", {})
            subject = props.get("subject", "—") or "—"
            ticket_url = ticket.get("url", "")
            if ticket_url:
                subject = f"[{subject}]({ticket_url})"
            stage_id = props.get("hs_pipeline_stage", "")
            stage_name = stage_map.get(stage_id, {}).get("label", stage_id)
            priority = props.get("hs_ticket_priority", "—") or "—"
            created = (props.get("createdate", "") or "")[:10]
            ai_summary = parse_ai_assessment(props.get("security_pipeline_ai_assessment"))
            lines.append(f"| {subject} | {stage_name} | {priority} | {created} | {ai_summary} |")

        lines.append("")
    else:
        lines.extend(["All tickets are assigned.", ""])

    # Tickets by stage
    lines.extend([
        "## 📋 Tickets by Stage",
        "",
    ])

    for stage_id in sorted_stages:
        stage_name = stage_map.get(stage_id, {}).get("label", stage_id)
        stage_tickets = by_stage[stage_id]
        count = len(stage_tickets)

        lines.extend([
            f"### {stage_name} ({count})",
            "",
            "| Subject | Owner | Created | Priority | AI Summary |",
            "|---------|-------|---------|----------|------------|",
        ])

        for ticket in stage_tickets:
            props = ticket.get("properties", {})
            subject = props.get("subject", "—") or "—"
            ticket_url = ticket.get("url", "")
            if ticket_url:
                subject = f"[{subject}]({ticket_url})"
            owner_id = props.get("hubspot_owner_id", "")
            owner_name = owner_map.get(owner_id, "Unassigned") if owner_id else "Unassigned"
            created = (props.get("createdate", "") or "")[:10]
            priority = props.get("hs_ticket_priority", "—") or "—"
            ai_summary = parse_ai_assessment(props.get("security_pipeline_ai_assessment"))
            lines.append(f"| {subject} | {owner_name} | {created} | {priority} | {ai_summary} |")

        lines.append("")

    # AI Triage Summary
    lines.extend([
        "## 🤖 AI Triage Summary",
        "",
        "| Category | Count |",
        "|----------|-------|",
        f"| In Scope | {ai_counts.get(AI_IN_SCOPE, 0)} |",
        f"| Out of Scope | {ai_counts.get(AI_OUT_OF_SCOPE, 0)} |",
        f"| Needs Review | {ai_counts.get(AI_NEEDS_REVIEW, 0)} |",
        f"| Not Triaged | {ai_counts.get(AI_NOT_TRIAGED, 0)} |",
        "",
    ])

    report = "\n".join(lines)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)

    print(f"\nReport written to: {output_path}")
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Generate HubSpot security pipeline queue report"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output file path (required)",
    )
    parser.add_argument(
        "--pipeline-id",
        default=DEFAULT_PIPELINE_ID,
        help=f"HubSpot pipeline ID (default: {DEFAULT_PIPELINE_ID})",
    )

    args = parser.parse_args()

    api_key = os.environ.get("HUBSPOT_API_KEY")
    if not api_key:
        print("ERROR: HUBSPOT_API_KEY environment variable is required", file=sys.stderr)
        sys.exit(1)

    print("Generating security pipeline queue report...")

    stage_map = fetch_pipeline_stages(args.pipeline_id, api_key)
    closed_stage_ids = {
        sid for sid, info in stage_map.items() if info.get("isClosed", False)
    }

    owner_map = fetch_owners(api_key)
    tickets = fetch_all_tickets(args.pipeline_id, api_key, exclude_stage_ids=closed_stage_ids)

    generate_report(tickets, stage_map, owner_map, args.output)


if __name__ == "__main__":
    main()
