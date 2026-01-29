# Linear CLI Command Reference

Complete command reference for advanced usage.

## Issue Commands

### Viewing
```bash
linear issue view              # Current branch's issue
linear issue view ABC-123      # Specific issue
linear issue view -w           # Open in web browser
linear issue view -a           # Open in Linear.app
linear issue id                # Print issue ID only
linear issue title             # Print title only
linear issue url               # Print Linear.app URL
```

### Listing
```bash
linear issue list              # Your unstarted issues
linear issue list -A           # All unstarted (any assignee)
```

### Workflow
```bash
linear issue start             # Interactive: pick → branch → switch
linear issue start ABC-123     # Start specific issue
linear issue pr                # Create GitHub PR from current issue
```

### Management
```bash
linear issue create                           # Interactive
linear issue create -t "Title" -d "Desc"      # With flags
linear issue update                           # Update current issue
linear issue delete                           # Delete current issue
```

### Comments
```bash
linear issue comment list           # List comments on current issue
linear issue comment add            # Add comment interactively
linear issue comment add -p <id>    # Reply to specific comment
```

### VCS Integration (Jujutsu only)
```bash
linear issue commits           # Show all commits for issue
```

## Team Commands

```bash
linear team list               # Display all teams
linear team id                 # Print team ID (for scripts)
linear team members            # List team members
linear team create             # Create new team
linear team autolinks          # Configure GitHub autolinks
```

## Project Commands

```bash
linear project list            # Display all projects
linear project view            # View project details
```

## Milestone Commands

```bash
linear milestone list --project <projectId>
linear milestone view <milestoneId>
linear milestone create --project <projectId> --name "Q1 Goals" --target-date "2026-03-31"
linear milestone update <milestoneId> --name "New Name"
linear milestone delete <milestoneId>
```

## General Commands

```bash
linear --help                  # All commands
linear --version               # Version info
linear config                  # Configure project
linear completions             # Generate shell completions
```

## Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `LINEAR_API_KEY` | API authentication | `lin_api_xxxxx` |
| `LINEAR_TEAM_ID` | Default team | `TEAM_abc123` |
| `LINEAR_WORKSPACE` | Workspace slug | `mycompany` |
| `LINEAR_ISSUE_SORT` | Sort order | `priority` or `manual` |
| `LINEAR_VCS` | Version control | `git` or `jj` |
| `LINEAR_DOWNLOAD_IMAGES` | Fetch images | `true` or `false` |

## Config File Format

```toml
# .linear.toml
api_key = "lin_api_..."
team_id = "TEAM_abc123"
workspace = "mycompany"
issue_sort = "priority"
vcs = "git"
download_images = false
```

## Installation

```bash
# Homebrew (recommended)
brew install schpet/tap/linear

# Deno
deno install -A --reload -f -g -n linear jsr:@schpet/linear-cli

# From source
git clone https://github.com/schpet/linear-cli
cd linear-cli
deno task install
```
