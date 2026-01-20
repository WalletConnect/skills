---
name: context-drift
description: Analyzes .claude/ context files for drift from codebase. Detects broken references, semantic mismatches, and orphaned code. Use when auditing documentation freshness, checking context alignment, or before releases.
user-invocable: true
---

# Context Drift Detector

Analyzes `.claude/` context files (skills, commands, agents) for drift from the actual codebase. Detects broken references, semantic mismatches, and identifies code that lacks documentation.

## When to use

- Auditing documentation freshness before a release
- After major refactoring to catch stale context
- Periodic maintenance to ensure docs match reality
- When onboarding to verify context files are current
- Before merging PRs that touch documented areas

## When not to use

- Writing new documentation (use `/update-docs`)
- General code quality checks (use `/tech-debt-hunt`)
- Understanding codebase structure (use `/understand-codebase`)

---

## Detection Methods

This skill uses three complementary detection approaches:

| Method | Severity | What it detects |
|--------|----------|-----------------|
| **Broken References** | Critical/High | File paths, commands, scripts that no longer exist |
| **Semantic Mismatch** | High/Medium | Documented behavior that doesn't match code |
| **Review Flags** | Low/Advisory | Potential drift needing human review |

See REFERENCE.md for detailed detection patterns.

---

## Default Workflow

### Phase 1: Discovery

1. **Find context files**:
   ```bash
   find .claude/skills -name "*.md" -type f
   find .claude/commands -name "*.md" -type f
   find .claude/agents -name "*.md" -type f
   ```

2. **Parse each file** to extract:
   - File path references (code blocks, `@path` mentions)
   - Bash commands and scripts
   - Tool/MCP references
   - Documented workflows and parameters

3. **Build reference map**: context file → referenced code paths

### Phase 2: Analysis

For each context file, run all detection methods:

1. **Validate references**:
   - Check all file paths exist
   - Verify scripts/commands are runnable
   - Confirm tool names are valid

2. **Semantic analysis** (for skills/commands):
   - Compare documented workflow steps vs actual
   - Check parameter counts match
   - Verify tool usage claims

3. **Staleness check**:
   - Get last modified date of context file
   - Check if referenced code has significant changes since
   - Flag if context untouched for 90+ days

4. **Classify by severity**: Critical → High → Medium → Low

### Phase 3: Orphan Detection

1. **Collect all referenced paths** from context files
2. **Find significant code** not referenced:
   - Files > 200 lines
   - Public exports/entry points
   - API handlers
3. **Report as "Needs Documentation"**

### Phase 4: Reporting

Generate structured report with:
- Summary counts by severity
- Critical issues (must fix)
- Semantic mismatches (should fix)
- Review flags (investigate)
- Orphaned code table

---

## Output Format

```markdown
# Context Drift Report

**Generated**: {timestamp}
**Repository**: {repo_name}

## Summary

| Category | Count |
|----------|-------|
| Context files scanned | N |
| Critical issues | X |
| Semantic mismatches | Y |
| Review flags | Z |
| Orphaned code files | O |

## Critical Issues (Broken References)

### .claude/skills/foo/SKILL.md
- **Line 45**: References `src/utils/helper.ts` - FILE NOT FOUND
- **Line 78**: Command `./scripts/validate.sh` - SCRIPT MISSING

## Semantic Mismatches

### .claude/commands/bar.md
- **Workflow drift**: Documents 3 steps, implementation has 5
- **Command drift**: Mentions `npm test`, package.json uses `bun test`

## Review Flags

### .claude/agents/baz.md
- Related code changed 15 commits since last context update
- Context file unchanged for 120 days

## Orphaned Code (Needs Documentation)

| File | Lines | Significance |
|------|-------|--------------|
| src/api/handlers.ts | 450 | Public API handler |
| src/core/engine.ts | 380 | Core module, exported |

## Recommendations

1. Fix critical issues immediately (broken references)
2. Review semantic mismatches for accuracy
3. Update or remove flagged stale documentation
4. Consider adding context for orphaned code
```

---

## Validation Checklist

- [ ] All `.claude/skills/`, `.claude/commands/`, `.claude/agents/` files discovered
- [ ] File path references extracted from code blocks and inline mentions
- [ ] Bash commands extracted and validated
- [ ] Broken references flagged as Critical
- [ ] Semantic analysis completed without false positives
- [ ] Orphaned code filtered by significance threshold
- [ ] Report sections organized by severity
- [ ] Recommendations are actionable

---

## Examples

### Example 1: Full repository scan

```
User: /context-drift

Claude: Running context drift analysis...

# Context Drift Report

**Generated**: 2024-01-15 14:30:00
**Repository**: my-project

## Summary

| Category | Count |
|----------|-------|
| Context files scanned | 12 |
| Critical issues | 2 |
| Semantic mismatches | 3 |
| Review flags | 1 |
| Orphaned code files | 4 |

## Critical Issues

### .claude/skills/worktree/SKILL.md
- **Line 58**: References `git worktree add -b` but worktree command deprecated
- **Line 120**: Script `./scripts/cleanup.sh` does not exist

[...continues with full report...]
```

### Example 2: No drift found

```
User: /context-drift

Claude: Running context drift analysis...

# Context Drift Report

**Generated**: 2024-01-15 14:30:00
**Repository**: my-project

## Summary

| Category | Count |
|----------|-------|
| Context files scanned | 8 |
| Critical issues | 0 |
| Semantic mismatches | 0 |
| Review flags | 0 |
| Orphaned code files | 0 |

All context files are current. No drift detected.
```

### Example 3: Repository without .claude/ directory

```
User: /context-drift

Claude: No `.claude/` directory found in this repository.

To use context drift detection, create context files:
- `.claude/skills/` - For complex workflows with subcommands
- `.claude/commands/` - For simple prompt templates
- `.claude/agents/` - For specialized sub-agent definitions

Run `/skill-writing` or `/command-creator` to get started.
```

---

## Notes

- This skill is resource-intensive; run manually, not automatically
- Semantic analysis is heuristic-based and may need human judgment
- Orphan detection uses conservative thresholds to reduce noise
- For large repos, consider scoping to specific directories
- See REFERENCE.md for customizing detection patterns

---

## Evaluation Prompts

### Test 1: Activation - should trigger
```
User: /context-drift
Expected: Skill activates, scans .claude/ files, produces drift report
```

### Test 2: Activation - should trigger
```
User: Check if my claude context files are up to date
Expected: Skill activates, runs full analysis
```

### Test 3: Non-activation - should NOT trigger
```
User: How do I write good documentation?
Expected: Normal response about documentation practices, NOT drift scan
```

### Test 4: Non-activation - should NOT trigger
```
User: Update the README with the latest changes
Expected: Normal documentation update (like /update-docs), NOT drift audit
```

### Test 5: Edge case - no .claude directory
```
User: /context-drift
Context: Repository has no .claude/ folder
Expected: Helpful message explaining how to create context files
```

### Test 6: Edge case - all current
```
User: /context-drift
Context: All context files recently updated, all references valid
Expected: Report stating "No drift detected" with green summary
```

### Test 7: Edge case - broken reference
```
User: /context-drift
Context: A SKILL.md references a file that was deleted
Expected: Critical severity flag with exact line number and file path
```

### Test 8: Edge case - semantic mismatch
```
User: /context-drift
Context: Command documents "npm test" but package.json uses "bun test"
Expected: Semantic mismatch flagged with both documented and actual values
```
