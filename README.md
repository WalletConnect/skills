# WalletConnect Skills

Centralized repository for shared Claude Code configuration files used across WalletConnect projects.

## Quick Start

```bash
# Clone repository
git clone git@github.com:WalletConnect/skills.git
cd skills

# Install to your local .claude directory
./scripts/install.sh
```

## What's Inside

This repository contains:
- **Skills**: Custom slash commands that extend Claude's capabilities (7 skills including `/worktree`, Linear CLI, AWS limits review, operational readiness)
- **Commands**: Prompt templates and workflows for common development tasks (26 commands)
- **Agents**: Specialized subagents for code review, simplification, and infrastructure validation (3 agents)

Skills live at the repository root (`skills/`) to match the [official Anthropic skills structure](https://github.com/anthropics/skills) and support the [npx skills API](https://skills.sh) (`npx skills add <owner>/<skill>`). A symlink at `.claude/skills` maintains backwards compatibility with existing scripts.

## Prerequisites

- [Claude Code](https://docs.claude.ai/claude-code) installed and configured
- Git access to WalletConnect repositories

## Installation

### Install Files to Local .claude Directory

```bash
# Clone repository
git clone git@github.com:WalletConnect/skills.git
cd skills

# Install all skills and commands
./scripts/install.sh

# Or force overwrite existing files
./scripts/install.sh --force
```

### Verify Installation

```bash
ls ~/.claude/skills/
ls ~/.claude/commands/
```

## Available Skills

| Skill | Description | Usage |
|-------|-------------|-------|
| `agent-creator` | Guide for creating custom Claude Code subagents with custom prompts and tools | Use when creating/updating agents |
| `aws-limits` | Reviews infrastructure code for AWS service quota violations | Use when reviewing Terraform/CloudFormation/CDK/Pulumi |
| `command-creator` | Guide for creating custom slash commands with arguments and bash execution | Use when creating/updating commands |
| `linear-cli` | Manages Linear issues via CLI - view, start, create, update issues and PRs | `/linear` or when managing Linear issues |
| `operational-readiness` | Production readiness checklist for services - validates observability, CI/CD, security, infrastructure | `/operational-readiness` |
| `skill-writing` | Designs and writes high-quality Agent Skills with proper structure and metadata | Use when creating/improving Skills |
| `worktree` | Create and configure new git worktree with conventional commit branch naming | `/worktree <name>` |

### Skill Details

#### agent-creator
Guides you through creating custom Claude Code subagents as Markdown files with YAML frontmatter. Helps define agent names, descriptions, tool restrictions, permissions, and system prompts for specialized workflows.

**Features:**
- Agent file structure and frontmatter options
- Tool restriction patterns
- Permission modes and hooks
- Read-only vs read-write agent examples

#### aws-limits
Reviews infrastructure code for AWS service quota violations before they cause production issues. Checks against known hard and soft limits across Lambda, API Gateway, S3, DynamoDB, Step Functions, Load Balancing, and more.

**Features:**
- Scans Terraform, CloudFormation, CDK, Pulumi files
- Flags violations with severity levels
- Links to AWS documentation
- Suggests mitigations

#### command-creator
Guides you through creating custom slash commands as Markdown files with optional frontmatter. Commands can use arguments, execute bash, reference files, and define tool permissions.

**Features:**
- Basic command structure
- Frontmatter options (description, allowed-tools, model)
- Arguments and bash execution
- File references and namespacing

#### linear-cli
Manages Linear issues from the terminal - view current work, start issues, create branches, open PRs, and stay in flow. Integrates with GitHub CLI for PR creation.

**Features:**
- View and list issues
- Start issues (creates branch)
- Create PRs with prefilled data
- Configuration management

#### operational-readiness
Comprehensive operational readiness checklist for validating services before production launch. Analyzes codebase for CI/CD configs, infrastructure code, and security patterns, then interactively verifies items that can't be detected from code.

**Features:**
- Auto-detects tech stack (Rust, Node.js, Terraform, CDK, etc.)
- Scans for observability, CI/CD, security, and infrastructure patterns
- Interactive verification for non-detectable items
- Generates prioritized report with remediation guidance
- Includes detailed reference docs for all checklist items

**Categories Covered:**
- Observability (metrics, logging, tracing, alerting)
- CI/CD & Testing
- Infrastructure Primitives
- Security (OWASP Top 10, secrets management, RLS)
- 3rd Party & Service Dependencies
- Data Retention & Privacy (GDPR)
- Efficiency & Frugality

**Example:**
```bash
/operational-readiness
# Prompts for service classification → Analyzes codebase
# → Asks verification questions → Generates readiness report
```

#### skill-writing
Produces usable Skill packages optimized for discoverability, correctness, concision, and testability. Follows progressive disclosure patterns and includes validation.

**Features:**
- Requirements extraction
- Information architecture design
- Frontmatter validation
- Evaluation prompt generation

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

## Available Commands

Commands are prompt templates that help with common development workflows. They are simple markdown files in `.claude/commands/` that Claude can use.

| Command | Description |
|---------|-------------|
| `analyze-dependencies` | Analyze and audit project dependencies |
| `api-documenter` | Generate API documentation |
| `aws-limits` | Review infrastructure code for AWS service quota violations |
| `code-review` | Review code changes using parallel subagents with severity ranking |
| `commit-and-push` | Stage, commit, and push changes with proper messaging |
| `debug-issue` | Systematic debugging workflow |
| `dev-diary` | Create developer diary entries |
| `explore-module` | Explore and understand code modules |
| `fix` | Fix GitHub issues in new worktree and submit PR |
| `gather-tech-docs` | Gather tech stack documentation |
| `github-assign-team-topics` | Assign team topics to WalletConnect/reown-com repos |
| `performance-check` | Check and optimize performance |
| `post-init-onboarding` | Post-initialization onboarding tasks |
| `pre-deploy-check` | Pre-deployment checklist |
| `pre-review-check` | Pre-review quality checklist |
| `refactor-assistant` | Guided refactoring workflow |
| `respond` | Respond to PR review feedback |
| `review` | Review pull requests thoroughly |
| `security-audit` | Security audit workflow |
| `start-feature` | Start new feature development |
| `summarize_prs` | Analyze and summarize open PRs |
| `tdd` | Test-driven development workflow |
| `tech-debt-hunt` | Technical debt assessment |
| `understand-codebase` | Deep dive into codebase understanding |
| `update-docs` | Update project documentation |
| `visual-test` | Visual testing with Playwright |

## Syncing Updates

### Pull Latest Changes from Repository

```bash
cd skills
git pull
./scripts/sync.sh --pull
```

### Push Local Changes to Repository (Contributors)

If you've created or modified skills/commands locally and want to share them:

```bash
cd skills

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

## Available Agents

Agents are specialized subagents that can be invoked by Claude Code to handle specific types of tasks. They are defined as markdown files in `.claude/agents/`.

| Agent | Description | Usage |
|-------|-------------|-------|
| `aws-limits` | Reviews infrastructure code for AWS service quota violations | Automatically invoked for Terraform/CloudFormation/CDK/Pulumi files |
| `code-review` | Provides actionable feedback on code changes focusing on bugs and security | Used by code-review command for parallel review |
| `code-simplifier` | Simplifies and refines code for clarity and maintainability | Can be invoked when code needs simplification |

Agents can be invoked automatically by Claude Code based on their description, or explicitly via commands and skills.

## Contributing

For AI agents: See [AGENTS.md](AGENTS.md) for repository architecture, validation requirements, and maintenance guidelines.

### Adding a New Skill

1. Create skill directory:
   ```bash
   mkdir -p skills/<skill-name>
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
   git add skills/<skill-name>/
   git commit -m "feat: add <skill-name> skill"
   git push
   ```

### Adding a New Command

1. Create command file:
   ```bash
   touch .claude/commands/<command-name>.md
   ```

2. Add content (optional frontmatter):
   ```markdown
   ---
   description: Brief description of the command
   argument-hint: [optional arguments]
   ---

   # Command Title

   Instructions and workflow for Claude to follow...
   ```

3. Test locally:
   ```bash
   # Commands are automatically available once in ~/.claude/commands/
   ```

4. Commit and push:
   ```bash
   git add .claude/commands/<command-name>.md
   git commit -m "feat: add <command-name> command"
   git push
   ```

### Frontmatter Requirements

**Skills** (`skills/<name>/SKILL.md`):
```yaml
---
name: skill-name              # Required: Skill identifier
description: Brief description # Required: When Claude should invoke this
user-invocable: true          # Optional: If user can call directly (default: true)
---
```

**Commands** (`.claude/commands/<name>.md`):
```yaml
---
description: Brief description # Optional: Command description
argument-hint: [args]         # Optional: Hint for arguments
---
```

Note: Commands have much simpler frontmatter requirements than skills. Many commands work fine without any frontmatter.

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
Copies all skills and commands to your local `~/.claude/` directory.

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
skills/                      # Repository root
├── skills/                  # All team skills (primary location)
│   ├── agent-creator/
│   │   └── SKILL.md
│   ├── aws-limits/
│   │   ├── SKILL.md
│   │   └── REFERENCE.md
│   ├── command-creator/
│   │   └── SKILL.md
│   ├── linear-cli/
│   │   └── SKILL.md
│   ├── operational-readiness/
│   │   ├── SKILL.md
│   │   ├── assets/
│   │   ├── references/
│   │   └── scripts/
│   ├── skill-writing/
│   │   └── SKILL.md
│   └── worktree/
│       └── SKILL.md
├── .claude/
│   ├── skills -> ../skills  # Symlink for backwards compatibility
│   ├── commands/            # All team commands
│   │   ├── analyze-dependencies.md
│   │   ├── api-documenter.md
│   │   ├── aws-limits.md
│   │   ├── code-review.md
│   │   ├── commit-and-push.md
│   │   ├── debug-issue.md
│   │   ├── dev-diary.md
│   │   ├── explore-module.md
│   │   ├── fix.md
│   │   ├── gather-tech-docs.md
│   │   ├── github-assign-team-topics.md
│   │   ├── performance-check.md
│   │   ├── post-init-onboarding.md
│   │   ├── pre-deploy-check.md
│   │   ├── pre-review-check.md
│   │   ├── refactor-assistant.md
│   │   ├── respond.md
│   │   ├── review.md
│   │   ├── security-audit.md
│   │   ├── start-feature.md
│   │   ├── summarize_prs.md
│   │   ├── tdd.md
│   │   ├── tech-debt-hunt.md
│   │   ├── understand-codebase.md
│   │   ├── update-docs.md
│   │   └── visual-test.md    # (26 total)
│   └── agents/              # Custom agents
│       ├── aws-limits.md
│       ├── code-review.md
│       └── code-simplifier.md
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
   ls ~/.claude/commands/
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
   cp -r ~/.claude/commands ~/claude-backup/commands
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
- Commands are flat markdown files in `commands/` directory
- Validate before committing (`./scripts/validate.sh`)
- Document all skills/commands clearly
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
