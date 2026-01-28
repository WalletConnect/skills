# Code Review

Review code changes using THREE (3) to FOUR (4) parallel subagents and correlate results into a summary ranked by severity. Each subagent should use the instructions from `~/.claude/agents/code-review.md`.

Use the provided user guidance to steer the review and focus on specific code paths, changes, and/or areas of concern.

**User Guidance:** $ARGUMENTS

## Default Behavior

1. Review **uncommitted changes** by default (`git diff` and `git diff --staged`)
2. If no uncommitted changes exist, review the **last commit** (`git show HEAD`)
3. If the user provides a **pull request number or link**, use `gh pr diff <number>` to fetch changes

## Workflow

1. First, determine what to review based on the rules above
2. Check if the changes include AWS infrastructure files:
   - Terraform files (`*.tf`)
   - CDK files (TypeScript files containing `aws-cdk`, `@aws-cdk`, `cdk.Stack`, `cdk.App`, or `Construct` patterns)
3. Launch parallel Task agents:
   - THREE agents with `subagent_type: general-purpose`, each instructed to:
     - Read the full file context (not just diffs) to understand surrounding logic
     - Focus on different aspects: bugs/logic, security/auth, and patterns/structure
     - Follow the detailed review guidelines from the code-review agent
   - If AWS infrastructure detected: ONE additional agent with `subagent_type: aws-limits` to review AWS service quota violations in the changed infrastructure files
4. Collect all findings and produce a **consolidated summary**
5. Rank issues by severity: Critical > High > Medium > Low
6. Include file paths and line numbers for each finding
7. Suggest fixes where appropriate

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
