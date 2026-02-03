# Dependencies Remediation Guide

## 3rd Party Service Monitoring

### Metrics Integration

**What:** Import metrics from third-party services into your monitoring system.

#### Infura Metrics
```hcl
# CloudWatch custom metric from Infura API
resource "aws_cloudwatch_metric_alarm" "infura_requests" {
  alarm_name          = "infura-request-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "InfuraFailures"
  namespace           = "Custom/Infura"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
}
```

#### Custom Metrics Collection
```typescript
// Wrap third-party calls with metrics
import { metrics } from './metrics';

async function callInfura(method: string, params: unknown[]) {
  const start = Date.now();
  try {
    const result = await infuraClient.request(method, params);
    metrics.recordLatency('infura', Date.now() - start);
    metrics.incrementCounter('infura.success');
    return result;
  } catch (error) {
    metrics.incrementCounter('infura.failure');
    throw error;
  }
}
```

---

### Status Page Integration

**What:** Subscribe to third-party status pages for outage notifications.

#### Slack Integration (Minimum Requirement)
1. Go to the third-party's status page (e.g., status.infura.io)
2. Subscribe to updates via webhook or RSS
3. Create a Slack channel: `#system-{vendor}-status`
4. Configure webhook to post to the channel

#### Example Status Channels
- `#system-infura-status`
- `#system-magic-status`
- `#system-aws-status`

#### Zapier/n8n Integration
```yaml
# n8n workflow example
trigger:
  type: webhook
  path: /statuspage-webhook

actions:
  - type: slack
    channel: "#system-vendor-status"
    message: |
      :warning: *{{ $json.incident.name }}*
      Status: {{ $json.incident.status }}
      Impact: {{ $json.incident.impact }}
      Link: {{ $json.incident.shortlink }}
```

---

### RPC Rate Limits

**What:** Configure appropriate rate limits for blockchain RPC providers.

#### Environment Configuration
```typescript
// config.ts
export const rpcConfig = {
  infura: {
    rateLimit: 10, // requests per second
    burstLimit: 100,
    timeout: 30000,
  },
  alchemy: {
    rateLimit: 25,
    burstLimit: 200,
    timeout: 30000,
  },
};
```

#### Rate-Limited Client
```typescript
import Bottleneck from 'bottleneck';

const limiter = new Bottleneck({
  minTime: 100, // 10 requests per second
  maxConcurrent: 5,
});

async function rpcCall(method: string, params: unknown[]) {
  return limiter.schedule(() => provider.send(method, params));
}
```

#### Fallback Configuration
```typescript
const providers = [
  { url: process.env.INFURA_URL, priority: 1 },
  { url: process.env.ALCHEMY_URL, priority: 2 },
  { url: process.env.QUICKNODE_URL, priority: 3 },
];

async function resilientRpcCall(method: string, params: unknown[]) {
  for (const provider of providers) {
    try {
      return await callProvider(provider.url, method, params);
    } catch (error) {
      console.warn(`Provider ${provider.url} failed, trying next...`);
    }
  }
  throw new Error('All RPC providers failed');
}
```

---

## Service Dependencies Documentation

### Upstream Dependencies

**What:** Document all services and resources your service depends on.

#### Documentation Template
```markdown
# Service Dependencies: [Service Name]

## Upstream Dependencies

### Databases
| Dependency | Type | Criticality | Health Check | Fallback |
|------------|------|-------------|--------------|----------|
| PostgreSQL (RDS) | Primary DB | Critical | `/health` checks DB | None - service fails |
| Redis (ElastiCache) | Cache | High | Redis PING | Bypass cache |

### Internal Services
| Dependency | Purpose | Criticality | Health Check | Fallback |
|------------|---------|-------------|--------------|----------|
| Auth Service | JWT validation | Critical | `/health` | Cached keys |
| Notification Service | Email/Push | Medium | `/health` | Queue retry |

### External Services
| Dependency | Purpose | Criticality | Health Check | Fallback |
|------------|---------|-------------|--------------|----------|
| Infura | Ethereum RPC | High | Request test | Alchemy fallback |
| SendGrid | Email delivery | Medium | Status page | Queue retry |
```

