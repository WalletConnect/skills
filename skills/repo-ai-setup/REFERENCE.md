# Repo Setup Reference

## AGENTS.md Format Guide

Expected sections (not a rigid template — adapt to the repo):

```markdown
# AGENTS.md

This file provides guidance to AI coding agents working with this repository.

## Repository Purpose
Brief description of what the project does and its role in the ecosystem.

## Architecture
High-level directory structure and key modules.

## Tech Stack
Languages, frameworks, and major dependencies.

## Commands
```bash
# Build
<build command>

# Test
<test command>

# Lint
<lint command>

# Format
<format command>
```

## Testing
Testing conventions, frameworks, and patterns used.

## Code Style & Conventions
Naming conventions, file organization patterns, import ordering, etc.

## Development Workflow
Branch strategy, PR process, CI/CD notes.
```

Key principles:
- Agent-agnostic language (no "Claude" or tool-specific references)
- Focus on what an AI agent needs to be productive in the codebase
- Include runnable commands (build, test, lint) so agents can verify their work
- Keep concise — link to detailed docs rather than duplicating them

---

## Claude Auto-Review Workflow Template

Use this template for `.github/workflows/claude-review.yml`. Replace `{DEFAULT_BRANCH}` with the repo's default branch name.

```yaml
name: Claude Auto Review

on:
  pull_request:
    types: [opened]
    branches: [{DEFAULT_BRANCH}]
  issue_comment:
    types: [created]

jobs:
  review:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    if: |
      github.event_name == 'pull_request'
      || (
        github.event_name == 'issue_comment'
        && github.event.issue.pull_request
        && contains(github.event.comment.body, '@claude review')
      )
    permissions:
      contents: read
      pull-requests: write
      issues: write
      id-token: write
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Claude Review
        uses: WalletConnect/actions/claude/auto-review@master
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

---

## Action Inputs Reference

Full inputs for `WalletConnect/actions/claude/auto-review`:

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `anthropic_api_key` | Yes | — | Anthropic API key |
| `model` | No | `claude-sonnet-4-6` | Claude model for reviews |
| `project_context` | No | — | Project-specific review context |
| `custom_prompt` | No | — | Full prompt override (ignores other prompt inputs) |
| `comment_pr_findings` | No | `true` | Post inline PR comments from findings |
| `force_breaking_changes_agent` | No | `false` | Force breaking changes subagent |
| `force_license_compliance_agent` | No | `false` | Force license compliance subagent |
| `force_data_classification_agent` | No | `false` | Force data classification subagent |

### Optional Workflow Additions

To add `project_context` to the workflow:

```yaml
      - name: Claude Review
        uses: WalletConnect/actions/claude/auto-review@master
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          project_context: |
            This is a Rust backend service. Focus on memory safety,
            error handling, and API contract compliance.
```
