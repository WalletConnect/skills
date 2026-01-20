# Context Drift Reference

Detailed patterns, heuristics, and thresholds for drift detection.

---

## Context File Types

### Skills (`.claude/skills/*/SKILL.md`)

**Frontmatter fields**:
```yaml
---
name: skill-name           # Required
description: ...           # Required
user-invocable: true       # Optional, defaults to true
---
```

**Common references to check**:
- File paths in code blocks
- Bash commands with `!` prefix
- Tool names (Read, Write, Bash, Grep, etc.)
- Referenced `REFERENCE.md`, `WORKFLOWS.md` files

### Commands (`.claude/commands/*.md`)

**Frontmatter fields**:
```yaml
---
description: ...           # Optional
argument-hint: <args>      # Optional
---
```

**Common references to check**:
- Variable substitutions (`${VAR}`, `$1`, `$ARGUMENTS`)
- Bash scripts in code blocks
- File path patterns
- CLI tool invocations (`npm`, `git`, `gh`, etc.)

### Agents (`.claude/agents/*.md`)

**Frontmatter fields**:
```yaml
---
name: agent-name           # Required
description: ...           # Required
tools: Tool1, Tool2        # Required (comma-separated)
model: sonnet|opus|haiku   # Optional
permissionMode: ...        # Optional
---
```

**Common references to check**:
- Tool list validity
- Model name validity
- Permission mode validity

---

## Reference Extraction Patterns

### File Paths

Extract paths from these patterns:

| Pattern | Example | Regex |
|---------|---------|-------|
| Code block paths | `` `src/utils.ts` `` | `` `([^`]+\.(ts|js|py|go|rs|md))` `` |
| At-mentions | `@src/utils.ts` | `@([\w/./-]+\.\w+)` |
| Quoted paths | `"src/utils.ts"` | `"([\w/./-]+\.\w+)"` |
| In bash commands | `cat src/file.ts` | `(cat\|head\|tail\|read) ([\w/./-]+)` |

### Bash Commands

Extract and validate these command types:

| Type | Pattern | Validation |
|------|---------|------------|
| Script execution | `./scripts/*.sh` | File exists + executable |
| npm/bun/pnpm | `npm run X` | Script exists in package.json |
| Git commands | `git worktree add` | Valid git subcommand |
| CLI tools | `gh pr create` | Tool installed (optional) |

### Tool References

Valid Claude Code tools to check against:

```
Read, Write, Edit, Bash, Glob, Grep, Task, TodoWrite,
WebFetch, WebSearch, AskUserQuestion, NotebookEdit
```

MCP tools follow pattern: `mcp__server__tool_name`

---

## Detection Heuristics

### Broken Reference Detection

**Critical severity** (always flag):
- Referenced file does not exist
- Referenced script not found
- Directory path invalid

**High severity** (likely broken):
- Referenced npm script not in package.json
- Tool name not in valid tool list
- MCP tool format invalid

**Validation commands**:
```bash
# Check file exists
test -f "$path" && echo "exists" || echo "MISSING"

# Check script exists
test -x "$script" && echo "executable" || echo "NOT EXECUTABLE"

# Check npm script
jq -e ".scripts[\"$script_name\"]" package.json >/dev/null 2>&1
```

### Semantic Mismatch Detection

**Workflow step count**:
1. Count numbered steps in context file (regex: `^\d+\.\s`)
2. Compare to actual implementation steps
3. Flag if difference > 1 step

**Parameter mismatch**:
1. Extract documented parameters from context
2. Find actual function/command signature
3. Flag if count differs or names don't match

**Tool usage claims**:
1. Extract "uses X tool" claims from context
2. Search codebase for actual tool usage
3. Flag if claimed tool not found in referenced code

**Command substitution**:
1. Extract package manager commands (`npm`, `yarn`, `pnpm`, `bun`)
2. Check actual package.json for which is used
3. Flag if documented != actual

### Staleness Detection

**Thresholds**:

| Signal | Threshold | Severity |
|--------|-----------|----------|
| Context age | > 90 days unchanged | Low |
| Code commits since context | > 10 commits | Medium |
| Significant code changes | > 50 lines changed | Medium |

**Git commands for staleness**:
```bash
# Last context file modification
git log -1 --format="%ci" -- .claude/skills/foo/SKILL.md

# Commits to related code since context update
git log --since="2024-01-01" --oneline -- src/related/

# Lines changed in related code
git diff --stat $(git log -1 --format="%H" -- .claude/skills/foo/SKILL.md) -- src/
```

---

## Orphan Detection

### Significance Filters

Code is "significant" and needs documentation if ANY of:

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| File size | > 200 lines | Complex enough to document |
| Export count | > 5 exports | Public API surface |
| Entry point | `index.ts`, `main.ts` | Module boundary |
| Handler pattern | `*Handler.ts`, `*Controller.ts` | API surface |
| Core naming | `core/*.ts`, `engine/*.ts` | Business logic |

### Exclusion Filters

Skip these from orphan detection:

| Pattern | Reason |
|---------|--------|
| `*.test.ts`, `*.spec.ts` | Test files |
| `*.d.ts` | Type definitions |
| `node_modules/**` | Dependencies |
| `dist/**`, `build/**` | Build output |
| `.git/**` | Git internals |
| `*.config.ts` | Config files |
| `*.generated.ts` | Generated code |

### Detection Algorithm

```
1. referenced_paths = extract_all_paths(context_files)
2. all_code_files = glob("**/*.{ts,js,py,go,rs}")
3. orphans = all_code_files - referenced_paths
4. significant_orphans = filter(orphans, is_significant)
5. report(significant_orphans)
```

---

## Severity Classification Matrix

| Issue Type | Severity | Action |
|------------|----------|--------|
| File not found | Critical | Must fix before merge |
| Script missing | Critical | Must fix before merge |
| Invalid tool name | High | Should fix soon |
| Workflow step mismatch | High | Review and update |
| Parameter mismatch | High | Review and update |
| Command substitution | Medium | Update when convenient |
| Stale context (90+ days) | Low | Review for relevance |
| Orphaned significant code | Advisory | Consider documenting |

---

## Report Generation

### Section Order

1. **Summary table** - Quick overview
2. **Critical issues** - Broken references (must fix)
3. **Semantic mismatches** - Behavior drift (should fix)
4. **Review flags** - Potential issues (investigate)
5. **Orphaned code** - Missing documentation (consider)
6. **Recommendations** - Prioritized actions

### Formatting Guidelines

- Use tables for structured data
- Include line numbers for issues
- Show both "documented" and "actual" values for mismatches
- Group issues by context file
- Sort by severity within groups
