---
name: rust-production-readiness
description: Audits Rust code for production readiness. Use when preparing Rust code for release, reviewing PRs before merge, or assessing code quality before shipping to production.
---

# Rust Production Readiness Audit

## Goal
Systematically evaluate Rust code against production-readiness criteria and produce an actionable report with findings and recommendations.

## When to use
- Before merging a PR to main
- Before cutting a release
- When onboarding to assess codebase health
- After major refactoring

## When not to use
- For prototype/experimental code
- For test-only code review
- When you just need a quick syntax check (use `cargo check` instead)

## Inputs
- Rust codebase (current directory or specified path)
- Optional: specific files/modules to focus on

## Outputs
- Structured audit report with severity ratings
- Specific file:line references for issues
- Recommended fixes

## Default workflow

1) **Gather context**
   - Read `Cargo.toml` for dependencies and features
   - Check for `CLAUDE.md` or project-specific conventions
   - Identify the crate type (library, binary, FFI)

2) **Run automated checks**
   ```bash
   cargo clippy --all-targets --all-features -- -D warnings
   cargo audit
   cargo test --all-features
   ```

3) **Manual code review** (see CHECKLIST.md for details)
   - Error handling patterns
   - Panic vectors
   - Unsafe code
   - Async pitfalls
   - Performance concerns

4) **Generate report**
   - Group findings by severity (Critical/High/Medium/Low)
   - Include file:line references
   - Provide fix recommendations

## Severity definitions

| Severity | Criteria |
|----------|----------|
| Critical | Can cause crashes, data loss, or security vulnerabilities in production |
| High | Likely to cause issues under load or edge cases |
| Medium | Code smell or maintainability concern |
| Low | Style or minor improvement suggestion |

## Quick checklist (detailed version in CHECKLIST.md)

- [ ] No `unwrap()` or `expect()` in non-test code paths
- [ ] All `Result` types handled or explicitly propagated
- [ ] No `panic!` in library code
- [ ] `unsafe` blocks documented with safety invariants
- [ ] Async code avoids holding locks across `.await`
- [ ] No unbounded allocations (Vec growth, string concat in loops)
- [ ] Dependencies audited (`cargo audit` clean)
- [ ] Public API documented
- [ ] Error types are meaningful (not just `String`)

## Report template

```markdown
# Rust Production Readiness Report

**Crate:** {name}
**Version:** {version}
**Date:** {date}

## Summary
- Critical: {n}
- High: {n}
- Medium: {n}
- Low: {n}

## Automated checks
- [ ] `cargo clippy`: {PASS/FAIL}
- [ ] `cargo audit`: {PASS/FAIL}
- [ ] `cargo test`: {PASS/FAIL}

## Findings

### Critical
{findings or "None"}

### High
{findings or "None"}

### Medium
{findings or "None"}

### Low
{findings or "None"}

## Recommendations
{prioritized action items}
```

## Examples

### Example 1: Focused module audit
**Input:** "Check the `src/account_client/` module for production readiness"
**Output:** Report focused on that module with findings like:
- `src/account_client/mod.rs:142` - `unwrap()` on user input parsing (Critical)
- `src/account_client/retry.rs:58` - Unbounded retry loop (High)

### Example 2: Pre-release full audit
**Input:** "/rust-production-readiness"
**Output:** Full crate audit with all checks run, summary statistics, and prioritized fix list.

## Evaluation prompts

1. **Activation test:** "Review this Rust code for production readiness before we ship"
   - Should trigger this skill

2. **Non-activation test:** "Help me write a new function to parse JSON"
   - Should NOT trigger (this is feature development, not audit)

3. **Edge case:** "Is this Rust code ready for prod?" (no specific files mentioned)
   - Should trigger, audit entire crate in current directory
