# OWASP Top 10 2025 — Category Reference

Per-category grep patterns, semantic checks, and severity guidance. Patterns are starting points — always read context before classifying findings.

---

## A01: Broken Access Control

**Relevance signals**: Any app with routes, endpoints, IAM policies, RBAC, or multi-tenancy.
**Skip when**: Pure library with no auth/access logic.

### Grep Patterns

| Pattern | Glob Filter | What It Finds |
|---------|-------------|---------------|
| `@Public\|@AllowAnonymous\|public.*route\|isPublic` | `*.{ts,js,java,cs,py}` | Explicitly public endpoints |
| `req\.user\|currentUser\|ctx\.user\|request\.user` | `*.{ts,js,py,rb}` | User context access (verify auth check exists) |
| `role\|permission\|authorize\|@Roles\|@HasPermission` | `*.{ts,js,java,cs,py}` | RBAC implementation |
| `cors\|Access-Control-Allow-Origin\|allowedOrigins` | `*.{ts,js,py,json,yaml}` | CORS configuration |
| `admin\|superuser\|root` | `*.{ts,js,py,rb,go}` | Privileged access paths |
| `iam.*policy\|aws_iam\|AssumeRole\|sts:` | `*.{tf,json,yaml}` | IAM policy definitions |
| `"Effect".*"Allow".*"\*"` | `*.{tf,json}` | Overly permissive IAM policies |
| `ssrf\|url.*fetch\|http.*request.*user` | `*.{ts,js,py,go}` | Potential SSRF vectors |

### Semantic Checks

After reading flagged files, answer:
1. Are all non-public routes protected by auth middleware?
2. Is authorization checked per-endpoint or only at gateway?
3. Can users access other users' resources by modifying IDs? (IDOR)
4. Are CORS origins restricted to known domains or set to `*`?
5. Do IAM policies follow least privilege? Any `*` resource/action?
6. Are admin endpoints on a separate path with additional auth?

### Severity Guide

- **Critical**: Missing auth on sensitive endpoints; `*/*` IAM policies in production
- **High**: IDOR potential; CORS allows `*`; admin routes without extra protection
- **Medium**: Overly broad but not wildcard IAM; missing rate limiting on auth
- **Low**: Permissive CORS in dev-only config; minor role granularity gaps

---

## A02: Security Misconfiguration

**Relevance signals**: Any deployable project with config files, environment settings, cloud resources.
**Skip when**: Pure algorithmic library with no deployment artifacts.

### Grep Patterns

| Pattern | Glob Filter | What It Finds |
|---------|-------------|---------------|
| `debug.*true\|DEBUG.*=.*1\|debug_mode\|FLASK_DEBUG` | `*.{py,js,ts,json,yaml,env*}` | Debug mode enabled |
| `default.*password\|admin.*admin\|password.*123` | `*` | Default/weak credentials |
| `0\.0\.0\.0\|0\.0\.0\.0/0\|::/0` | `*.{tf,json,yaml}` | Open network access |
| `ingress.*0\.0\.0\.0\|cidr.*0\.0\.0\.0/0\|from_port.*0.*to_port.*65535` | `*.tf` | Overly permissive security groups |
| `X-Frame-Options\|X-Content-Type\|Strict-Transport\|Content-Security-Policy` | `*.{ts,js,py,conf}` | Security headers (check presence/absence) |
| `encryption.*false\|encrypted.*false\|kms_key.*null` | `*.tf` | Missing encryption at rest |
| `logging.*false\|access_logs.*false\|enable_logging.*false` | `*.{tf,json,yaml}` | Disabled logging |
| `tls_policy\|ssl_policy\|minimum_tls\|TLSv1[^.]` | `*.{tf,json,yaml,conf}` | Weak TLS configuration |
| `versioning.*enabled.*false\|mfa_delete.*false` | `*.tf` | Missing S3 versioning/MFA delete |

### Semantic Checks

1. Are debug/development settings disabled in production configs?
2. Are default credentials changed or removed?
3. Are security groups/firewalls restricted to necessary ports/CIDRs?
4. Is encryption enabled for all data stores and transit?
5. Are security headers configured for web endpoints?
6. Is S3/storage access properly restricted (no public buckets)?

### Severity Guide

