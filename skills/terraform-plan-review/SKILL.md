---
name: terraform-plan-review
description: >-
  Analyzes Terraform plan output as a staff DevOps engineer. Compares planned
  changes against code diff, counts resources, identifies unexpected changes,
  assesses risk. Use when reviewing terraform plan output locally, checking if
  a plan is safe to apply, or doing pre-PR infrastructure review.
---

# Terraform Plan Review

## Goal

Analyze Terraform plan output with the rigor of a staff DevOps engineer. Compare planned changes against the code diff to surface unexpected changes, assess risk, and produce a structured review report — replicating CI-based plan review quality locally for immediate feedback.

## When to use

- "Review this terraform plan"
- "Is this plan safe to apply?"
- "Analyze plan_output.txt"
- "Check my terraform changes before I PR"
- "What does this plan do?"
- "Review my infra changes"

## When not to use

- General Terraform code review without plan output (use code-review skill)
- Writing or generating Terraform code
- Terraform state management or import operations
- Cloud cost estimation (use infracost or similar)
- OWASP security audit (use security-audit-owasp-top-10 skill)

## Inputs

- Terraform plan output (file path, auto-detected file, or generated via `terraform plan`)
- Optional: stderr/log file with warnings and errors
- Optional: git diff of `.tf`/`.tfvars`/`.hcl` changes

## Outputs

- Structured markdown report inline with resource counts, alignment check, risk assessment, detailed changes, and recommendations

## Workflow

### Phase 1: Acquire Plan Output

Waterfall strategy — try each approach in order:

1. **Explicit path**: If `$ARGUMENTS` contains a file path, read that file
2. **Auto-detect**: Glob for plan output files in cwd:
   ```
   Glob: plan.txt, plan_output.txt, tfplan.txt, *plan*.txt
   ```
   If exactly one match, use it. If multiple, ask user to pick.
3. **Generate**: If `.terraform/` directory exists, offer to run:
   ```bash
   terraform plan -no-color > /tmp/plan_output.txt 2>/tmp/plan_stderr.log; echo "EXIT CODE: $?"
   ```
   Before running, check for `.tfvars` files (Glob `**/*.tfvars`) and if found, add `-var-file=<path>` to the command. `cd` into the directory containing `*.tf` files first if they are in a subdirectory. Wait for user confirmation before running. Analyze the result.
4. **Ask**: If none of the above work, ask the user to provide a file path.

Also check for optional log/stderr files:
```
Glob: plan.log, plan_stderr.log, *plan*.log
```

### Phase 2: Acquire Git Diff

For alignment checking, gather the Terraform-relevant code diff:

1. Detect base branch: check for `main`, then `master`, then upstream tracking branch
2. Combine diffs:
   ```bash
   git diff <base>...HEAD -- '*.tf' '*.tfvars' '*.hcl'
   git diff -- '*.tf' '*.tfvars' '*.hcl'
   git diff --staged -- '*.tf' '*.tfvars' '*.hcl'
   ```
3. Filter to Terraform files only (`.tf`, `.tfvars`, `.hcl`)
4. If not a git repo or no diff available, skip alignment check and note it in the report

### Phase 3: Analyze Plan

Read the full plan output and extract:

1. **Summary line**: Parse `Plan: X to add, Y to change, Z to destroy` (or "No changes")
2. **Resource changes**: Enumerate every resource action, grouped by operation type:
   - Created (`+`)
   - Updated in-place (`~`)
   - Destroyed (`-`)
   - Replaced (destroy then create, or create then destroy) (`-/+` or `+/-`)
   - Read (data sources)
3. **Attribute details**: For each changed resource, note which attributes are modified and whether values are known or `(known after apply)`
4. **Context**: Read relevant `.tf` files for the changed resources:
   ```
   Glob: **/*.tf
   ```
   Read files that define or reference the changed resources.
5. **Log analysis**: If a log/stderr file exists, parse for:
   - Warnings (deprecations, provider issues)
   - Errors
   - Provider version information

### Phase 4: Alignment Check + Risk Assessment

**Alignment Check** — compare each planned change against the git diff:

