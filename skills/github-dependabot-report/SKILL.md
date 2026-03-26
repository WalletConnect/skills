---
name: github-dependabot-report
description: Generates a Dependabot security alerts report for walletconnect, reown-com, and walletconnectfoundation GitHub orgs. Groups alerts by team ownership (GitHub topics). Use when reviewing security posture, preparing for security reviews, or tracking vulnerability remediation.
allowed-tools: Read, Bash(python3:*), Bash(gh:*), Write
---

# GitHub Dependabot Report

## Goal

Generate a markdown report of critical and high severity Dependabot alerts across Reown GitHub organizations, grouped by team ownership.

## When to use

- Weekly/monthly security posture review
- Preparing for security audits
- Tracking vulnerability remediation progress
- Assessing team-level security health

## When not to use

- Checking a single repository (use `gh api` directly)
- Non-security dependency updates

## Prerequisites

- GitHub CLI (`gh`) authenticated with access to:
  - walletconnect
  - reown-com
  - walletconnectfoundation
- Python 3.10+

### 🔑 CI token requirements

The CI workflow uses `DEPENDABOT_REPORT_GH_PAT` — this **must be a classic PAT**, not a fine-grained token. Fine-grained PATs are scoped to a single GitHub organization, but this report scans 3 orgs (`walletconnect`, `reown-com`, `walletconnectfoundation`). Only classic PATs work across multiple orgs.

Required classic PAT scope: `security_events` (read-only access to Dependabot alerts across all orgs the token owner belongs to).

## Default workflow

1. Run the report generator script, passing all user arguments through:

```bash
python3 ~/.claude/skills/github-dependabot-report/scripts/dependabot_report.py --output <path> $ARGUMENTS
```

`--output` is **required** — always provide a path. Suggested defaults:
- Local: `~/chief-of-staff/reports/security-ops/YYYY-MM-DD-dependabot-alerts.md`
- CI: `./report.md`

If the user doesn't specify an output path, use the local default with today's date.

2. Read and present a summary of the generated report.

3. Offer to share findings with relevant teams.

## Script options

```bash
# All orgs, critical+high only (--output is required)
python3 ~/.claude/skills/github-dependabot-report/scripts/dependabot_report.py \
  --output ~/chief-of-staff/reports/security-ops/2026-02-23-dependabot-alerts.md

# Include medium severity
python3 ~/.claude/skills/github-dependabot-report/scripts/dependabot_report.py \
  --output /tmp/report.md --include-medium

# Specific org only
python3 ~/.claude/skills/github-dependabot-report/scripts/dependabot_report.py \
  --output /tmp/report.md --org walletconnect

# Multiple specific orgs
python3 ~/.claude/skills/github-dependabot-report/scripts/dependabot_report.py \
  --output /tmp/report.md --org walletconnect --org reown-com
```

## Report structure

The generated report includes:

- **Executive summary**: In-scope alert counts by severity, with out-of-scope totals noted separately
- **Team breakdown**: Alerts grouped by GitHub topic (e.g., `team-buyer-experience`)
- **Unowned repos**: Repositories without team topics
- **Out of scope repos**: Repositories tagged `out-of-scope` (excluded from summary counts and alert details)
- **Per-repo details**: Alert counts, severity, and direct links (in-scope repos only)

## Team ownership

Repositories are assigned to teams based on GitHub topics matching the pattern `team-*`. Repos without team topics appear in the "Unowned" section.

## Out-of-scope filtering

Repositories tagged with the `out-of-scope` GitHub topic are separated from the main report. These are typically example/demo repos, forks, or experimental projects where Dependabot noise isn't actionable. Out-of-scope repos:

- Are **excluded** from the executive summary severity counts
- Are **excluded** from the per-repo alert details section
- Appear in their own "Out of Scope Repositories" section with a summary table

To mark a repo as out of scope, add the `out-of-scope` topic via GitHub settings or the API.

## Slack delivery

**Local (interactive):** After generating the report, summarize key findings and offer to post to Slack using the Slack MCP tool if available. The summary should include total alert counts, top affected repos, and teams needing attention.

**CI:** The `WalletConnect/skills` repo has a weekly workflow (`.github/workflows/weekly-dependabot-report.yml`) that runs the Python report script, uses the Anthropic Messages API to compose a Slack summary, and posts it via webhook.

## Validation checklist

- [ ] Report file created at the specified `--output` path
- [ ] All three orgs scanned (check summary counts)
- [ ] Alerts grouped by team topic
- [ ] Links to GitHub security pages work
