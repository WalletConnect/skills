# Evaluation Prompts

Test prompts validating activation, non-activation, and edge case behavior.

## Activation Tests (should trigger)

### 1. Direct audit request
**Prompt**: "Run a security audit on this codebase using OWASP Top 10"
**Expected**: Full 5-phase audit workflow. Report covers all 10 categories with relevance filtering.

### 2. OWASP-specific
**Prompt**: "Check this repo against the OWASP Top 10 2025 categories"
**Expected**: Triggers skill. Reconnaissance classifies project type. Report references 2025 categories including A03 Supply Chain and A10 Exceptional Conditions.

### 3. Partial audit
**Prompt**: "Audit A01 and A03 only for this project"
**Expected**: Partial audit mode. Minimal recon for language detection. Only A01 and A03 analyzed. Other categories listed as out-of-scope in report.

### 4. Vulnerability check
**Prompt**: "Check for common vulnerabilities in this codebase"
**Expected**: Triggers skill. Full audit with all phases. Report structured per OWASP categories.

### 5. IaC-specific
**Prompt**: "Run an OWASP security audit on this Terraform repository"
**Expected**: Project type classified as IaC. Relevance matrix applied: A01/A02 Full, A05/A07 Skip. Report focuses on access control, misconfiguration, supply chain.

## Non-Activation Tests (should not trigger)

### 6. PR review
**Prompt**: "Review PR #42 for security issues"
**Expected**: Does NOT trigger this skill. Uses review skill or manual review instead.

### 7. Dependency audit only
**Prompt**: "Run npm audit on this project"
**Expected**: Does NOT trigger. User wants `npm audit` output, not OWASP audit.

### 8. Compliance
**Prompt**: "Check our SOC2 compliance status"
**Expected**: Does NOT trigger. SOC2 is compliance-framework specific, not OWASP.

### 9. General OWASP question
**Prompt**: "What is OWASP Top 10?"
**Expected**: Does NOT trigger. Informational question, not audit request.

## Edge Case Tests

### 10. Empty/minimal codebase
**Prompt**: "Run OWASP audit" (on a repo with only README.md and .gitignore)
**Expected**: Phase 1 completes with "minimal/unknown" project type. Report notes insufficient code for meaningful audit. No false findings fabricated.

### 11. Monorepo
**Prompt**: "Audit this monorepo against OWASP Top 10" (on a repo with frontend/, backend/, infra/ directories)
**Expected**: Phase 1 identifies monorepo. Asks user preference: per-project sections or unified report. Runs relevance matrix per sub-project (e.g. frontend=web-app, infra=iac).

### 12. Single category deep dive
**Prompt**: "Deep dive into A04 Cryptographic Failures for this repo"
**Expected**: Partial audit mode. Exhaustive A04 analysis — runs all grep patterns, reads all flagged files, provides detailed semantic analysis. Other categories skipped.

### 13. Report to file
**Prompt**: "Run OWASP audit and save the report to security-report.md"
**Expected**: Full audit workflow. Report written to `security-report.md` via Write tool instead of inline output. Confirms file path with user.