---

### Downstream Dependencies

**What:** Document all services that depend on your service.

#### Documentation Template
```markdown
## Downstream Dependencies

### Services That Depend On Us
| Service | How They Use Us | Impact of Our Outage |
|---------|-----------------|---------------------|
| Web App | API calls | Full outage |
| Mobile App | API calls | Full outage |
| Analytics | Event stream | Data loss |

### Maintenance Windows
- Coordinate with downstream services before planned maintenance
- Notify: #downstream-service-channel
- Contact: @downstream-team
```

---

### Dependency Health in Service Health Endpoint

**What:** Include dependency health status in your health check response.

```typescript
interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  dependencies: DependencyHealth[];
  timestamp: string;
}

interface DependencyHealth {
  name: string;
  status: 'healthy' | 'unhealthy';
  latencyMs?: number;
  error?: string;
}

app.get('/health', async (req, res) => {
  const dependencies: DependencyHealth[] = [];

  // Check database
  const dbStart = Date.now();
  try {
    await db.query('SELECT 1');
    dependencies.push({
      name: 'database',
      status: 'healthy',
      latencyMs: Date.now() - dbStart,
    });
  } catch (error) {
    dependencies.push({
      name: 'database',
      status: 'unhealthy',
      error: error.message,
    });
  }

  // Check Redis
  const redisStart = Date.now();
  try {
    await redis.ping();
    dependencies.push({
      name: 'redis',
      status: 'healthy',
      latencyMs: Date.now() - redisStart,
    });
  } catch (error) {
    dependencies.push({
      name: 'redis',
      status: 'unhealthy',
      error: error.message,
    });
  }

  // Determine overall status
  const unhealthyDeps = dependencies.filter(d => d.status === 'unhealthy');
  const criticalDeps = ['database']; // Define which deps are critical
  const criticalUnhealthy = unhealthyDeps.filter(d => criticalDeps.includes(d.name));

  let status: 'healthy' | 'degraded' | 'unhealthy';
  if (criticalUnhealthy.length > 0) {
    status = 'unhealthy';
  } else if (unhealthyDeps.length > 0) {
    status = 'degraded';
  } else {
    status = 'healthy';
  }

  const statusCode = status === 'unhealthy' ? 503 : 200;
  res.status(statusCode).json({
    status,
    dependencies,
    timestamp: new Date().toISOString(),
  });
});
```

---

### Fallback Behavior

**What:** Define graceful degradation when non-critical dependencies fail.

#### Pattern: Circuit Breaker
```typescript
import CircuitBreaker from 'opossum';

const breaker = new CircuitBreaker(callExternalService, {
  timeout: 3000,
  errorThresholdPercentage: 50,
  resetTimeout: 30000,
});

breaker.fallback(() => {
  // Return cached data or default response
  return getCachedResponse();
});

breaker.on('open', () => {
  console.warn('Circuit breaker opened - using fallback');
});
```

#### Pattern: Cache Fallback
```typescript
async function getDataWithFallback(key: string) {
  try {
    // Try primary source
    const data = await primaryService.get(key);
    await cache.set(key, data, { ttl: 3600 });
    return data;
  } catch (error) {
    // Fall back to cache
    const cached = await cache.get(key);
    if (cached) {
      console.warn('Using cached data due to primary service failure');
      return cached;
    }
    throw error;
  }
}
```

#### Pattern: Graceful Feature Degradation
```typescript
async function getUserProfile(userId: string) {
  const profile = await userService.getProfile(userId);

  // Non-critical: recent activity
  try {
    profile.recentActivity = await activityService.getRecent(userId);
  } catch (error) {
    console.warn('Activity service unavailable, showing empty activity');
    profile.recentActivity = [];
  }

  // Non-critical: recommendations
  try {
    profile.recommendations = await recommendationService.get(userId);
  } catch (error) {
    console.warn('Recommendation service unavailable');
    profile.recommendations = null;
  }

  return profile;
}
```
