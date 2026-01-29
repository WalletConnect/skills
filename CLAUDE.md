# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Centralized repo for shared Claude Code configuration (skills, commands, agents) used across WalletConnect projects. Files here mirror `~/.claude/` structure for syncing to local machines.

## Commands

```bash
# Validate all files (frontmatter, structure)
./scripts/validate.sh

# Install to local ~/.claude/
./scripts/install.sh
./scripts/install.sh --force  # overwrite existing

# Sync between repo and local
./scripts/sync.sh             # interactive bi-directional
./scripts/sync.sh --pull      # repo → local
./scripts/sync.sh --push      # local → repo
./scripts/sync.sh --dry-run   # preview only
```

npm equivalents: `npm run validate`, `npm run install-files`, `npm run sync`

## Architecture

```
.claude/
├── skills/           # Full skills with SKILL.md + optional references
│   └── <name>/
│       ├── SKILL.md           # Required: frontmatter + instructions
│       ├── REFERENCE.md       # Optional: API docs, schemas
│       ├── WORKFLOWS.md       # Optional: multi-step procedures
│       └── references/        # Optional: supporting files
├── commands/         # Simple prompt templates (flat .md files)
└── agents/           # Subagent definitions (.md files with frontmatter)
```

### Skills vs Commands vs Agents

- **Skills** (`skills/<name>/SKILL.md`): Complex, multi-file capabilities with structured workflows. Require `name` and `description` frontmatter.
- **Commands** (`commands/<name>.md`): Simple prompt templates. Frontmatter optional.
- **Agents** (`agents/<name>.md`): Subagent definitions with tool restrictions and custom prompts. Require `name` and `description` frontmatter; support `tools`, `model`, `permissionMode`.

### Frontmatter Requirements

Skills and agents require YAML frontmatter:
```yaml
---
name: lowercase-hyphen-only
description: What it does. When to use it.
---
```

Agents additionally support:
- `tools`: Comma-separated tool list (default: all)
- `model`: haiku, sonnet, opus, inherit (default: sonnet)
- `permissionMode`: default, acceptEdits, dontAsk, bypassPermissions, plan

## Validation

The `validate.sh` script checks:
- Frontmatter exists and is valid YAML
- Required fields present (`name`, `description`)
- `model` field valid if present (haiku/sonnet/opus)
- Skill directory names match skill names

Always run `./scripts/validate.sh` before committing changes to `.claude/`.