- **Critical**: Default admin creds in production; public S3 with sensitive data; 0.0.0.0/0 on DB ports
- **High**: Debug mode in production config; missing encryption at rest; overly permissive SGs
- **Medium**: Missing security headers; TLS 1.0/1.1 allowed; disabled logging
- **Low**: Missing HSTS preload; verbose server headers; non-production misconfig

---

## A03: Supply Chain Failures (NEW in 2025)

**Relevance signals**: Any project with dependencies, CI/CD pipelines, or external scripts.
**Skip when**: Rarely — nearly all projects have dependencies.

### Grep Patterns

| Pattern | Glob Filter | What It Finds |
|---------|-------------|---------------|
| `"latest"\|">=\|"~\|"\^` | `package.json` | Unpinned npm dependencies |
| `>=\|~=\|!=\|==.*\*` | `requirements*.txt` | Unpinned Python dependencies |
| `uses:.*@master\|uses:.*@main\|uses:.*@v[0-9]$` | `.github/workflows/*.{yml,yaml}` | Unpinned GitHub Actions (not SHA-pinned) |
| `curl.*\|.*sh\|wget.*\|.*sh\|bash.*<(curl` | `*.{sh,yml,yaml,Dockerfile*}` | Piped script execution from URLs |
| `integrity=\|crossorigin=` | `*.{html,htm}` | SRI on external scripts (check presence) |
| `npm_config_registry\|--registry\|pip.*--index-url\|--extra-index` | `*.{sh,yml,yaml,Dockerfile*,npmrc,pip.conf}` | Custom package registries |
| `COPY.*requirements\|COPY.*package.*json\|ADD.*http` | `Dockerfile*` | Dependency installation in containers |

Also check for:
- `Glob: *lock*` — verify lock files exist (package-lock.json, yarn.lock, poetry.lock, Cargo.lock, go.sum)
- `Glob: .github/workflows/*` — check all workflow actions are SHA-pinned

### Semantic Checks

1. Do lock files exist and are they committed?
2. Are CI/CD actions pinned to full SHA, not tags/branches?
3. Are external scripts verified before execution (checksums, signatures)?
4. Are dependency sources trusted (no typosquatting-prone names)?
5. Is there a dependency update/review process (Dependabot, Renovate)?
6. Are Docker base images pinned to digest, not just tag?

### Severity Guide

- **Critical**: Piped remote scripts without verification in CI; compromisable CI actions on main
- **High**: Unpinned CI actions using tags; no lock files; custom registries without auth
- **Medium**: Unpinned deps with ranges; missing SRI on CDN scripts; no Dependabot
- **Low**: Using `^` pins (common but less strict); missing `.npmrc` engine-strict

---

## A04: Cryptographic Failures

**Relevance signals**: Any code handling secrets, tokens, passwords, PII, or encrypted data.
**Skip when**: IaC-only repos with no application logic (but check for secrets in IaC).

### Grep Patterns

| Pattern | Glob Filter | What It Finds |
|---------|-------------|---------------|
| `md5\|MD5\|sha1\|SHA1\|sha-1` | `*.{ts,js,py,go,java,rb,rs}` | Weak hash algorithms |
| `DES\|RC4\|Blowfish\|ECB` | `*.{ts,js,py,go,java,rb,rs}` | Weak encryption algorithms |
| `password.*=.*["']\|api_key.*=.*["']\|secret.*=.*["']` | `*.{ts,js,py,go,java,rb,rs,tf}` | Hardcoded secrets |
| `AKIA[A-Z0-9]\|aws_secret\|AWS_SECRET` | `*` | AWS credentials |
| `http://(?!localhost\|127\.0\.0\|0\.0\.0\.0)` | `*.{ts,js,py,go,yaml,json,tf}` | Plaintext HTTP to external services |
| `Math\.random\|random\.random\|rand\(\)` | `*.{ts,js,py,go,rb}` | Non-cryptographic RNG for security use |
| `-----BEGIN.*PRIVATE KEY` | `*` | Embedded private keys |
| `\.pem\|\.key\|\.p12\|\.pfx` | `.gitignore` | Key files in gitignore (check they exist) |

### Semantic Checks

