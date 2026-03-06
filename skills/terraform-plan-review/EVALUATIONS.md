# Evaluation Prompts

Test prompts validating activation, non-activation, and edge case behavior.

## Activation Tests (should trigger)

### 1. Direct plan review
**Prompt**: "Review this terraform plan output"
**Expected**: Phase 1 searches for plan files in cwd. Full 5-phase workflow produces structured report with resource counts, alignment check, risk assessment, and recommendations.

### 2. Explicit file path
**Prompt**: "/terraform-plan-review plan_output.txt"
**Expected**: Phase 1 reads `plan_output.txt` directly. Skips auto-detection. Full analysis and report.

### 3. Safety check
**Prompt**: "Is this terraform plan safe to apply?"
**Expected**: Triggers skill. Emphasis on risk assessment section. Verdict clearly states safe/review/high-risk.

### 4. Pre-PR review
**Prompt**: "Check my terraform changes before I create a PR"
**Expected**: Full workflow including git diff alignment check. Report highlights expected vs unexpected changes.

### 5. Plan analysis
**Prompt**: "Analyze plan.txt and tell me what it will do"
**Expected**: Phase 1 reads `plan.txt`. Report focuses on detailed changes section with clear per-resource breakdown.

## Non-Activation Tests (should not trigger)

### 6. Code review
**Prompt**: "Review my Terraform code for best practices"
**Expected**: Does NOT trigger. No plan output involved — use code-review skill.

### 7. Write Terraform
**Prompt**: "Write a Terraform module for an S3 bucket"
**Expected**: Does NOT trigger. User wants code generation, not plan review.

### 8. State management
**Prompt**: "How do I import an existing resource into Terraform state?"
**Expected**: Does NOT trigger. Informational question about state management.

### 9. Cost estimation
**Prompt**: "How much will this Terraform change cost?"
**Expected**: Does NOT trigger. Cost estimation is a separate concern.

## Edge Case Tests

### 10. No changes plan
**Prompt**: "/terraform-plan-review" (on a plan output showing "No changes. Infrastructure is up-to-date.")
**Expected**: Reports clean plan. Skips alignment and risk sections. Brief confirmation that infrastructure matches configuration.

### 11. Plan with errors
**Prompt**: "/terraform-plan-review" (on a plan output containing errors instead of a plan)
**Expected**: Identifies errors in plan output. Reports the errors with context. Suggests fixes rather than analyzing a non-existent plan.

### 12. Large plan
**Prompt**: "/terraform-plan-review" (on a plan with 150+ resource changes)
**Expected**: Summarizes at category level. Details only high-risk and unexpected changes. Notes that some resources are summarized for brevity.

### 13. No git repo
**Prompt**: "/terraform-plan-review plan.txt" (outside a git repository)
**Expected**: Phase 2 detects no git repo. Alignment check skipped with note in report. All other phases proceed normally.
