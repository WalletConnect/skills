---
name: worktree
description: Create and configure a new git worktree with conventional commit style branch naming. Use when the user wants to create a worktree or mentions 'worktree', 'new branch in separate directory', or 'parallel work on different branch'.
user-invocable: true
---

# Create Git Worktree

Creates a new git worktree in a sibling directory with proper branch naming following conventional commit conventions.

## Instructions

When the user invokes this skill:

1. **Get the worktree name**: If not provided, ask the user what name they want for the worktree (e.g., "alerts", "new-dashboard", "fix-terraform").

2. **Prompt for commit type**: Use the AskUserQuestion tool to ask which conventional commit type to use:
   - Question: "Which type of change will this worktree be for?"
   - Header: "Commit type"
   - Options:
     - feat: New feature or functionality
     - fix: Bug fix
     - chore: Maintenance, dependencies, or tooling
     - docs: Documentation changes
     - refactor: Code refactoring without feature changes
     - test: Adding or updating tests
     - perf: Performance improvements
     - ci: CI/CD configuration changes

3. **Construct the branch name**: Combine the selected type with the provided name using a forward slash:
   - Format: `{type}/{name}`
   - Example: `feat/queue-alerts` or `fix/terraform-validation`

4. **Determine worktree path**:
   - Get the current repository name from the git remote or directory name
   - Construct the sibling directory path: `../{repo-name}-{branch-name}`
   - Example: If repo is `infra-monitoring-grafana` and branch is `feat/alerts`, path is `../infra-monitoring-grafana-feat-alerts`
   - Replace forward slashes in branch name with hyphens for the directory name

5. **Create the worktree**: Run the git worktree command:
   ```bash
   git worktree add -b {branch-name} {worktree-path}
   ```
   - The `-b` flag creates a new branch
   - This creates the directory and checks out the new branch

6. **Confirm success**: After creation, inform the user:
   - The branch name that was created
   - The directory path where the worktree was created
   - Provide a command they can use to change into the worktree:
     ```bash
     cd {worktree-path}
     ```

7. **Handle errors**: If the worktree creation fails:
   - Check if a worktree or branch with that name already exists
   - Suggest an alternative name or ask if they want to use an existing worktree
   - Check if the target directory already exists

## Example Usage

User: `/worktree alerts`
- Claude prompts for commit type → User selects "feat"
- Creates branch: `feat/alerts`
- Creates worktree at: `../infra-monitoring-grafana-feat-alerts`
- Shows: `cd ../infra-monitoring-grafana-feat-alerts`

## Notes

- Worktrees allow working on multiple branches simultaneously without switching
- Each worktree has its own working directory but shares the same git history
- To remove a worktree later, use: `git worktree remove {path}`
- List all worktrees with: `git worktree list`