1. Are passwords hashed with bcrypt/scrypt/argon2 (not MD5/SHA1)?
2. Are encryption algorithms current (AES-256-GCM, not DES/RC4)?
3. Is `Math.random()` used where `crypto.randomBytes()` should be?
4. Are secrets in environment variables, not hardcoded?
5. Are private keys excluded from version control?
6. Is TLS used for all external communications?

### Severity Guide

- **Critical**: Hardcoded production secrets; private keys in repo; plaintext password storage
- **High**: MD5/SHA1 for password hashing; HTTP for sensitive data; weak encryption
- **Medium**: Non-crypto RNG in token generation; missing key rotation; HTTP for non-sensitive APIs
- **Low**: SHA1 for non-security checksums; self-signed certs in dev

---

## A05: Injection

**Relevance signals**: Any app accepting user input — web, API, CLI, file parsers.
**Skip when**: IaC-only, pure config repos.

### Grep Patterns

| Pattern | Glob Filter | What It Finds |
|---------|-------------|---------------|
| `query.*\+\|"SELECT.*\+\|"INSERT.*\+\|"UPDATE.*\+\|"DELETE.*\+` | `*.{ts,js,py,go,java,rb}` | SQL string concatenation |
| `\$\{.*\}.*query\|f".*SELECT\|f".*INSERT` | `*.{ts,js,py}` | SQL template literal injection |
| `exec\(\|spawn\(\|system\(\|popen\(\|shell_exec` | `*.{ts,js,py,go,rb,php}` | OS command execution |
| `eval\(\|Function\(\|setTimeout\(.*string\|setInterval\(.*string` | `*.{ts,js}` | JavaScript code injection |
| `innerHTML\|dangerouslySetInnerHTML\|v-html\|\|bypassSecurity` | `*.{ts,js,tsx,jsx,vue,html}` | XSS sinks |
| `\.\.\/\|\.\.\\\\` | `*.{ts,js,py,go,rb}` | Path traversal patterns |
| `render_template_string\|Template\(.*user\|Jinja.*\{\{` | `*.py` | Template injection |
| `xml.*parse\|etree\.parse\|SAXParser\|XMLReader` | `*.{py,java,go}` | XXE potential |
| `deserialize\|pickle\.load\|yaml\.load\|unserialize\|readObject` | `*.{py,java,rb,php}` | Deserialization (also A08) |

### Semantic Checks

1. Is user input parameterized in SQL queries (prepared statements)?
2. Are OS command arguments escaped/validated, not concatenated?
3. Is user-generated content sanitized before DOM insertion?
4. Are file paths validated against traversal (`../`)?
5. Is XML parsing configured to disable external entities?
6. Are template engines used with auto-escaping enabled?

### Severity Guide

- **Critical**: Unparameterized SQL with user input; OS command injection; RCE via deserialization
- **High**: XSS in user-facing pages; path traversal to arbitrary files; XXE
- **Medium**: Template injection with limited scope; SQL injection behind auth
- **Low**: Reflected XSS in admin-only page; path traversal limited to public directory

---

## A06: Insecure Design

**Relevance signals**: Applications with business logic, user workflows, or multi-step processes.
**Skip when**: Libraries, simple CLIs, IaC.

### Grep Patterns

| Pattern | Glob Filter | What It Finds |
|---------|-------------|---------------|
| `rateLimit\|rate_limit\|throttle\|RateLimiter` | `*.{ts,js,py,go,java}` | Rate limiting (check presence) |
| `upload\|multer\|formidable\|multipart` | `*.{ts,js,py,go}` | File upload handling |
| `reset.*password\|forgot.*password\|recovery` | `*.{ts,js,py,go,html}` | Password reset flows |
| `otp\|totp\|2fa\|mfa\|two.factor` | `*.{ts,js,py,go}` | Multi-factor auth (check presence) |
| `captcha\|recaptcha\|hcaptcha\|turnstile` | `*.{ts,js,py,html}` | Bot protection (check presence) |
| `threat.*model\|THREAT\|security.*design` | `*.md` | Threat model documentation |

### Semantic Checks

1. Are rate limits applied to auth endpoints and expensive operations?
2. Do file uploads validate type, size, and content (not just extension)?
3. Are password reset tokens single-use, time-limited, and unpredictable?
4. Is there evidence of threat modeling or security design review?
5. Are business-critical workflows protected against abuse?
6. Are sensitive operations confirmed (email, 2FA) before execution?

