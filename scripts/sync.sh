#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLAUDE_DIR="$HOME/.claude"
MODE="bidirectional"
DRY_RUN=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --pull)
            MODE="pull"
            shift
            ;;
        --push)
            MODE="push"
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Sync Claude skills and agents between repository and local ~/.claude/"
            echo ""
            echo "OPTIONS:"
            echo "  --pull         Only sync from repository to local"
            echo "  --push         Only sync from local to repository"
            echo "  --dry-run      Show what would change without making changes"
            echo "  --help, -h     Show this help message"
            echo ""
            echo "Default behavior (no options): Interactive bidirectional sync"
            exit 0
            ;;
        *)
            echo -e "${RED}ERROR${NC}: Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}WalletConnect Claude Files Sync${NC}"
echo ""

# Check if ~/.claude/ exists
if [[ ! -d "$CLAUDE_DIR" ]]; then
    echo -e "${RED}ERROR${NC}: ~/.claude/ directory not found"
    echo "Please install Claude Code first"
    exit 1
fi

# Validate repository files before syncing
echo "Validating repository files..."
if ! "$REPO_ROOT/scripts/validate.sh" >/dev/null 2>&1; then
    echo -e "${YELLOW}WARNING${NC}: Repository validation failed. Proceeding anyway..."
fi

echo ""

# Function to sync directories
sync_dir() {
    local src="$1"
    local dest="$2"
    local direction="$3"

    # Ensure destination exists
    mkdir -p "$dest"

    if [[ "$DRY_RUN" == true ]]; then
        echo -e "${YELLOW}[DRY RUN]${NC} $direction: $src → $dest"
        rsync -avn --itemize-changes --exclude='.DS_Store' "$src/" "$dest/" | grep -v "^sending\|^sent\|^total\|^$" || true
    else
        echo -e "${BLUE}Syncing${NC} $direction: $src → $dest"
        rsync -av --itemize-changes --exclude='.DS_Store' "$src/" "$dest/" | grep -v "^sending\|^sent\|^total\|^$" || true
    fi
}

# Pull from repository to local
if [[ "$MODE" == "pull" ]] || [[ "$MODE" == "bidirectional" ]]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Syncing from repository → local"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    if [[ -d "$REPO_ROOT/.claude/skills" ]]; then
        sync_dir "$REPO_ROOT/.claude/skills" "$CLAUDE_DIR/skills" "skills"
        echo ""
    fi

    if [[ -d "$REPO_ROOT/.claude/agents" ]]; then
        sync_dir "$REPO_ROOT/.claude/agents" "$CLAUDE_DIR/agents" "agents"
        echo ""
    fi
fi

# Push from local to repository
if [[ "$MODE" == "push" ]] || [[ "$MODE" == "bidirectional" ]]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Syncing from local → repository"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    if [[ -d "$CLAUDE_DIR/skills" ]]; then
        sync_dir "$CLAUDE_DIR/skills" "$REPO_ROOT/.claude/skills" "skills"
        echo ""
    fi

    if [[ -d "$CLAUDE_DIR/agents" ]]; then
        sync_dir "$CLAUDE_DIR/agents" "$REPO_ROOT/.claude/agents" "agents"
        echo ""
    fi

    # Validate after push
    if [[ "$DRY_RUN" != true ]]; then
        echo "Validating synced files..."
        if ! "$REPO_ROOT/scripts/validate.sh"; then
            echo ""
            echo -e "${RED}WARNING${NC}: Validation failed after sync"
            echo "Please review changes and fix any errors before committing"
            exit 1
        fi
    fi
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}Dry run complete${NC} - no changes made"
    echo ""
    echo "Run without --dry-run to apply these changes"
else
    echo -e "${GREEN}✓ Sync complete!${NC}"
    echo ""
    if [[ "$MODE" == "push" ]] || [[ "$MODE" == "bidirectional" ]]; then
        echo "Next steps:"
        echo "  git status          # Review changes"
        echo "  git add .claude/    # Stage changes"
        echo "  git commit -m '...' # Commit with conventional format"
        echo "  git push            # Push to remote"
    fi
fi
