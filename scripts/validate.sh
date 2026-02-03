#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ERRORS=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Validating Claude files..."

# Function to extract frontmatter from a file
extract_frontmatter() {
    local file="$1"
    awk '/^---$/{if(++c==2){exit}}c==1' "$file"
}

# Function to get a field from frontmatter
get_field() {
    local frontmatter="$1"
    local field="$2"
    echo "$frontmatter" | grep "^${field}:" | sed "s/^${field}:[[:space:]]*//" | tr -d '"' | tr -d "'"
}

# Function to validate a skill file
validate_skill() {
    local file="$1"
    local skill_dir="$(dirname "$file")"
    local skill_name="$(basename "$skill_dir")"
    local errors=0

    # Check filename is SKILL.md
    if [[ "$(basename "$file")" != "SKILL.md" ]]; then
        echo -e "${RED}ERROR${NC} $file: Skill files must be named SKILL.md"
        ((errors++))
    fi

    # Extract frontmatter
    local frontmatter=$(extract_frontmatter "$file")

    if [[ -z "$frontmatter" ]]; then
        echo -e "${RED}ERROR${NC} $file: No frontmatter found (must start with ---)"
        ((errors++))
        return $errors
    fi

    # Validate required fields
    local name=$(get_field "$frontmatter" "name")
    local description=$(get_field "$frontmatter" "description")

    if [[ -z "$name" ]]; then
        echo -e "${RED}ERROR${NC} $file: Missing required field 'name' in frontmatter"
        ((errors++))
    fi

    if [[ -z "$description" ]]; then
        echo -e "${RED}ERROR${NC} $file: Missing required field 'description' in frontmatter"
        ((errors++))
    fi

    # Check if directory name matches skill name (if name exists)
    if [[ -n "$name" ]] && [[ "$name" != "$skill_name" ]]; then
        echo -e "${YELLOW}WARNING${NC} $file: Directory name '$skill_name' doesn't match skill name '$name'"
    fi

    return $errors
}

# Validate skills
echo ""
echo "Validating skills..."
skill_count=0
if [[ -d "$REPO_ROOT/.claude/skills" ]]; then
    while IFS= read -r -d '' file; do
        ((skill_count++))
        if validate_skill "$file"; then
            :
        else
            ((ERRORS += $?))
        fi
    done < <(find -L "$REPO_ROOT/.claude/skills" -name "SKILL.md" -print0)
fi

if [[ $skill_count -eq 0 ]]; then
    echo -e "${YELLOW}WARNING${NC} No skills found in .claude/skills/"
else
    echo -e "${GREEN}✓${NC} Validated $skill_count skill(s)"
fi

echo ""
if [[ $ERRORS -eq 0 ]]; then
    echo -e "${GREEN}✓ Validation passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Validation failed with $ERRORS error(s)${NC}"
    exit 1
fi