### Severity Guide

- **Critical**: No rate limiting on auth + password reset via predictable tokens
- **High**: Unrestricted file upload; password reset without expiry; no abuse controls
- **Medium**: Rate limits only on some endpoints; file upload missing content validation
- **Low**: No documented threat model; captcha missing on public forms

---

## A07: Authentication Failures

**Relevance signals**: Any app with user authentication, sessions, or token-based auth.
**Skip when**: IaC, libraries without auth, CLIs without login.

### Grep Patterns

| Pattern | Glob Filter | What It Finds |
|---------|-------------|---------------|
| `jwt\.verify\|jwt\.decode\|jsonwebtoken\|jose` | `*.{ts,js,py,go}` | JWT handling |
| `jwt\.decode\b(?!.*verify)` | `*.{ts,js,py}` | JWT decode without verify |
| `algorithm.*none\|alg.*none\|HS256` | `*.{ts,js,py,go,json}` | Weak JWT algorithms |
| `session.*secret\|cookie.*secret\|SESSION_SECRET` | `*.{ts,js,py,env*}` | Session configuration |
| `httpOnly\|secure.*cookie\|sameSite\|maxAge\|expires` | `*.{ts,js,py}` | Cookie security settings |
| `bcrypt\|scrypt\|argon2\|pbkdf2` | `*.{ts,js,py,go}` | Password hashing (check presence) |
| `login.*attempt\|failed.*login\|brute.*force\|lockout` | `*.{ts,js,py,go}` | Brute force protection |
| `console\.log.*password\|log.*credential\|print.*token` | `*.{ts,js,py}` | Credential logging |

### Semantic Checks

1. Are JWTs verified with signature validation (not just decoded)?
2. Is the JWT algorithm specified server-side (not from token header)?
3. Are session cookies httpOnly, secure, and sameSite?
4. Are passwords hashed with modern algorithms (bcrypt/argon2)?
5. Is there account lockout or progressive delay after failed logins?
6. Are credentials ever logged or included in error responses?

### Severity Guide

- **Critical**: JWT decode without verify; `alg: none` accepted; credentials in logs
- **High**: Missing httpOnly/secure on auth cookies; no brute force protection; weak password hashing
- **Medium**: Short session expiry missing; HS256 with weak secret; no refresh token rotation
- **Low**: Missing sameSite attribute; session not invalidated on password change

---

## A08: Data Integrity Failures

**Relevance signals**: Apps with CI/CD, external script loading, serialization, or software updates.
**Skip when**: Rarely — check CI/CD at minimum.

### Grep Patterns

| Pattern | Glob Filter | What It Finds |
|---------|-------------|---------------|
| `pickle\.load\|yaml\.load(?!.*Loader)\|unserialize\|readObject` | `*.{py,java,rb,php}` | Unsafe deserialization |
| `<script.*src=.*http\|<link.*href=.*http` | `*.{html,htm,ejs,hbs}` | External scripts without SRI |
| `integrity=\|crossorigin=` | `*.{html,htm}` | SRI presence (verify coverage) |
| `uses:.*@(?!([a-f0-9]{40}))` | `.github/workflows/*.{yml,yaml}` | CI actions not SHA-pinned |
| `GITHUB_TOKEN\|secrets\.\|ACTIONS_` | `.github/workflows/*.{yml,yaml}` | CI secret usage (check scope) |
| `pull_request_target\|workflow_dispatch.*inputs` | `.github/workflows/*.{yml,yaml}` | Dangerous CI triggers |
| `npm publish\|docker push\|twine upload` | `.github/workflows/*.{yml,yaml}` | Artifact publishing (check signing) |

### Semantic Checks

1. Is deserialization of untrusted data avoided or restricted to safe loaders?
2. Do external scripts have Subresource Integrity (SRI) hashes?
3. Are CI/CD pipelines protected against injection via PRs from forks?
4. Are build artifacts signed or verified before deployment?
5. Is `pull_request_target` used safely (no checkout of PR code)?
6. Are CI secrets scoped to minimum necessary?

### Severity Guide

