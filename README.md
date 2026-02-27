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
- **Skills**: Custom slash commands that extend Claude's capabilities (e.g., `/worktree`)
- **Commands**: Prompt templates and workflows for common development tasks

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
| `operational-readiness` | Production readiness checklist for services - validates observability, CI/CD, security, infrastructure | `/operational-readiness` |
| `security-audit-owasp-top-10` | Comprehensive security audit against OWASP Top 10 2025 framework | `/security-audit-owasp-top-10` |
| `worktree` | Create and configure new git worktree with conventional commit branch naming | `/worktree <name>` |
| `code-review` | Review code changes for bugs, security issues, and structural problems | `/code-review [guidance]` |
| `code-simplifier` | Simplify and refine code for clarity while preserving functionality | `/code-simplifier` |
| `aws-limits` | Review infrastructure code for AWS service quota violations | `/aws-limits` |
| `license-compliance` | Scan project dependencies for license compliance across 9 ecosystems. Supports org-wide sweeps | `/license-compliance [--repo org/repo]` |
| `repo-setup` | Set up AI agent docs (AGENTS.md), CLAUDE.md symlink, and auto-review workflow | `/repo-setup` |

### Skill Details

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

#### security-audit-owasp-top-10
Performs systematic security audit of codebases against the OWASP Top 10 2025 framework. Uses semantic code analysis (not just pattern matching) to detect vulnerabilities with severity-rated findings and remediation guidance.

**Features:**
- Auto-detects project type and applies relevance filtering
- Covers all 10 OWASP categories with context-aware checks
- Semantic analysis with false positive filtering
- Severity + confidence ratings for each finding
- Evidence-backed findings with file locations and code snippets
- Specific remediation guidance per vulnerability
- Supports partial audits (e.g., "audit A01 and A03 only")

**Categories Covered:**
- A01: Broken Access Control
- A02: Security Misconfiguration
- A03: Supply Chain & Component Failures
- A04: Cryptographic Failures
- A05: Injection (SQL, XSS, Command)
- A06: Insecure Design
- A07: Authentication & Session Failures
- A08: Data & Software Integrity Failures
- A09: Security Logging & Monitoring Failures
- A10: Exceptional Condition & Error Handling

**Example:**
```bash
/security-audit-owasp-top-10
# Performs full OWASP Top 10 audit → Generates severity-rated report

/security-audit-owasp-top-10 audit A01 and A05 only
# Audits only access control and injection categories
```

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

#### code-review
Reviews code changes using parallel subagents to analyze bugs/logic, security/auth, and patterns/structure. Automatically detects AWS infrastructure files and runs service quota checks.

**Features:**
- Reviews uncommitted changes by default, or last commit, or PR diffs
- Parallel analysis by 3-4 specialized reviewers
- Severity-ranked output (Critical > High > Medium > Low)
- AWS limits review for infrastructure code

**Example:**
```bash
/code-review                    # Review uncommitted changes
/code-review focus on auth      # Review with specific guidance
/code-review #123               # Review a PR
```

#### code-simplifier
Analyzes recently modified code and applies refinements for clarity, consistency, and maintainability while preserving exact functionality.

**Features:**
- Preserves all original behavior
- Applies project-specific conventions
- Early returns, dead code removal, constant extraction
- Balance between simplicity and clarity

#### aws-limits
Reviews Terraform, CloudFormation, CDK, or Pulumi code for AWS service limit violations that could cause production issues.

**Features:**
- Checks against known hard and soft limits
- Severity-ranked findings with AWS documentation links
- Mitigation suggestions for each violation

#### repo-setup
Sets up a repository with standardized AI agent documentation and automated PR review infrastructure following the WalletConnect checklist.

**Features:**
- Detects existing AGENTS.md / CLAUDE.md state and skips completed steps
- Converts existing CLAUDE.md to agent-agnostic AGENTS.md
- Runs Claude Code `/init` in a subagent for repos without any agent docs
- Creates backward-compatible CLAUDE.md → AGENTS.md symlink
- Sets up Claude auto-review GitHub Action workflow
- Auto-detects default branch for workflow configuration

**Example:**
```bash
/repo-setup                  # Full setup
/repo-setup just docs        # Only AGENTS.md + symlink
/repo-setup just workflow    # Only auto-review workflow
```

## Available Commands

Commands are prompt templates that help with common development workflows. They are simple markdown files in `.claude/commands/` that Claude can use.

| Command | Description |
|---------|-------------|
| `analyze-dependencies` | Analyze and audit project dependencies |
| `api-documenter` | Generate API documentation |
| `commit-and-push` | Stage, commit, and push changes with proper messaging |
| `debug-issue` | Systematic debugging workflow |
| `dev-diary` | Create developer diary entries |
| `explore-module` | Explore and understand code modules |
| `fix` | Fix GitHub issues in new worktree and submit PR |
| `gather-tech-docs` | Gather tech stack documentation |
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

## Contributing

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
│   ├── worktree/
│   │   └── SKILL.md
│   ├── code-review/
│   │   └── SKILL.md
│   ├── code-simplifier/
│   │   └── SKILL.md
│   ├── aws-limits/
│   │   ├── SKILL.md
│   │   └── REFERENCE.md
│   ├── repo-setup/
│   │   ├── SKILL.md
│   │   └── REFERENCE.md
│   ├── security-audit-owasp-top-10/
│   │   ├── SKILL.md
│   │   ├── CATEGORIES.md
│   │   └── EVALUATIONS.md
│   └── ...
├── .claude/
│   ├── skills -> ../skills  # Symlink for backwards compatibility
│   └── commands/            # All team commands
│       ├── pre-review-check.md
│       ├── commit-and-push.md
│       ├── respond.md
│       └── ...
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
