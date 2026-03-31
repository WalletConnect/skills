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
- **Skills**: Custom slash commands that extend Claude's capabilities (17 skills including `/worktree`, Linear CLI, AWS limits review, operational readiness, security auditing, supply-chain security, terraform plan review, and more)
- **Commands**: Prompt templates and workflows for common development tasks (25 commands)

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
| `code-review` | Review code changes for bugs, security issues, and structural problems | `/code-review [guidance]` |
| `code-simplifier` | Simplify and refine code for clarity while preserving functionality | `/code-simplifier` |
| `command-creator` | Guide for creating custom slash commands with arguments and bash execution | Use when creating/updating commands |
| `context-audit` | Audit AI context files for accuracy, coverage, and clarity against the actual codebase | `/context-audit` |
| `deepnote-notebook` | Edit Deepnote .ipynb notebooks correctly by syncing the deepnote_source metadata field | Use when editing Deepnote notebooks |
| `github-dependabot-report` | Generates Dependabot security alerts report for WalletConnect GitHub orgs, grouped by team | `/github-dependabot-report` |
| `hubspot-security-queue` | Summarizes HubSpot security ticket pipeline — queue status, unassigned tickets, AI triage | `/hubspot-security-queue` |
| `license-compliance` | Scan project dependencies for license compliance across 9 ecosystems. Supports org-wide sweeps | `/license-compliance [--repo org/repo]` |
| `linear-cli` | Manages Linear issues via CLI - view, start, create, update issues and PRs | `/linear` or when managing Linear issues |
| `operational-readiness` | Production readiness checklist for services - validates observability, CI/CD, security, infrastructure | `/operational-readiness` |
| `repo-ai-setup` | Set up AI agent docs (AGENTS.md), CLAUDE.md symlink, and auto-review workflow | `/repo-ai-setup` |
| `security-audit-owasp-top-10` | Comprehensive security audit against OWASP Top 10 2025 framework | `/security-audit-owasp-top-10` |
| `skill-writing` | Designs and writes high-quality Agent Skills with proper structure and metadata | Use when creating/improving Skills |
| `supply-chain-security` | Detects supply-chain attack patterns — invisible Unicode (Glassworm), malicious install hooks, eval decoders, lockfile anomalies | `/supply-chain-security` |
| `terraform-plan-review` | Analyze Terraform plan output — resource counts, alignment check, risk assessment, recommendations | `/terraform-plan-review [plan-file]` |
| `walletconnect-pay` | Guide wallet developers through WalletConnect Pay SDK integration (Kotlin, Swift, React Native, Flutter) | `/walletconnect-pay` |
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

#### command-creator
Guides you through creating custom slash commands as Markdown files with optional frontmatter. Commands can use arguments, execute bash, reference files, and define tool permissions.

**Features:**
- Basic command structure
- Frontmatter options (description, allowed-tools, model)
- Arguments and bash execution
- File references and namespacing

#### deepnote-notebook
Ensures edits to Deepnote-exported `.ipynb` notebooks are visible when re-imported into Deepnote. Deepnote stores a duplicate of cell content in `metadata.deepnote_source` which must be kept in sync with the standard `source` field.

**Features:**
- Automatic `deepnote_source` sync after `NotebookEdit` calls
- SQL cell handling (raw SQL in `deepnote_source` vs Python wrapper in `source`)
- New SQL cell metadata setup (`deepnote_cell_type`, `sql_integration_id`, `deepnote_variable_name`)
- Verification step to catch stale content

**Example:**
```bash
/deepnote-notebook
# "Update the SQL query in cell 5 of analytics.ipynb"
# → Edits source, syncs deepnote_source, verifies no stale content
```

#### github-dependabot-report
Generates a Dependabot security alerts report for walletconnect, reown-com, and walletconnectfoundation GitHub orgs. Groups alerts by team ownership (GitHub topics). Useful for reviewing security posture, preparing for security reviews, or tracking vulnerability remediation.

**Features:**
- Scans multiple GitHub organizations
- Groups vulnerabilities by team/topic ownership
- Severity-ranked findings
- Tracks remediation status

#### hubspot-security-queue
Summarizes the HubSpot security ticket pipeline queue. Shows total tickets, breakdown by stage, unassigned tickets needing attention, and AI triage status from the `security-pipeline-triage-worker`.

**Features:**
- Pipeline stage breakdown with ticket counts
- Unassigned ticket identification
- AI triage coverage summary (in-scope, out-of-scope, needs review, not triaged)
- Owner name and stage name resolution

