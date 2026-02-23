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

- **Executive summary**: Total alerts by severity across all orgs
- **Team breakdown**: Alerts grouped by GitHub topic (e.g., `team-buyer-experience`)
- **Unowned repos**: Repositories without team topics
- **Per-repo details**: Alert counts, severity, and direct links

## Team ownership

Repositories are assigned to teams based on GitHub topics matching the pattern `team-*`. Repos without team topics appear in the "Unowned" section.

## Slack delivery

**Local (interactive):** After generating the report, summarize key findings and offer to post to Slack using the Slack MCP tool if available. The summary should include total alert counts, top affected repos, and teams needing attention.

**CI:** The `WalletConnect/actions` repo has a weekly workflow (`.github/workflows/weekly-dependabot-report.yml`) that generates the report and delivers a summary to Slack via the Claude Agent SDK. See that workflow for CI-specific delivery configuration.

## Validation checklist

- [ ] Report file created at the specified `--output` path
- [ ] All three orgs scanned (check summary counts)
- [ ] Alerts grouped by team topic
- [ ] Links to GitHub security pages work