- **Critical**: Unsafe deserialization of user input; CI pipeline RCE via fork PRs
- **High**: External scripts without SRI; pull_request_target with PR code checkout
- **Medium**: CI actions on tags not SHAs; unsigned artifacts; broad CI secret access
- **Low**: Missing SRI on internal CDN; no artifact provenance metadata

---

## A09: Logging & Alerting Failures

**Relevance signals**: Any deployed application or infrastructure.
**Skip when**: Pure libraries (but note if logging guidance is absent).

### Grep Patterns

| Pattern | Glob Filter | What It Finds |
|---------|-------------|---------------|
| `winston\|bunyan\|pino\|log4j\|logging\.\|logrus\|slog\|zap` | `*.{ts,js,py,go,java}` | Logging framework usage |
| `log.*login\|log.*auth\|log.*access\|audit.*log` | `*.{ts,js,py,go,java}` | Auth event logging |
| `log.*password\|log.*secret\|log.*token\|log.*credit` | `*.{ts,js,py,go}` | Sensitive data in logs |
| `console\.log\|print(\|fmt\.Print` | `*.{ts,js,py,go}` | Unstructured logging (non-framework) |
| `alert\|alarm\|notify\|pagerduty\|opsgenie\|cloudwatch.*alarm` | `*.{ts,js,py,go,tf,yaml}` | Alerting configuration |
| `aws_cloudwatch\|aws_cloudtrail\|flow_log\|access_log` | `*.tf` | Cloud logging resources |

### Semantic Checks

1. Is a structured logging framework used (not just console.log)?
2. Are authentication events (login, logout, failure) logged?
3. Are sensitive values (passwords, tokens, PII) excluded from logs?
4. Is there alerting on security-relevant events (failed logins, errors)?
5. Are logs shipped to a centralized system (not just local files)?
6. Are CloudTrail/flow logs enabled for cloud infrastructure?

### Severity Guide

- **Critical**: Credentials/tokens logged in plaintext; no logging on auth events
- **High**: No structured logging framework; sensitive PII in logs; no centralized logging
- **Medium**: Missing alerting on security events; console.log in production; incomplete audit trail
- **Low**: Missing log rotation; no log level configuration; verbose debug logging

---

## A10: Exceptional Conditions (NEW in 2025)

**Relevance signals**: Any application with error handling, external service calls, or resource management.
**Skip when**: Rarely — all code has error handling patterns.

### Grep Patterns

| Pattern | Glob Filter | What It Finds |
|---------|-------------|---------------|
| `catch\s*\(\s*\)\s*\{\s*\}\|except:\s*pass\|catch\s*\{\s*\}` | `*.{ts,js,py,go,java}` | Empty catch blocks |
| `catch.*console\.log\|except.*print\|catch.*\/\/` | `*.{ts,js,py}` | Swallowed exceptions |
| `\.stack\|stackTrace\|traceback` | `*.{ts,js,py,go}` | Stack traces (check not exposed to users) |
| `timeout\|Timeout\|deadline\|context\.WithTimeout` | `*.{ts,js,py,go}` | Timeout configuration |
| `process\.exit\|os\.Exit\|sys\.exit\|panic\(` | `*.{ts,js,py,go}` | Abrupt termination |
| `finally\|defer\|__exit__\|dispose\|cleanup` | `*.{ts,js,py,go}` | Resource cleanup patterns |
| `globalThis.*error\|process\.on.*uncaught\|window\.onerror` | `*.{ts,js}` | Global error handlers |
| `retry\|backoff\|circuit.*breaker` | `*.{ts,js,py,go}` | Resilience patterns (check presence) |

### Semantic Checks

1. Are catch blocks handling errors meaningfully (not swallowing)?
2. Are error responses generic to users but detailed in logs?
3. Are timeouts configured for external service calls?
4. Are resources cleaned up in finally/defer blocks?
5. Is there a global error handler to prevent crashes from leaking info?
6. Are retry/circuit-breaker patterns used for external dependencies?
7. Do errors fail-closed (deny) rather than fail-open (allow)?

### Severity Guide

- **Critical**: Fail-open on auth/authz errors; stack traces with secrets exposed to users
- **High**: Empty catches on security-critical paths; no timeouts on external calls; resource leaks
- **Medium**: Generic swallowed exceptions; missing global error handler; no circuit breakers
- **Low**: Missing finally blocks for non-critical resources; no retry on idempotent operations
