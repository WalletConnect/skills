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
            echo "Sync Claude skills and commands between repository and local ~/.claude/"
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

# Markers for CLAUDE.md append-only mode
CLAUDE_MD_BEGIN="<!-- BEGIN walletconnect/claude-files -->"
CLAUDE_MD_END="<!-- END walletconnect/claude-files -->"

# Function to append CLAUDE.md content without overwriting user content
append_claude_md() {
    local src="$1"
    local dest="$2"

    local repo_content
    repo_content=$(cat "$src")
    local marked_content="${CLAUDE_MD_BEGIN}
${repo_content}
${CLAUDE_MD_END}"

    if [[ "$DRY_RUN" == true ]]; then
        if [[ ! -f "$dest" ]]; then
            echo -e "${YELLOW}[DRY RUN]${NC} Would create: CLAUDE.md"
        elif grep -q "$CLAUDE_MD_BEGIN" "$dest"; then
            echo -e "${YELLOW}[DRY RUN]${NC} Would update: CLAUDE.md"
        else
            echo -e "${YELLOW}[DRY RUN]${NC} Would append: CLAUDE.md"
        fi
        return
    fi

    if [[ ! -f "$dest" ]]; then
        # Create new file with just the marked content
        echo "$marked_content" > "$dest"
        echo -e "${GREEN}✓${NC} Created: CLAUDE.md"
    elif grep -q "$CLAUDE_MD_BEGIN" "$dest"; then
        # Replace existing marked section using line numbers (portable)
        local begin_line end_line total_lines before after
        begin_line=$(grep -n "$CLAUDE_MD_BEGIN" "$dest" | head -1 | cut -d: -f1)
        end_line=$(grep -n "$CLAUDE_MD_END" "$dest" | tail -1 | cut -d: -f1)
        total_lines=$(wc -l < "$dest" | tr -d ' ')

        # Get content before the marker (if any)
        if [[ "$begin_line" -gt 1 ]]; then
            before=$(head -n $((begin_line - 1)) "$dest")
        else
            before=""
        fi

        # Get content after the marker (if any)
        if [[ "$end_line" -lt "$total_lines" ]]; then
            after=$(tail -n $((total_lines - end_line)) "$dest")
        else
            after=""
        fi

        {
            if [[ -n "$before" ]]; then
                echo "$before"
            fi
            echo "$marked_content"
            if [[ -n "$after" ]]; then
                echo "$after"
            fi
        } > "$dest"
        echo -e "${GREEN}✓${NC} Updated: CLAUDE.md"
    else
        # Append marked content to existing file
        {
            echo ""
            echo "$marked_content"
        } >> "$dest"
        echo -e "${GREEN}✓${NC} Appended: CLAUDE.md"
    fi
}

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

    if [[ -d "$REPO_ROOT/.claude/commands" ]]; then
        sync_dir "$REPO_ROOT/.claude/commands" "$CLAUDE_DIR/commands" "commands"
        echo ""
    fi

    # Sync CLAUDE.md (append-only)
    if [[ -f "$REPO_ROOT/CLAUDE.md" ]]; then
        append_claude_md "$REPO_ROOT/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"
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

    if [[ -d "$CLAUDE_DIR/commands" ]]; then
        sync_dir "$CLAUDE_DIR/commands" "$REPO_ROOT/.claude/commands" "commands"
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
