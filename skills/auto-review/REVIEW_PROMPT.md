# Main Review Prompt

This mirrors the core review prompt from the `claude/auto-review` action, adapted for a local pre-PR run. Apply it after gathering the diff (see SKILL.md step 1).

## Critical constraints

Be extremely concise; sacrifice grammar for concision. Read-only: no shell commands, builds, or execution. Issues-only: report problems, never praise. If no issues: `✅ No issues found`.

## Review scope

Focus on:

- Code quality / best practices for the project's technologies
- Bugs (especially critical paths, async ops)
- Performance (frontend / backend)
- Security (auth, APIs, data handling)
- Test coverage / quality
- Type safety, error handling, edge cases
- Maintainability / readability

**Diffs alone are not enough.** Read full file(s) to understand context. Code that looks wrong in isolation may be correct given surrounding logic.

## Automated checks

**Only report if violations are found. Skip a check if nothing is detected.**

### PR Size Assessment (check FIRST)

Flag if **>15 files OR >800 lines changed**:

> 🚨 **PR Too Large** **Files:** [N] **Lines:** [N] **Severity:** HIGH **Category:** maintainability
> This PR is doing too much. Suggest 2–4 focused PRs split by (1) logical concern (refactoring vs features vs infra vs deps) and (2) file/directory groupings. Format: "PR 1: [description] - [files]".

### External Domain URLs

Flag URLs to domains other than `reown.com`, `walletconnect.com`, `walletconnect.org`:

> 🔒 **External Domain URL** (Non-blocking) **URL:** [url] **File:** [path:line] — Verify intentional, review security implications.

### Static Resource Cache-Control

Flag static files (`.woff`, `.woff2`, `.ttf`, `.jpg`, `.png`, `.css`, `.js`, `.mp4`, etc.) with `max-age < 31536000` or missing explicit `Cache-Control`:

> ⚠️ **Cache-Control Issue** **Resource:** [url] **File:** [path:line] **Current:** [value] **Recommendation:** "Cache-Control: public, max-age=31536000, immutable"

### GitHub Actions Workflow Security

Scan `.github/workflows/*.y*ml` for:

- **CRITICAL:** `pull_request_target` + PR head checkout (`github.event.pull_request.head.*`) = arbitrary code execution
- **HIGH:** `pull_request_target` + script execution
- **MEDIUM:** Any `pull_request_target` usage (runs with secrets)

> 🚨 **GitHub Actions Security Risk** **Severity:** [level] **File:** [path:line] **Pattern:** [issue] **Recommendation:** [fix]

### WalletConnect Pay Architecture

Flag anti-patterns in payment / wallet / transaction code:

1. **CRITICAL:** Cross-service DB access (imports, queries, connections) → 🚨 Services must use APIs
2. **HIGH:** Missing idempotency keys in POST/PUT/PATCH/DELETE → ⚠️ Extract key, check store, return cached response
3. **HIGH:** External calls without timeout/retry → ⚠️ Add timeout, retry+backoff, circuit breaker
4. **HIGH:** Event consumers (SQS/SNS/Kafka) without message deduplication → ⚠️ Check message ID before mutations
5. **MEDIUM:** Multi-step workflows without saga compensation → ⚠️ Add rollback/compensating events
6. **MEDIUM:** State transitions without trace context → ⚠️ Add structured logging with traceId/correlationId

## Response format

Be concise — ONLY report issues that need fixing. If no issues: `✅ No issues found`. Wrap ALL issues in a collapsed `<details>` section. No praise, issues-only.

````markdown
<details>
<summary>Found N issue(s)</summary>

#### Issue 1: Brief description
**ID:** {file-slug}-{semantic-slug}-{hash}
**File:** path/to/file.ext:123
**Severity:** CRITICAL/HIGH/MEDIUM/LOW
**Category:** security/performance/code_quality/breaking_change

**Context:**
- **Pattern:** What the problematic code pattern is
- **Risk:** Why it's a problem technically
- **Impact:** Potential consequences (exploit, data loss, etc.)
- **Trigger:** Under what conditions this becomes exploitable

**Recommendation:** Fix with minimal code snippet (1–10 lines).
</details>
````

**ID Generation:** `{filename}-{2-4-key-terms}-{SHA256(path+desc).substr(0,4)}` — example: `login-sql-injection-f3a2`.

**Recommendation guidelines:** Include focused code snippets showing the exact fix. DO show specific changes needed. DON'T provide full implementations or boilerplate.

**Rules:** Use "Issue N:" not "#N". Include line numbers. Include code snippets in recommendations.

**Feedback style:** Constructive feedback with specific suggestions. Consider impact on system architecture and user experience. Focus exclusively on problems and their solutions.

### Worked example

````markdown
<details>
<summary>Found 1 issue(s)</summary>

#### Issue 1: SQL injection in user query
**ID:** users-sql-injection-f3a2
**File:** src/database/users.ts:45
**Severity:** HIGH
**Category:** security

**Context:**
- **Pattern:** Query at line 45 builds SQL via string concatenation with user-provided `userId`
- **Risk:** Allows arbitrary SQL injection via crafted input (e.g., `1' OR '1'='1`)
- **Impact:** Unauthorized data access, modification, or database destruction
- **Trigger:** Any endpoint accepting user input that reaches this query

**Recommendation:** Use parameterized queries:
```typescript
const result = await db.query('SELECT * FROM users WHERE id = $1', [userId]);
```
</details>
````
