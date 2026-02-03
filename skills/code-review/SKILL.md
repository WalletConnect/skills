---
name: code-review
description: Provide actionable feedback on code changes. Focuses on bugs, security issues, and structural problems.
---

# Code Review

Review code changes using THREE (3) to FOUR (4) parallel subagents and correlate results into a summary ranked by severity.

Use the provided user guidance to steer the review and focus on specific code paths, changes, and/or areas of concern.

**User Guidance:** $ARGUMENTS

## Default Behavior

1. Review **uncommitted changes** by default (`git diff` and `git diff --staged`)
2. If no uncommitted changes exist, review the **last commit** (`git show HEAD`)
3. If the user provides a **pull request number or link**, use `gh pr diff <number>` to fetch changes

## Workflow

1. First, determine what to review based on the rules above
2. Check if the changes include AWS infrastructure files:
   - Terraform files (`*.tf`) containing AWS patterns (`provider "aws"`, `aws_` resources, or `hashicorp/aws`)
   - CDK files (TypeScript files containing `aws-cdk`, `@aws-cdk`, `cdk.Stack`, `cdk.App`, or `Construct` patterns)
3. Launch parallel Task agents:
   - THREE agents with `subagent_type: general-purpose`, each instructed to:
     - Read the full file context (not just diffs) to understand surrounding logic
     - Focus on different aspects: bugs/logic, security/auth, and patterns/structure
     - Follow the detailed review guidelines below
   - If AWS infrastructure detected: ONE additional agent with `subagent_type: aws-limits` to review AWS service quota violations in the changed infrastructure files
4. Collect all findings and produce a **consolidated summary**
5. Rank issues by severity: Critical > High > Medium > Low
6. Include file paths and line numbers for each finding
7. Suggest fixes where appropriate

## Review Guidelines

**Diffs alone are not enough.** Read the full file(s) being modified to understand context. Code that looks wrong in isolation may be correct given surrounding logic.

### What to Look For

#### Bugs — Primary focus
- Logic errors, off-by-one mistakes, incorrect conditionals
- Missing guards, unreachable code paths, broken error handling
- Edge cases: null/empty inputs, race conditions
- Security: injection, auth bypass, data exposure

#### Structure — Does the code fit the codebase?
- Follows existing patterns and conventions?
- Uses established abstractions?
- Excessive nesting that could be flattened?

#### Performance — Only flag if obviously problematic
- O(n²) on unbounded data, N+1 queries, blocking I/O on hot paths

### Before You Flag Something

- **Be certain.** Don't flag something as a bug if you're unsure — investigate first.
- **Don't invent hypothetical problems.** If an edge case matters, explain the realistic scenario.
- **Don't be a zealot about style.** Some "violations" are acceptable when they're the simplest option.
- Only review the changes — not pre-existing code that wasn't modified.

### Output Guidelines

- Be direct about bugs and why they're bugs
- Communicate severity honestly — don't overstate
- Include file paths and line numbers
- Suggest fixes when appropriate
- Matter-of-fact tone, no flattery

### Severity Levels

- **Critical**: Security vulnerabilities, data loss, crashes in production
- **High**: Bugs that will cause incorrect behavior, broken functionality
- **Medium**: Code that works but has issues (poor error handling, edge cases)
- **Low**: Style issues, minor improvements, suggestions

## Output Format

```
## Code Review Summary

### Critical Issues
- [file:line] Description of critical bug/security issue

### High Priority
- [file:line] Description

### Medium Priority
- [file:line] Description

### Low Priority / Suggestions
- [file:line] Description

### AWS Service Limits (if applicable)
- [file:line] Description of limit concern

### Summary
Brief overall assessment of the changes.
```
