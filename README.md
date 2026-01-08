# WalletConnect Claude Files

Centralized repository for shared Claude Code skills and subagents used across WalletConnect projects.

## Quick Start

```bash
# Clone repository
git clone git@github.com:WalletConnect/claude-files.git
cd claude-files

# Install to your local .claude directory
./scripts/install.sh
```

## What's Inside

This repository contains:
- **Skills**: Custom commands that extend Claude's capabilities
- **Agents**: Specialized subagents for specific tasks

All files are organized to mirror your local `~/.claude/` directory structure for easy syncing.

## Prerequisites

- [Claude Code](https://docs.claude.ai/claude-code) installed and configured
- Git access to WalletConnect repositories

## Installation

### Install Files to Local .claude Directory

```bash
# Clone repository
git clone git@github.com:WalletConnect/claude-files.git
cd claude-files

# Install all skills and agents
./scripts/install.sh

# Or force overwrite existing files
./scripts/install.sh --force
```

### Verify Installation

```bash
ls ~/.claude/skills/
ls ~/.claude/agents/
```

## Available Skills

| Skill | Description | Usage |
|-------|-------------|-------|
| `worktree` | Create and configure new git worktree with conventional commit branch naming | `/worktree <name>` |

### Skill Details

#### worktree
Creates a new git worktree in a sibling directory with proper branch naming following conventional commit conventions. Useful when you need to work on multiple branches simultaneously.

**Features:**
- Interactive commit type selection (feat, fix, chore, etc.)
- Automatic branch naming: `{type}/{name}`
- Sibling directory creation: `../{repo}-{type}-{name}`
- Error handling for existing worktrees

**Example:**
```bash
/worktree alerts
# Prompts for commit type → Creates feat/alerts branch
# Creates worktree at ../repo-name-feat-alerts
```

## Available Agents

| Agent | Description | Model |
|-------|-------------|-------|
| `github-comment-deleter` | Delete comments from GitHub PRs/issues (use only when explicitly requested) | haiku |

### Agent Details

#### github-comment-deleter
Safely deletes comments from GitHub pull requests and issues using the GitHub CLI. Only invoked when user explicitly requests comment deletion.

**Features:**
- Handles both regular PR comments and inline review comments
- Shows deletion summary before proceeding
- Graceful error handling
- Progress reporting for large comment counts

**Use Cases:**
- Cleaning up PR comment threads
- Removing outdated review comments
- Bulk comment management

## Syncing Updates

### Pull Latest Changes from Repository

```bash
cd claude-files
git pull
./scripts/sync.sh --pull
```

### Push Local Changes to Repository (Contributors)

If you've created or modified skills/agents locally and want to share them:

```bash
cd claude-files

# Sync from local to repository
./scripts/sync.sh --push

# Review changes
git status
git diff

# Commit using conventional format
git add .claude/
git commit -m "feat: add new skill for X"

# Push to remote
git push
```

### Bi-directional Sync

```bash
# Interactive sync (shows changes and asks for confirmation)
./scripts/sync.sh

# Dry run (preview changes without applying)
./scripts/sync.sh --dry-run
```

## Contributing

### Adding a New Skill

1. Create skill directory:
   ```bash
   mkdir -p .claude/skills/<skill-name>
   ```

2. Create `SKILL.md` with frontmatter:
   ```markdown
   ---
   name: skill-name
   description: Brief description for Claude to understand when to invoke
   user-invocable: true
   ---

   # Skill Title

   Detailed instructions for Claude...
   ```

3. Validate:
   ```bash
   ./scripts/validate.sh
   ```

4. Commit and push:
   ```bash
   git add .claude/skills/<skill-name>/
   git commit -m "feat: add <skill-name> skill"
   git push
   ```

### Adding a New Agent

1. Create agent file:
   ```bash
   touch .claude/agents/<agent-name>.md
   ```

2. Add frontmatter and instructions:
   ```markdown
   ---
   name: agent-name
   description: When to use this agent with examples
   model: haiku
   ---

   Agent instructions and behavior...
   ```

3. Validate:
   ```bash
   ./scripts/validate.sh
   ```

4. Commit and push:
   ```bash
   git add .claude/agents/<agent-name>.md
   git commit -m "feat: add <agent-name> agent"
   git push
   ```

### Frontmatter Requirements

**Skills** (`.claude/skills/<name>/SKILL.md`):
```yaml
---
name: skill-name              # Required: Skill identifier
description: Brief description # Required: When Claude should invoke this
user-invocable: true          # Optional: If user can call directly (default: true)
---
```

**Agents** (`.claude/agents/<name>.md`):
```yaml
---
name: agent-name              # Required: Agent identifier
description: When to use      # Required: When to use with examples
model: haiku                  # Optional: haiku|sonnet|opus (default: sonnet)
---
```

### Commit Conventions

Follow conventional commit format:
- `feat: add new feature`
- `fix: fix bug`
- `docs: update documentation`
- `chore: maintenance tasks`
- `refactor: code refactoring`
- `test: add or update tests`

## Scripts Reference

### validate.sh
Validates all markdown files have correct frontmatter and structure.

```bash
./scripts/validate.sh
```

Checks:
- Frontmatter exists and is valid YAML
- Required fields present (name, description)
- Model field valid (if present)
- Skill directory names match skill names
- File structure follows conventions

### install.sh
Copies all skills and agents to your local `~/.claude/` directory.

```bash
# Interactive installation
./scripts/install.sh

# Force overwrite existing files
./scripts/install.sh --force

# Show help
./scripts/install.sh --help
```

Features:
- Validates files before installation
- Prompts before overwriting (unless --force)
- Shows installation summary
- Creates directories if needed

### sync.sh
Syncs files between repository and local .claude directory.

```bash
# Interactive bi-directional sync
./scripts/sync.sh

# Pull only (repo → local)
./scripts/sync.sh --pull

# Push only (local → repo)
./scripts/sync.sh --push

# Preview changes
./scripts/sync.sh --dry-run

# Show help
./scripts/sync.sh --help
```

Features:
- Uses rsync for efficient syncing
- Shows detailed change summary
- Validates after push operations
- Preserves file permissions

## Directory Structure

```
claude-files/
├── .claude/
│   ├── skills/              # All team skills
│   │   └── worktree/
│   │       └── SKILL.md
│   └── agents/              # All team agents
│       └── github-comment-deleter.md
├── scripts/
│   ├── install.sh           # Install files to local .claude/
│   ├── sync.sh              # Sync between local and repo
│   └── validate.sh          # Validate file formats
├── .gitignore
├── README.md
└── package.json
```

## Troubleshooting

### Files Not Appearing in Claude

1. Verify installation:
   ```bash
   ls ~/.claude/skills/
   ls ~/.claude/agents/
   ```

2. Check frontmatter validation:
   ```bash
   ./scripts/validate.sh
   ```

3. Restart Claude Code if needed

### Validation Errors

Run validation to see specific issues:
```bash
./scripts/validate.sh
```

Common issues:
- Missing frontmatter (must start with `---`)
- Invalid YAML syntax
- Required fields missing (name, description)
- Invalid model value (must be haiku, sonnet, or opus)

### Sync Conflicts

If you have conflicting changes:

1. Preview differences:
   ```bash
   ./scripts/sync.sh --dry-run
   ```

2. Backup local changes:
   ```bash
   cp -r ~/.claude/skills ~/claude-backup/skills
   cp -r ~/.claude/agents ~/claude-backup/agents
   ```

3. Resolve conflicts manually and re-run sync

### Permission Errors

If you get permission errors during installation:
```bash
# Check .claude directory permissions
ls -la ~/.claude/

# Ensure scripts are executable
chmod +x scripts/*.sh
```

## Team Conventions

- Use conventional commit format for all commits
- Skills go in their own subdirectories with `SKILL.md`
- Agents are flat files in `agents/` directory
- Validate before committing (`./scripts/validate.sh`)
- Document all skills/agents clearly
- Test locally before pushing

## npm Scripts

You can also use npm scripts for convenience:

```bash
npm run validate        # Run validation
npm run install-files   # Install to local .claude/
npm run sync            # Sync files
```

## Support

Questions or issues? Open an issue in this repository.

## License

UNLICENSED - For WalletConnect internal use only.
