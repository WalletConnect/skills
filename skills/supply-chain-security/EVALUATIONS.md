# Evaluation Prompts

Test prompts validating activation, non-activation, and edge case behavior.

## Activation Tests (should trigger)

### 1. PR review for supply-chain patterns
**Prompt**: "Check this PR for supply-chain attack indicators"
**Expected**: Skill activates. Reviews PR diff for invisible Unicode, malicious hooks, lockfile anomalies, and eval-based decoders. Runs byte-count cross-checks on suspicious files.

### 2. Glassworm-specific
**Prompt**: "Scan this repo for Glassworm attack patterns"
**Expected**: Triggers skill. Runs hex-dump scans for PUA variation selectors, checks for zero-width characters, searches for `codePointAt` + `0xFE00` decoder patterns.

### 3. Dependency change review
**Prompt**: "Review this package.json change for security issues"
**Expected**: Triggers skill. Checks for unexpected `preinstall`/`postinstall` hooks, lockfile-only changes, eval+Buffer patterns in added dependencies.

### 4. Invisible Unicode check
**Prompt**: "Check if any files in this diff contain hidden Unicode characters"
**Expected**: Triggers skill. Runs detection commands (xxd hex dump, zero-width grep, byte-count anomaly check). Reports findings per file.

### 5. Lockfile anomaly
**Prompt**: "The lockfile changed but package.json didn't — is this safe?"
**Expected**: Triggers skill. Flags as a supply-chain red flag. Examines lockfile diff for suspicious version changes, new registries, or integrity hash mismatches.

## Non-Activation Tests (should not trigger)

### 6. General OWASP audit
**Prompt**: "Run an OWASP Top 10 audit on this codebase"
**Expected**: Does NOT trigger this skill. Uses `security-audit-owasp-top-10` instead.

### 7. npm audit
**Prompt**: "Run npm audit to check for known vulnerabilities"
**Expected**: Does NOT trigger. User wants `npm audit` output, not supply-chain pattern scanning.

### 8. License compliance
**Prompt**: "Check our dependencies for license issues"
**Expected**: Does NOT trigger. Uses `license-compliance` skill instead.

### 9. General code review
**Prompt**: "Review this PR for bugs and code quality"
**Expected**: Does NOT trigger. Uses `code-review` skill instead.

### 10. Dependabot report
**Prompt**: "Show me our Dependabot security alerts"
**Expected**: Does NOT trigger. Uses `github-dependabot-report` skill instead.

## Edge Case Tests

### 11. Binary files in diff
**Prompt**: "Check this PR for supply-chain issues" (PR contains binary files like .wasm, .node)
**Expected**: Skill activates. Notes that binary files cannot be scanned for invisible Unicode but flags their presence as requiring manual review. Focuses detection on text files.

### 12. Monorepo with multiple lockfiles
**Prompt**: "Scan for supply-chain attack patterns" (monorepo with yarn.lock, pnpm-lock.yaml, Cargo.lock)
**Expected**: Skill activates. Checks all lockfiles for anomalies. Cross-references each lockfile against its corresponding manifest (package.json, Cargo.toml).

### 13. False positive — legitimate postinstall
**Prompt**: "Check this package.json for supply-chain issues" (package.json has `postinstall: "husky install"`)
**Expected**: Skill activates. Flags the postinstall hook for review but notes that `husky install` is a common legitimate pattern. Recommends verifying the script content rather than auto-rejecting.

### 14. Combined with code review
**Prompt**: "Review this PR — pay special attention to any supply-chain risks"
**Expected**: Skill activates alongside code-review. Supply-chain checks run in addition to standard review. Both skill outputs are presented.
