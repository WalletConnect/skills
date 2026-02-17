---
name: context-audit
description: |
  Audits AI context files (CLAUDE.md, .cursorrules, SKILL.md, etc.) against the actual codebase. Detects stale references, vague instructions, missing coverage, and structural issues. Use when auditing AI documentation, checking context alignment, improving agent instructions, or before onboarding.

  Triggers: "context audit", "check ai context", "audit context files", "context quality", "review CLAUDE.md", "improve agent docs", "ai docs quality", "context drift"
---

# Context Audit

Audit AI context files in a repository for accuracy, coverage, and clarity. Produces a scored quality report with actionable fixes.

**User Guidance:** $ARGUMENTS

## When to Use

- Auditing AI documentation freshness or correctness
- Checking if context files match the actual codebase
- Before onboarding new team members to AI-assisted development
- After major refactors that may have invalidated context docs
- Periodic hygiene checks on agent instructions

## When Not to Use

- Writing new context files from scratch (that's a creative task, not an audit)
- Reviewing code changes (use code-review instead)
- General documentation review (this is specific to AI agent context)

## Supported Context Files

| File Pattern | Tool |
|--------------|------|
| `CLAUDE.md`, `AGENTS.md` (root + nested) | Claude Code |
| `.cursorrules`, `.cursor/rules/*.mdc` | Cursor |
| `.github/copilot-instructions.md` | GitHub Copilot |
| `.windsurfrules` | Windsurf |
| `.claude/skills/*/SKILL.md` | Claude Code Skills |
| `.agents/skills/*/SKILL.md` | Agent Skills (generic) |
| `.claude/commands/*.md` | Claude Code Commands |
| `.agents/context/*.md` | Agent Context docs |

## Workflow

### 1. Discover Context Files

Scan the repository for all AI context files listed above. Report which files were found and which tools they serve.

If the user provides `$ARGUMENTS` referencing specific files (e.g., "focus on CLAUDE.md only"), limit discovery and analysis to those files.

If **no context files are found**, skip analysis and instead:
- Report that no AI context exists
- Detect the repo's tech stack from package files, language files, and directory structure
- Suggest which context files to create and what they should cover
- Offer to generate a starter `CLAUDE.md` / `AGENTS.md`

### 2. Analyze with Parallel Subagents

Launch **3 parallel Task subagents** (`subagent_type: general-purpose`), each focused on a different dimension. Each subagent must produce **per-file scores** as well as an **overall dimension score**.

#### Subagent 1: Reference Validator
- Extract all file paths, directory references, function/class/method names, CLI commands, and package names mentioned in context files
- Verify each reference exists in the codebase using Glob and Grep
- Flag references that don't resolve as **stale references**
- Check that code examples in context files match actual code patterns
- Score each file individually, then compute overall: **Accuracy (0-100)**

#### Subagent 2: Coverage Analyzer
- Detect the repo's actual tech stack from: package managers (`package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`), frameworks, CI/CD configs, infrastructure files
- Identify key architectural patterns by scanning source code structure
- Compare what the context files document vs what actually exists
- Flag undocumented areas using the coverage checklist in [CHECKLISTS.md](CHECKLISTS.md)
- Score each file individually, then compute overall: **Coverage (0-100)**

#### Subagent 3: Quality Assessor
- Evaluate each context file for clarity, specificity, and actionability
- Flag vague instructions (e.g., "handle errors properly" without specifying how)
- Check for inconsistent terminology across files
- Assess length appropriateness (flag files under 20 lines as too sparse, over 500 lines as potentially bloated)
- Check for presence of examples and anti-patterns
- Verify instructions don't contradict each other across files
- Score each file individually, then compute overall: **Clarity (0-100)**

Provide each subagent with:
- The full content of all discovered context files
- The repo's directory structure (top 3 levels)
- The detailed criteria from [CHECKLISTS.md](CHECKLISTS.md)

### 3. Score and Rank

Compute scores from subagent results. Use per-file scores to populate the "Scores by File" table, and overall dimension scores for the "Scores by Dimension" table:

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Accuracy | 40% | Do references match reality? |
| Coverage | 35% | Are key areas documented? |
| Clarity | 25% | Are instructions specific and actionable? |

**Overall = (Accuracy x 0.4) + (Coverage x 0.35) + (Clarity x 0.25)**

### 4. Generate Report

Consolidate findings into the output format below. Rank all issues by severity.

### 5. Offer Remediation

After presenting the report, ask the user:
> "Would you like me to fix these issues? I can update the context files to resolve stale references, add missing coverage, and improve clarity."

If yes, apply fixes file-by-file, showing changes before writing.

## Severity Levels

- **Critical**: Stale references that actively mislead the agent (wrong file paths, deleted functions referenced as current)
- **High**: Missing coverage of major architectural components, contradictory instructions
- **Medium**: Vague instructions, missing examples, minor stale references
- **Low**: Style improvements, terminology consistency, length optimization

## Output Format

```markdown
# Context Audit Report

**Repository:** [name]
**Files Scanned:** [count]
**Overall Score:** [X/100] [grade: A/B/C/D/F]

## Scores by File

| File | Accuracy | Coverage | Clarity | Overall | Issues |
|------|----------|----------|---------|---------|--------|
| CLAUDE.md | 85 | 70 | 90 | 81 | 3 |
| ... | ... | ... | ... | ... | ... |

## Scores by Dimension

| Dimension | Score | Summary |
|-----------|-------|---------|
| Accuracy | X/100 | [one-line summary] |
| Coverage | X/100 | [one-line summary] |
| Clarity | X/100 | [one-line summary] |

## Critical Issues
- [file:line] Description — why it misleads agents

## High Priority
- [file:line] Description

## Medium Priority
- [file:line] Description

## Low Priority / Suggestions
- [file:line] Description

## Missing Coverage
Key areas of the codebase not documented in any context file:
- [area]: [what should be documented]

## Remediation Summary
[Actionable fixes grouped by file, ready to apply]
```

## Grading Scale

| Score | Grade | Meaning |
|-------|-------|---------|
| 90-100 | A | Excellent — context is accurate, comprehensive, and clear |
| 80-89 | B | Good — minor gaps or stale references |
| 70-79 | C | Adequate — notable gaps in coverage or accuracy |
| 60-69 | D | Poor — significant issues that mislead agents |
| <60 | F | Failing — context is largely stale, missing, or vague |
