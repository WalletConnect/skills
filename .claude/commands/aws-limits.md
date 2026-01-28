# AWS Limits Review

Review infrastructure code for AWS service quota violations.

## Instructions

1. Identify the infrastructure files to review:
   - If `$ARGUMENTS` specifies files/paths, use those
   - Otherwise, find AWS-related files: `*.tf`, `*.yaml`, `*.yml`, `*.json`, `cdk.ts`, `pulumi.*`

2. Read the skill reference for comprehensive limits:
   - `~/.claude/skills/aws-limits/SKILL.md`
   - `~/.claude/skills/aws-limits/REFERENCE.md`

3. Scan code for AWS resource definitions and SDK usage

4. Check against known limits, prioritizing:
   - Hard limits that cause immediate failures
   - Default soft limits commonly hit at moderate scale
   - Architecture patterns that will hit limits at scale

5. Output findings in this format:

```markdown
## AWS Limits Review

### Critical
- **[Service]: [Limit]** - `file:line` - [Issue] - [Mitigation]

### High
...

### Medium
...

### Low / Informational
...

### Services Reviewed (No Issues)
- [List]
```

## Key Limits to Watch

- **ALB**: 5 LBs per target group (hard)
- **Lambda**: 15 min timeout, 6 MB sync payload (hard)
- **API Gateway**: 29s timeout (soft), 5,000 burst (hard)
- **Step Functions**: 25,000 events (hard)
- **Cognito**: 120 RPS auth (soft)
- **CloudFormation**: 500 resources per stack (hard)
- **DynamoDB**: 400 KB item size (hard)

Always include AWS documentation links for flagged limits.