- **Expected**: Change directly maps to a code modification in the diff
- **Unexpected**: Change has no corresponding code diff — indicates drift, implicit dependencies, provider behavior changes, or module version side effects

**Risk Assessment** — evaluate each risk category using patterns from `REFERENCE.md`:

| Risk Category | What to look for |
|---|---|
| Destructive changes | Resources being destroyed or replaced, especially stateful resources (databases, storage, encryption keys) |
| Data loss potential | Destruction of resources that contain data (RDS, S3, DynamoDB, EBS, etc.) |
| IAM changes | New or modified IAM roles, policies, permissions — especially wildcards or admin access |
| Network changes | Security groups, NACLs, VPC peering, route changes that could affect connectivity or exposure |
| Force-replacements | Resources being replaced due to immutable attribute changes (name, AMI, engine version) |
| Cost impact | New resources or scaling changes that significantly affect cost (large instances, NAT gateways, etc.) |
| Warnings/errors | Deprecation warnings, provider errors, or validation issues from log file |

**Risk Level Classification**:
- **High**: Any destructive change to stateful resources, IAM wildcard permissions, public network exposure, or force-replacement of critical infrastructure
- **Medium**: Non-destructive changes to security-sensitive resources, new IAM policies with bounded scope, scaling changes
- **Low**: Additive-only changes, tag updates, config changes to non-sensitive resources, output changes

### Phase 5: Generate Report

Produce emoji-rich markdown optimized for terminal display (no HTML tags like `<details>`):

```markdown
## 📊 Terraform Plan Review

**Summary:**
- Resources: X to add, Y to change, Z to destroy
- Verdict: ✅ Safe to apply / ⚠️ Review recommended / 🚨 High risk — review carefully
- Risk Level: Low / Medium / High

### 📋 Resource Summary

| Operation | Count | Resources |
|-----------|-------|-----------|
| ➕ Create | N | `resource.name`, ... |
| 🔄 Update | N | `resource.name`, ... |
| ❌ Destroy | N | `resource.name`, ... |
| ♻️ Replace | N | `resource.name`, ... |

### ✅ Alignment Check

**Expected Changes** (match code diff):
- `resource.name` — <why it's expected based on diff>

**Unexpected Changes** (no matching code diff):
- `resource.name` — <likely cause: drift / implicit dependency / provider behavior>

(If no git diff available: "⚠️ No git diff available — alignment check skipped")

### 🔥 Risk Assessment

For each risk found:
- **[Category]**: `resource.name` — <description of risk and impact>

If no risks: "✅ No significant risks identified"

### 📝 Detailed Changes

Group by operation type. For each resource:

**➕ Create: `resource_type.name`**
- key_attribute = "value"
- key_attribute = (known after apply)

**🔄 Update: `resource_type.name`**
- attribute: "old_value" → "new_value"

**❌ Destroy: `resource_type.name`**
- (note if stateful / contains data)

**♻️ Replace: `resource_type.name`**
- Trigger: <attribute causing replacement>
- ⚠️ This will destroy and recreate the resource

### 💡 Recommendations

Actionable next steps based on findings:
1. <specific action items>
2. <risk mitigations>
3. <suggested follow-ups>
```

## Decision Points

- **Very large plan (>100 resources)**: Summarize at category level, only detail high-risk and unexpected changes. Note truncation.
- **No changes plan**: Report as clean — "Plan: no changes. Infrastructure is up-to-date." Skip Phases 4-5, just confirm.
- **Plan errors**: If the plan output contains errors instead of a plan, report the errors and suggest fixes rather than analyzing a plan.
- **Multiple workspaces**: If plan mentions workspace, note which workspace is being planned against.

## Validation Checklist

- [ ] Plan output successfully read and parsed
- [ ] Resource count matches summary line
- [ ] Every resource change categorized (create/update/destroy/replace)
- [ ] Alignment check performed (or noted as skipped with reason)
- [ ] Risk assessment covers all categories from REFERENCE.md
- [ ] Report uses consistent risk level definitions
- [ ] Recommendations are actionable and specific

## References

- High-risk patterns, resource types, drift causes: `REFERENCE.md`
- Evaluation prompts: `EVALUATIONS.md`
