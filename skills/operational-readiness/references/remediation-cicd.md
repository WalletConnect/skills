# CI/CD & Testing Remediation Guide

## Unit/Functional Tests in CI

**What:** CI workflow that runs tests on every PR with >80% coverage on critical paths.

### GitHub Actions Example (Rust)
```yaml
name: CI
on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - uses: Swatinem/rust-cache@v2

      - name: Run tests
        run: cargo test --all-features

      - name: Generate coverage
        run: |
          cargo install cargo-tarpaulin
          cargo tarpaulin --out Xml --output-dir coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: coverage/cobertura.xml
          fail_ci_if_error: true
          threshold: 80
```

### GitHub Actions Example (TypeScript)
```yaml
name: CI
on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci
      - run: npm test -- --coverage --coverageThreshold='{"global":{"branches":80,"functions":80,"lines":80}}'
```

**Test coverage targets:**
- Critical paths (auth, payments, core business logic): >80%
- Non-happy paths (error handling, edge cases): Explicitly tested
- Integration points: Mocked appropriately

---

## Integration/E2E Tests in CD

**What:** Post-deployment tests that verify the service works in the target environment.

### GitHub Actions Example
```yaml
name: CD
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # ... deployment steps ...

      - name: Run E2E tests
        run: |
          npm run test:e2e
        env:
          API_URL: ${{ secrets.STAGING_API_URL }}

      - name: Smoke test
        run: |
          curl -f ${{ secrets.STAGING_API_URL }}/health || exit 1
```

### Playwright E2E Example (Frontend)
```typescript
import { test, expect } from '@playwright/test';

test('user can login', async ({ page }) => {
  await page.goto('/login');
  await page.fill('[name="email"]', 'test@example.com');
  await page.fill('[name="password"]', 'password');
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL('/dashboard');
});
```

---

## Load Testing

**What:** Simulate production-level traffic to validate performance under load.

**Required for:** Services with >1000 req/min or user-facing services.

### k6 Example
```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 100 },   // Ramp up
    { duration: '5m', target: 100 },   // Stay at peak
    { duration: '2m', target: 200 },   // Spike
    { duration: '2m', target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% of requests under 500ms
    http_req_failed: ['rate<0.01'],    // <1% failure rate
  },
};

export default function () {
  const res = http.get('https://api.example.com/endpoint');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  sleep(1);
}
```

### Run in CI
```yaml
- name: Run load tests
  run: |
    docker run --rm -i grafana/k6 run - < loadtest.js
```

---

## Rollback Procedure

**What:** Documented and tested process to quickly recover from a bad deployment.

### Documentation Template
```markdown
# Rollback Procedure: [Service Name]

## Quick Rollback (< 5 minutes)
1. Go to AWS Console > ECS > [Cluster] > [Service]
2. Click "Update Service"
3. Select previous task definition revision
4. Click "Update"

## CLI Rollback
```bash
# List recent task definitions
aws ecs list-task-definitions --family-prefix myservice --sort DESC

# Update service to previous version
aws ecs update-service \
  --cluster production \
  --service myservice \
  --task-definition myservice:123
```

## Terraform Rollback
```bash
# Revert to previous commit
git revert HEAD
git push

# Or manually set image tag
terraform apply -var="image_tag=v1.2.3"
```

## Verification Steps
1. Check service health: `curl https://api.example.com/health`
2. Verify logs in CloudWatch
3. Check error rates in dashboards
4. Notify team in #incidents

## Escalation
- Primary: @oncall-engineer
- Secondary: @team-lead
- Platform: @platform-team
```

**Testing:** Perform rollback drill quarterly to ensure procedure works.

---

## Post-Deploy Health Checks

**What:** Automated verification that the deployment succeeded.

### GitHub Actions Example
```yaml
- name: Wait for deployment
  run: |
    for i in {1..30}; do
      STATUS=$(curl -s -o /dev/null -w "%{http_code}" ${{ env.API_URL }}/health)
      if [ "$STATUS" = "200" ]; then
        echo "Service is healthy"
        exit 0
      fi
      echo "Waiting for service... (attempt $i)"
      sleep 10
    done
    echo "Service failed to become healthy"
    exit 1

- name: Run smoke tests
  run: npm run test:smoke
  env:
    API_URL: ${{ env.API_URL }}
```

### AWS CodeDeploy with Health Checks
```yaml
# appspec.yml
hooks:
  AfterInstall:
    - location: scripts/health_check.sh
      timeout: 300
      runas: root
```
