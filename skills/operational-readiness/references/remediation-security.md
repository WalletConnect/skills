# Security Remediation Guide

## OWASP Top 10 2025 Validation

**What:** Validate against industry-standard web application security risks.

**Reference:** https://owasp.org/Top10/2025/

### Key Areas to Validate

1. **A01: Broken Access Control** - Verify authorization on all endpoints
2. **A02: Cryptographic Failures** - Use TLS 1.3, strong encryption
3. **A03: Injection** - Parameterized queries, input validation
4. **A04: Insecure Design** - Threat modeling, secure architecture patterns
5. **A05: Security Misconfiguration** - Secure defaults, hardened configs
6. **A06: Vulnerable Components** - Dependency scanning, SBOM
7. **A07: Authentication Failures** - MFA, rate limiting, secure sessions
8. **A08: Software/Data Integrity** - Code signing, verified updates
9. **A09: Logging/Monitoring Failures** - Security event logging
10. **A10: SSRF** - Validate/sanitize URLs, network segmentation

### Validation Checklist
```markdown
- [ ] All endpoints require authentication (except public routes)
- [ ] Authorization checked at both API and database level
- [ ] All user input validated and sanitized
- [ ] SQL/NoSQL queries use parameterized statements
- [ ] TLS 1.2+ enforced for all connections
- [ ] Secrets encrypted at rest and in transit
- [ ] Dependencies scanned for vulnerabilities
- [ ] Security headers configured (see below)
```

---

## Secure Design Review

**What:** Threat modeling and security architecture review before implementation.

### Threat Modeling Process (STRIDE)
1. **Spoofing** - Can attackers impersonate users/services?
2. **Tampering** - Can data be modified maliciously?
3. **Repudiation** - Can actions be denied without proof?
4. **Information Disclosure** - Can sensitive data leak?
5. **Denial of Service** - Can the service be overwhelmed?
6. **Elevation of Privilege** - Can users gain unauthorized access?

### Documentation Template
```markdown
# Security Design Review: [Service Name]

## Data Flow Diagram
[Include diagram showing data flows and trust boundaries]

## Assets
- User credentials
- API keys
- Business data

## Threat Analysis
| Threat | Category | Mitigation |
|--------|----------|------------|
| SQL injection | Tampering | Parameterized queries |
| Session hijacking | Spoofing | Secure cookies, HTTPS |

## Security Controls
- Authentication: JWT with refresh tokens
- Authorization: RBAC with database-level RLS
- Encryption: TLS 1.3, AES-256 at rest
```

---

## Dependency Scanning & SBOM

**What:** Automated scanning for vulnerable dependencies and software bill of materials.

### GitHub Dependabot
```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10

  - package-ecosystem: "cargo"
    directory: "/"
    schedule:
      interval: "weekly"
```

### GitHub Actions Security Scanning
```yaml
name: Security Scan
on:
  push:
    branches: [main]
  pull_request:

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Snyk
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}

      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          format: spdx-json
          output-file: sbom.spdx.json

      - name: Upload SBOM
        uses: actions/upload-artifact@v3
        with:
          name: sbom
          path: sbom.spdx.json
```

### Cargo Audit (Rust)
```yaml
- name: Security audit
  run: |
    cargo install cargo-audit
    cargo audit
```

---

## Clickjacking Protection (Frontend)

**What:** HTTP headers to prevent UI redressing attacks.

### Next.js Configuration
```javascript
// next.config.js
const securityHeaders = [
  {
    key: 'X-Frame-Options',
    value: 'DENY'
  },
  {
    key: 'Content-Security-Policy',
    value: "frame-ancestors 'none'"
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff'
  },
  {
    key: 'Referrer-Policy',
    value: 'strict-origin-when-cross-origin'
  },
  {
    key: 'Permissions-Policy',
    value: 'camera=(), microphone=(), geolocation=()'
  }
];

module.exports = {
  async headers() {
    return [
      {
        source: '/:path*',
        headers: securityHeaders,
      },
    ];
  },
};
```

**Reference:** https://github.com/WalletConnect/www-walletconnect/blob/main/next.config.js#L11

---

## Email Security (SPF/DKIM)

### SPF Record
```
# DNS TXT record for your domain
v=spf1 include:_spf.google.com include:amazonses.com ~all
```

### DKIM Setup (AWS SES)
```hcl
resource "aws_ses_domain_identity" "main" {
  domain = var.domain
}

resource "aws_ses_domain_dkim" "main" {
  domain = aws_ses_domain_identity.main.domain
}

resource "aws_route53_record" "dkim" {
  count   = 3
  zone_id = var.zone_id
  name    = "${element(aws_ses_domain_dkim.main.dkim_tokens, count.index)}._domainkey"
  type    = "CNAME"
  ttl     = "600"
  records = ["${element(aws_ses_domain_dkim.main.dkim_tokens, count.index)}.dkim.amazonses.com"]
}
```

---

## Row Level Security (Supabase)

**What:** Database-level access control for multi-tenant data.

### Supabase RLS Policies
```sql
-- Enable RLS
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

-- Users can only see their own projects
CREATE POLICY "Users can view own projects"
ON projects FOR SELECT
USING (auth.uid() = user_id);

-- Users can only insert their own projects
CREATE POLICY "Users can insert own projects"
ON projects FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Users can only update their own projects
CREATE POLICY "Users can update own projects"
ON projects FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Users can only delete their own projects
CREATE POLICY "Users can delete own projects"
ON projects FOR DELETE
USING (auth.uid() = user_id);
```

---

## Rate Limiting

**What:** Protect APIs from abuse and DoS attacks.

### Express Rate Limiter
```typescript
import rateLimit from 'express-rate-limit';

const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // Limit each IP to 100 requests per window
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many requests, please try again later.' },
});

app.use('/api/', limiter);
```

### Rust (tower)
```rust
use tower::ServiceBuilder;
use tower_governor::{GovernorConfig, GovernorLayer};

let governor_conf = GovernorConfig::default();

let app = Router::new()
    .route("/api/:path*", get(handler))
    .layer(
        ServiceBuilder::new()
            .layer(GovernorLayer { config: governor_conf })
    );
```

### AWS WAF
```hcl
resource "aws_wafv2_web_acl" "main" {
  name  = "${var.service_name}-waf"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "rate-limit"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "rate-limit"
    }
  }
}
```

---

## Audit Logging

**What:** Log security-relevant events for investigation and compliance.

### Events to Log
- Authentication attempts (success/failure)
- Authorization failures
- Admin actions
- Data access (especially sensitive data)
- Configuration changes
- API key usage

### Implementation
```typescript
interface AuditLog {
  timestamp: string;
  userId: string;
  action: string;
  resource: string;
  outcome: 'success' | 'failure';
  metadata: Record<string, unknown>;
  ipAddress: string;
  userAgent: string;
}

function logAuditEvent(event: AuditLog) {
  // Send to CloudWatch Logs with specific log group
  logger.info({ ...event, type: 'audit' });
}

// Usage
logAuditEvent({
  timestamp: new Date().toISOString(),
  userId: req.user.id,
  action: 'user.delete',
  resource: `user:${targetUserId}`,
  outcome: 'success',
  metadata: { reason: 'account_closure' },
  ipAddress: req.ip,
  userAgent: req.headers['user-agent'],
});
```