**Example:**
```bash
/hubspot-security-queue
# Generates report → Summarizes queue status → Offers Slack delivery
```

#### license-compliance
Scans project dependencies for license compliance across 9 ecosystems. Classifies licenses as permissive, weak copyleft, or restrictive. Supports monorepos, remote GitHub repos, and org-wide scanning with tracker-based resume.

**Ecosystems Supported:**
- JS/TS (pnpm/npm/yarn)
- Rust (cargo)
- Python (pip/poetry/uv/pipenv)
- Swift (SPM)
- Kotlin (Gradle)
- Dart (pub)
- Go (modules)
- C# (NuGet)
- Solidity (Foundry)

**Example:**
```bash
/license-compliance                        # Scan current project
/license-compliance --repo org/repo        # Scan remote repo
```

#### context-audit
Audits AI context files (CLAUDE.md, .cursorrules, SKILL.md, etc.) against the actual codebase. Detects stale references, vague instructions, missing coverage, and structural issues.

**Features:**
- Discovers all AI context files across tools (Claude Code, Cursor, Copilot, Windsurf)
- Parallel analysis with 3 specialized subagents (reference validity, coverage, clarity)
- Scored quality report (Accuracy, Coverage, Clarity → Overall grade A-F)
- Severity-ranked findings with actionable remediation
- Handles repos with zero context files (suggests what to create)

**Example:**
```bash
/context-audit                          # Full audit of all context files
/context-audit focus on CLAUDE.md only  # Audit specific file
```

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

#### repo-ai-setup
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
/repo-ai-setup                  # Full setup
/repo-ai-setup just docs        # Only AGENTS.md + symlink
/repo-ai-setup just workflow    # Only auto-review workflow
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

#### skill-writing
Produces usable Skill packages optimized for discoverability, correctness, concision, and testability. Follows progressive disclosure patterns and includes validation.

**Features:**
- Requirements extraction
- Information architecture design
- Frontmatter validation
- Evaluation prompt generation

#### supply-chain-security
Detects supply-chain attack patterns in code changes, informed by the Glassworm campaign (March 2026) which compromised 151+ GitHub repositories using invisible Unicode payloads.

**Detection Capabilities:**
- Invisible Unicode obfuscation (PUA variation selectors, zero-width characters)
- Glassworm decoder pattern (`eval` + `Buffer.from` + `codePointAt` with hex ranges)
- Malicious `preinstall`/`postinstall`/`preuninstall` hooks in `package.json`
- Lockfile anomalies (changes without corresponding `package.json` updates)
- Byte-count cross-checks for hidden content
- PR review red flags (force-pushed commits, AI-generated cover changes)

**Includes:**
- Detection commands (hex dump, zero-width grep, byte-count anomaly checks)
- Emergency response protocol for compromised machines

**Example:**
```bash
/supply-chain-security
# "Check this PR for supply-chain attack indicators"
# → Scans for invisible Unicode, malicious hooks, eval decoders, lockfile anomalies
```

#### terraform-plan-review
Analyzes Terraform plan output with the rigor of a staff DevOps engineer. Compares planned changes against code diff, surfaces unexpected changes, assesses risk, and produces a structured review report — replicating CI-based plan review quality locally for immediate feedback.

**Features:**
- Waterfall plan acquisition (file path, auto-detect, generate, or ask)
- Git diff alignment check (expected vs unexpected changes)
- Risk assessment (destructive changes, data loss, IAM, networking, force-replacements)
- High-risk resource type awareness (AWS, GCP, Azure)
- Drift detection and common drift cause identification
- Emoji-rich terminal-optimized report

**Risk Categories:**
- Destructive changes and data loss potential
- IAM and permission escalation
- Network exposure changes
- Force-replacements of critical infrastructure
- Cost impact and scaling changes
- Provider warnings and deprecations

