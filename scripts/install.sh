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
            echo "Install Claude skills and agents to local ~/.claude/ directory"
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
            ((SKIPPED++))
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
    ((INSTALLED++))
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

# Install agents
if [[ -d "$REPO_ROOT/.claude/agents" ]]; then
    echo "Installing agents..."
    for agent_file in "$REPO_ROOT/.claude/agents"/*.md; do
        if [[ -f "$agent_file" ]]; then
            agent_name=$(basename "$agent_file")
            src="$agent_file"
            dest="$CLAUDE_DIR/agents/$agent_name"
            # Create agents directory if it doesn't exist
            mkdir -p "$CLAUDE_DIR/agents"
            copy_with_confirmation "$src" "$dest" "agent: ${agent_name%.md}"
        fi
    done
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
echo "To verify installation:"
echo "  ls ~/.claude/skills/"
echo "  ls ~/.claude/agents/"
