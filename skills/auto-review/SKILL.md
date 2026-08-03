---
name: auto-review
description: Runs a local Claude code review of branch changes before opening a PR, mirroring the WalletConnect/actions claude/auto-review GitHub Action. Same review scope, the same automated checks (PR size, external-domain URLs, cache-control, GitHub Actions security, WalletConnect Pay architecture), and the same conditional breaking-changes / license-compliance / data-classification subagents — but reads the local git diff instead of the GitHub PR API and prints findings to the terminal. Use when the user says "auto-review", "review my changes before PR", "run the auto review locally", "pre-PR review", or wants the CI review run before pushing.
---

# Auto Review (local)

## Goal

Reproduce the WalletConnect `claude/auto-review` GitHub Action **locally**, against the current branch's changes, so issues are caught before the PR is opened. Same review scope, same automated checks, same severity/ID output format, same three conditional subagents — just sourced from `git diff` instead of the GitHub PR API.

## When to use

- Before opening or pushing a PR, to preview what CI auto-review will flag.
- The user says "auto-review", "review my changes", "pre-PR review", "run the auto review locally".

## When not to use

- Reviewing an already-open PR on GitHub — use the CI action or `gh`-based review instead; this skill is for local, pre-push changes.
- General "explain this code" requests with no review intent.

## Critical constraints (match the action exactly)

- **Read-only.** No builds, no test runs, no shell mutations. Inspection only.
- **Issues-only.** Report problems, never praise. If nothing is found, say `✅ No issues found`.
- **Be extremely concise.** Sacrifice grammar for concision.
- **Diffs alone are not enough.** `Read` the full file around each change — code that looks wrong in isolation may be correct in context.
- This is a **full review** every run. The action's "incremental review" mode (reusing IDs from prior PR comments) does **not** apply locally — there are no prior comments.

## Workflow

### 1. Determine the diff scope

Establish the base and collect changed files + patches. Default base is the repo's main branch (`main`, else `master`). Let the user override (e.g. "review against develop").

```bash
# Base ref (prefer the tracked upstream's base; fall back to origin/main then main)
BASE="${BASE:-$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null | sed 's#/.*##' >/dev/null; echo origin/main)}"
git fetch origin --quiet 2>/dev/null || true

# Changed files (committed-on-branch + staged + unstaged) vs the merge-base
MB=$(git merge-base HEAD "$BASE" 2>/dev/null || git rev-parse HEAD)
git diff --name-status "$MB" -- ; echo "--- working tree ---" ; git status --porcelain
```

Use whichever combination reflects "what this PR will contain." If the branch has commits, diff `merge-base..HEAD`; if work is uncommitted, include the working tree. Get full patches with `git diff "$MB"` (and `git diff` / `git diff --staged` for uncommitted work).

If there are no changes, output `✅ No issues found` and stop.

### 2. Decide which subagents to spawn (heuristic gating)

Apply the heuristics in **[HEURISTICS.md](HEURISTICS.md)** to the changed-file list + patch text. Each yields a `{ spawn, reason }` decision:

- **Breaking changes** — `action.yml`/workflows, package manifests, type defs, API routes, schema/migration files, removed files, or breaking-change keywords in the patch.
- **License compliance** — any dependency manifest or lockfile changed.
- **Data classification** — IaC/Terraform, k8s/Helm, CloudFormation, env/secret files, db schema, API handlers, or sensitive-data keywords in the patch.

Skip-all if every changed file is docs-only or test-only (per the rules in HEURISTICS.md). The user can force any subagent on ("force breaking changes", etc.). State each decision briefly, e.g. `breaking-changes: spawn (package manifests, removed files)`.

### 3. Run the main review

Follow **[REVIEW_PROMPT.md](REVIEW_PROMPT.md)** — the review scope and the five automated checks (PR size, external-domain URLs, cache-control, GitHub Actions security, WalletConnect Pay architecture). Use `Read`, `Glob`, `Grep` to inspect full files; do not rely on the diff alone.

### 4. Spawn the gated subagents (in parallel)

For each subagent whose decision was `spawn: true`, launch a `general-purpose` agent via the Agent tool. Pass it:

1. "Read your spec file at `<this skill's directory>/agents/<spec>.md` — the `auto-review` skill folder containing this SKILL.md (e.g. `~/.claude/skills/auto-review/agents/<spec>.md` when installed there) — and follow its instructions."
2. The base ref and the list of changed files (with paths).
3. Instruction to review the **local working tree / branch diff**, not a GitHub PR.

Spec files: `agents/review-breaking-changes.md` (IDs `brk-`), `agents/review-license-compliance.md` (IDs `lic-`), `agents/review-data-classification.md` (IDs `dcl-`).

Launch all gated subagents in a single batch so they run concurrently.

### 5. Merge and output

Merge subagent findings into the main review's findings:

- Keep each subagent's prefixed IDs (`brk-`/`lic-`/`dcl-`) as-is.
- Deduplicate when the main review found the same issue independently — prefer the prefixed ID.
- Sort all findings by severity: **CRITICAL > HIGH > MEDIUM > LOW**.

Print the consolidated result to the terminal using the issue format in REVIEW_PROMPT.md (wrapped in a `<details>` block). If there are genuinely no issues across the main review and all subagents, output exactly `✅ No issues found`.

There is no inline-PR-comment step locally — the action's `findings.json` → GitHub comments flow is replaced by terminal output. If the user wants a file, write the findings to `auto-review-findings.md` in the repo root.

## Validation checklist

- [ ] Diff scope reflects what the PR will contain (branch commits and/or working tree), against the correct base.
- [ ] All three heuristics evaluated; spawn decisions + reasons stated.
- [ ] Full files read for flagged lines, not just the diff.
- [ ] All five automated checks considered (report only on violations).
- [ ] Findings carry ID, File:line, Severity, Category, Context, Recommendation.
- [ ] Subagent IDs keep their prefixes; duplicates merged; sorted by severity.
- [ ] No praise; `✅ No issues found` when clean.

## Notes on parity with CI

- The action defaults to model `claude-sonnet-4-6` and allows tools `Read, Glob, Grep, Task, WebFetch`. Locally, mirror the read-only tool set.
- External-domain allowlist is WalletConnect-specific: `reown.com`, `walletconnect.com`, `walletconnect.org`. Flag URLs to other domains as non-blocking.
- The WalletConnect Pay architecture check is intentionally project-specific (cross-service DB access, idempotency keys, timeouts/retries, message dedup, saga compensation, trace context).