**Example:**
```bash
/terraform-plan-review                  # Auto-detect plan file in cwd
/terraform-plan-review plan_output.txt  # Analyze specific file
# → Produces structured report with resource counts, alignment check,
#   risk assessment, detailed changes, and recommendations
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

#### walletconnect-pay
Guides wallet developers through integrating WalletConnect Pay SDK so users can pay at any WC Pay-compatible POS terminal using USDC. Covers all three integration paths (WalletKit recommended, Standalone SDK, API-First) across all supported mobile frameworks.

**Supported frameworks:** Kotlin (Android), Swift (iOS), React Native, Flutter
**Supported assets:** USDC on Ethereum, Base, Optimism, Polygon, Arbitrum

**Features:**
- Framework selection guide (WalletKit vs Standalone vs API-First)
- Complete payment flow: link detection → options → actions → signing → data collection → confirm
- EIP-712 typed data signing examples per platform
- KYC/KYT WebView data collection integration with prefill support
- CAIP-10 account formatting for multi-chain payment options
- Payment status polling patterns
- Error handling and troubleshooting guide

**Reference files included:**
- `references/kotlin-walletkit.md` — Kotlin WalletKit integration
- `references/swift-walletkit.md` — Swift WalletKit integration
- `references/react-native-walletkit.md` — React Native WalletKit integration
- `references/flutter-walletkit.md` — Flutter WalletKit integration
- `references/kotlin-standalone.md` — Kotlin Standalone SDK (no WalletKit)
- `references/swift-standalone.md` — Swift Standalone SDK (no WalletKit)
- `references/react-native-standalone.md` — React Native Standalone SDK (no WalletKit)
- `references/flutter-standalone.md` — Flutter Standalone SDK (no WalletKit)
- `references/api-first.md` — Direct Gateway API integration

**Example:**
```bash
/walletconnect-pay
# "I'm building a Swift iOS wallet, how do I integrate WalletConnect Pay?"
# → Walks through WalletKit Swift setup, full payment flow, signing, WebView

/walletconnect-pay
# "My wallet doesn't use WalletKit, what are my options?"
# → Explains Standalone SDK and API-First approaches with code examples
```


## Available Commands

Commands are prompt templates that help with common development workflows. They are simple markdown files in `.claude/commands/` that Claude can use.

| Command | Description |
|---------|-------------|
| `analyze-dependencies` | Analyze and audit project dependencies |
| `api-documenter` | Generate API documentation |
| `aws-limits` | Review infrastructure code for AWS service quota violations |
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
│   ├── code-review/
│   │   └── SKILL.md
│   ├── code-simplifier/
│   │   └── SKILL.md
│   ├── command-creator/
│   │   └── SKILL.md
│   ├── context-audit/
│   │   ├── SKILL.md
│   │   └── CHECKLISTS.md
│   ├── deepnote-notebook/
│   │   └── SKILL.md
│   ├── github-dependabot-report/
│   │   ├── SKILL.md
│   │   ├── package.json
│   │   └── scripts/
│   ├── hubspot-security-queue/
│   │   ├── SKILL.md
│   │   ├── package.json
│   │   └── scripts/
│   ├── license-compliance/
│   │   ├── SKILL.md
│   │   ├── config/
│   │   └── scripts/
│   ├── linear-cli/
│   │   └── SKILL.md
│   ├── operational-readiness/
│   │   ├── SKILL.md
│   │   ├── assets/
│   │   ├── references/
│   │   └── scripts/
│   ├── repo-ai-setup/
│   │   ├── SKILL.md
│   │   └── REFERENCE.md
│   ├── security-audit-owasp-top-10/
│   │   ├── SKILL.md
│   │   ├── CATEGORIES.md
│   │   └── EVALUATIONS.md
│   ├── skill-writing/
│   │   └── SKILL.md
│   ├── supply-chain-security/
│   │   ├── SKILL.md
│   │   └── EVALUATIONS.md
│   ├── terraform-plan-review/
│   │   ├── SKILL.md
│   │   ├── REFERENCE.md
│   │   └── EVALUATIONS.md
│   └── worktree/
│       └── SKILL.md
├── .claude/
│   ├── skills -> ../skills  # Symlink for backwards compatibility
│   └── commands/            # All team commands
│       ├── analyze-dependencies.md
│       ├── api-documenter.md
│       ├── aws-limits.md
│       ├── commit-and-push.md
│       ├── debug-issue.md
│       ├── dev-diary.md
│       ├── explore-module.md
│       ├── fix.md
│       ├── gather-tech-docs.md
│       ├── github-assign-team-topics.md
│       ├── performance-check.md
│       ├── post-init-onboarding.md
│       ├── pre-deploy-check.md
│       ├── pre-review-check.md
│       ├── refactor-assistant.md
│       ├── respond.md
│       ├── review.md
│       ├── security-audit.md
│       ├── start-feature.md
│       ├── summarize_prs.md
│       ├── tdd.md
│       ├── tech-debt-hunt.md
│       ├── understand-codebase.md
│       ├── update-docs.md
│       └── visual-test.md    # (25 total)
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
