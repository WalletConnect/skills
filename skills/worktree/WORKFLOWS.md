# Worktree Workflows

Detailed step-by-step procedures for complex worktree operations.

## Remove Workflow (Full)

Complete procedure for safe worktree removal with branch cleanup.

```
START
  │
  ├─► Get target path (from args or prompt)
  │
  ├─► Validate target
  │   ├─ Is main worktree? → ABORT "Cannot remove main worktree"
  │   └─ Path exists? → Continue / ABORT "Worktree not found"
  │
  ├─► Check worktree status
  │   │  git -C {path} status --porcelain
  │   │
  │   ├─ Has uncommitted changes?
  │   │   └─► Warn user, ask: "Force remove and lose changes?"
  │   │       ├─ No → ABORT
  │   │       └─ Yes → Set force_flag = -f
  │   │
  │   └─ Is locked?
  │       └─► Ask: "Worktree is locked. Force remove anyway?"
  │           ├─ No → ABORT
  │           └─ Yes → Set force_flag = -ff
  │
  ├─► Get branch name
  │   │  git -C {path} branch --show-current
  │   └─ Save as {branch}
  │
  ├─► Check for unpushed commits
  │   │  git -C {path} log @{u}..HEAD --oneline 2>/dev/null
  │   └─ If any → Warn "Branch has X unpushed commits"
  │
  ├─► Remove worktree
  │   │  git worktree remove {force_flag} {path}
  │   └─ Verify success
  │
  ├─► Delete local branch
  │   │  git branch -d {branch}
  │   ├─ Success → Continue
  │   └─ Failed (not merged) → Ask: "Branch not merged. Force delete?"
  │       ├─ No → Skip branch deletion
  │       └─ Yes → git branch -D {branch}
  │
  ├─► Check for remote branch
  │   │  git ls-remote --heads origin {branch}
  │   ├─ Not found → Skip
  │   └─ Found → Ask: "Delete remote branch origin/{branch}?"
  │       ├─ No → Skip
  │       └─ Yes → git push origin --delete {branch}
  │
  └─► Report summary
      - Worktree removed: {path}
      - Local branch deleted: {branch} (or "skipped")
      - Remote branch deleted: origin/{branch} (or "skipped")
END
```

---

## Cleanup Workflow (Batch)

Interactive batch removal with smart filtering.

```
START
  │
  ├─► List all worktrees
  │   │  git worktree list --porcelain
  │   └─ Parse into array of {path, branch, flags}
  │
  ├─► Identify main worktree
  │   │  First entry OR entry where path matches $(git rev-parse --show-toplevel)
  │   └─ Mark as protected
  │
  ├─► Gather status for each non-main worktree
  │   │  For each worktree:
  │   │    - Check if prunable (flag in porcelain output)
  │   │    - Check if branch merged: git branch --merged main | grep {branch}
  │   │    - Check last commit age: git -C {path} log -1 --format=%cr
  │   │    - Check uncommitted changes count
  │   │
  │   └─ Build status string for each:
  │      "{branch} - {status}"
  │      e.g., "feat/old - merged, no changes, 3 weeks old"
  │
  ├─► Present selection (AskUserQuestion)
  │   │  Question: "Which worktrees to remove?"
  │   │  multiSelect: true
  │   │  Options: List each with status
  │   │
  │   └─ If no selection → END
  │
  ├─► For each selected worktree
  │   │  Run Remove Workflow (above)
  │   └─ Collect results
  │
  ├─► Run prune
  │   │  git worktree prune -v
  │   └─ Capture pruned entries
  │
  └─► Report summary
      - Worktrees removed: X
      - Branches deleted: Y local, Z remote
      - Stale entries pruned: N
END
```

---

## Create Workflow (Detailed)

```
START
  │
  ├─► Parse args for worktree name
  │   ├─ Name provided → Use it
  │   └─ No name → Ask user: "What name for this worktree?"
  │
  ├─► Prompt for commit type (AskUserQuestion)
  │   │  Header: "Commit type"
  │   │  Options:
  │   │    - feat: New feature
  │   │    - fix: Bug fix
  │   │    - chore: Maintenance
  │   │    - docs: Documentation
  │   │    - refactor: Refactoring
  │   │    - test: Tests
  │   │    - perf: Performance
  │   │    - ci: CI/CD
  │   │
  │   └─ Save as {type}
  │
  ├─► Construct branch name
  │   │  {type}/{name}
  │   └─ e.g., feat/queue-alerts
  │
  ├─► Get repo name
  │   │  Try: basename of $(git remote get-url origin) without .git
  │   │  Fallback: basename of $(pwd)
  │   └─ Save as {repo}
  │
  ├─► Construct worktree path
  │   │  ../{repo}-{type}-{name}
  │   │  (replace / with - in type/name)
  │   └─ e.g., ../my-project-feat-queue-alerts
  │
  ├─► Check for conflicts
  │   ├─ Branch exists? git show-ref --verify refs/heads/{branch}
  │   │   └─ Yes → Ask: "Use existing branch or pick new name?"
  │   │
  │   └─ Directory exists? test -d {path}
  │       └─ Yes → Ask: "Directory exists. Use different name?"
  │
  ├─► Create worktree
  │   │  git worktree add -b {branch} {path}
  │   │  OR (if using existing branch)
  │   │  git worktree add {path} {branch}
  │   │
  │   └─ Check exit code
  │
  └─► Report success
      - Branch: {branch}
      - Path: {path}
      - Command: cd {path}
END
```

---

## Lock Workflow

```
START
  │
  ├─► Get target (from args or list non-locked worktrees)
  │
  ├─► Validate
  │   ├─ Is main worktree? → ABORT "Main worktree doesn't need locking"
  │   └─ Already locked? → ABORT "Already locked"
  │
  ├─► Ask for reason (optional)
  │   │  "Why lock this worktree? (optional)"
  │   └─ Options: portable device, long experiment, other, skip
  │
  ├─► Lock
  │   │  git worktree lock {path}
  │   │  OR
  │   │  git worktree lock --reason "{reason}" {path}
  │   │
  │   └─ Verify: git worktree list -v | grep locked
  │
  └─► Confirm: "Locked {path}. Reason: {reason}"
END
```

---

## Prune Workflow

```
START
  │
  ├─► Preview
  │   │  git worktree prune -n -v
  │   │
  │   ├─ No stale entries → Report "Nothing to prune" → END
  │   └─ Found entries → Show list
  │
  ├─► Confirm
  │   │  "Prune these X stale entries?"
  │   ├─ No → END
  │   └─ Yes → Continue
  │
  ├─► Prune
  │   │  git worktree prune -v
  │   └─ Capture output
  │
  └─► Report: "Pruned X entries"
END
```

---

## Useful Commands Reference

| Task | Command |
|------|---------|
| List verbose | `git worktree list -v` |
| List porcelain | `git worktree list --porcelain` |
| Check if branch merged | `git branch --merged main \| grep {branch}` |
| Get current branch | `git branch --show-current` |
| Check uncommitted | `git status --porcelain` |
| Count uncommitted | `git status --porcelain \| wc -l` |
| Unpushed commits | `git log @{u}..HEAD --oneline` |
| Check remote branch | `git ls-remote --heads origin {branch}` |
| Last commit age | `git log -1 --format=%cr` |
| Get repo name | `basename $(git remote get-url origin .git)` |
| Main worktree path | `git rev-parse --show-toplevel` |
