#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLAUDE_DIR="$HOME/.claude"
FORCE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f)
            FORCE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Install Claude skills and commands to local ~/.claude/ directory"
            echo ""
            echo "OPTIONS:"
            echo "  --force, -f    Overwrite existing files without asking"
            echo "  --help, -h     Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}ERROR${NC}: Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}WalletConnect Claude Files Installer${NC}"
echo ""

# Check if ~/.claude/ exists
if [[ ! -d "$CLAUDE_DIR" ]]; then
    echo -e "${RED}ERROR${NC}: ~/.claude/ directory not found"
    echo "Please install Claude Code first: https://docs.claude.ai/claude-code"
    exit 1
fi

# Validate files before installing
echo "Validating files..."
if ! "$REPO_ROOT/scripts/validate.sh"; then
    echo ""
    echo -e "${RED}ERROR${NC}: Validation failed. Please fix errors before installing."
    exit 1
fi

echo ""
echo "Installing to $CLAUDE_DIR..."
echo ""

INSTALLED=0
SKIPPED=0

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

    if [[ ! -f "$dest" ]]; then
        # Create new file with just the marked content
        echo "$marked_content" > "$dest"
        echo -e "${GREEN}✓${NC} Created: CLAUDE.md"
        ((++INSTALLED))
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
        ((++INSTALLED))
    else
        # Append marked content to existing file
        {
            echo ""
            echo "$marked_content"
        } >> "$dest"
        echo -e "${GREEN}✓${NC} Appended: CLAUDE.md"
        ((++INSTALLED))
    fi
}

# Function to copy with confirmation
copy_with_confirmation() {
    local src="$1"
    local dest="$2"
    local type="$3"

    if [[ -e "$dest" ]] && [[ "$FORCE" != true ]]; then
        echo -e "${YELLOW}File exists${NC}: $dest"
        read -p "Overwrite? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Skipped${NC}: $type"
            ((++SKIPPED))
            return
        fi
    fi

    # Create parent directory if needed
    mkdir -p "$(dirname "$dest")"

    # Copy the file/directory
    if [[ -d "$src" ]]; then
        cp -r "$src" "$dest"
    else
        cp "$src" "$dest"
    fi

    echo -e "${GREEN}✓${NC} Installed: $type"
    ((++INSTALLED))
}

# Install skills
if [[ -d "$REPO_ROOT/.claude/skills" ]]; then
    echo "Installing skills..."
    for skill_dir in "$REPO_ROOT/.claude/skills"/*; do
        if [[ -d "$skill_dir" ]]; then
            skill_name=$(basename "$skill_dir")
            src="$skill_dir"
            dest="$CLAUDE_DIR/skills/$skill_name"
            copy_with_confirmation "$src" "$dest" "skill: $skill_name"
        fi
    done
    echo ""
fi

# Install commands
if [[ -d "$REPO_ROOT/.claude/commands" ]]; then
    echo "Installing commands..."
    for command_file in "$REPO_ROOT/.claude/commands"/*.md; do
        if [[ -f "$command_file" ]]; then
            command_name=$(basename "$command_file")
            src="$command_file"
            dest="$CLAUDE_DIR/commands/$command_name"
            # Create commands directory if it doesn't exist
            mkdir -p "$CLAUDE_DIR/commands"
            copy_with_confirmation "$src" "$dest" "command: ${command_name%.md}"
        fi
    done
    echo ""
fi

# Install CLAUDE.md (append-only)
if [[ -f "$REPO_ROOT/CLAUDE.md" ]]; then
    echo "Installing CLAUDE.md..."
    append_claude_md "$REPO_ROOT/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"
    echo ""
fi

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✓${NC} Installation complete!"
echo ""
echo "Installed: $INSTALLED file(s)"
if [[ $SKIPPED -gt 0 ]]; then
    echo "Skipped:   $SKIPPED file(s)"
fi
echo ""
echo "Files installed to: $CLAUDE_DIR"
echo ""

# Verify installation
echo "Verifying installation..."
INSTALLED_SKILLS=$(ls -1 "$CLAUDE_DIR/skills" 2>/dev/null | wc -l | tr -d ' ')
INSTALLED_COMMANDS=$(ls -1 "$CLAUDE_DIR/commands" 2>/dev/null | wc -l | tr -d ' ')
echo -e "${GREEN}✓${NC} $INSTALLED_SKILLS skill(s) and $INSTALLED_COMMANDS command(s) installed"
