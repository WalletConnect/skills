---
name: hubspot-security-queue
description: Summarizes the HubSpot security ticket pipeline queue. Shows all tickets, unassigned items, tickets by stage, and AI triage status. Use for security queue reviews, standup prep, or tracking triage backlog.
allowed-tools: Read, Bash(python3:*), Write
---

# HubSpot Security Pipeline Queue Report

## Goal

Generate a markdown report summarizing the security ticket pipeline in HubSpot: total tickets, breakdown by stage, unassigned tickets needing attention, and AI triage status.

## When to use

- Security queue standup prep
- Checking triage backlog
- Reviewing unassigned tickets
- Tracking AI triage coverage
- Security ops reporting

## When not to use

- Creating or updating individual tickets (use HubSpot directly)
- Non-security pipelines

## Prerequisites

- `HUBSPOT_API_KEY` environment variable set with access to the security pipeline
- Python 3.10+

## Default workflow

1. Run the report generator script, passing all user arguments through:

```bash
python3 ~/.claude/skills/hubspot-security-queue/scripts/security_queue_report.py --output <path> $ARGUMENTS
```

`--output` is **required** — always provide a path. Suggested defaults:
- Local: `~/reports/security-ops/YYYY-MM-DD-security-queue.md`
- CI: `./report.md`

If the user doesn't specify an output path, use the local default with today's date.

2. Read and present a summary of the generated report.

3. Offer to share findings with relevant teams.

## Script options

```bash
# Default pipeline (--output is required)
python3 ~/.claude/skills/hubspot-security-queue/scripts/security_queue_report.py \
  --output ~/reports/security-ops/2026-03-19-security-queue.md

# Custom pipeline ID
python3 ~/.claude/skills/hubspot-security-queue/scripts/security_queue_report.py \
  --output /tmp/report.md --pipeline-id 123456789
```

## Report structure

The generated report includes:

- **Executive Summary**: Table with total tickets, count per stage, unassigned count, AI triaged vs pending
- **Unassigned Tickets**: Table of tickets with no owner — Subject, Stage, Created, AI Summary
- **Tickets by Stage**: For each stage (sorted by display order), a table with Subject, Owner, Created, Priority, AI Summary
- **AI Triage Summary**: Counts for In Scope, Out of Scope, Needs Review, Not Triaged

## Slack delivery

**Local (interactive):** After generating the report, summarize key findings and offer to post to Slack using the Slack MCP tool if available. The summary should include total ticket count, unassigned count, and triage status.

**CI:** The `scripts/run-report.mjs` wrapper runs the Python script, uses the Anthropic Messages API to compose a Slack summary, and posts it via webhook.

## Validation checklist

- [ ] Report file created at the specified `--output` path
- [ ] All pipeline stages resolved to names (not raw IDs)
- [ ] Owner names resolved (not raw IDs)
- [ ] Unassigned tickets section populated
- [ ] AI triage summary has all four categories
