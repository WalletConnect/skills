# Observability Remediation Guide

## Alarmable Top-Level Metric / Canary

**What:** A metric or canary that triggers OpsGenie alerts when the service is unhealthy.

**Why:** We need to be informed **before** customers find out the service has issues.

**Implementation Options:**

### Option 1: Alarmable Metric (for >100 req/min services)
```hcl
# Terraform example - CloudWatch alarm
resource "aws_cloudwatch_metric_alarm" "http_5xx_alarm" {
  alarm_name          = "${var.service_name}-http-5xx"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = 10
  alarm_actions       = [var.opsgenie_sns_topic_arn]
}
```

### Option 2: AWS HealthCheck Canary (for <100 req/min services)
```hcl
resource "aws_route53_health_check" "service_health" {
  fqdn              = var.service_endpoint
  port              = 443
  type              = "HTTPS"
  resource_path     = "/health"
  failure_threshold = 3
  request_interval  = 30
}
```

### Option 3: AWS Synthetics Canary
```hcl
resource "aws_synthetics_canary" "api_canary" {
  name                 = "${var.service_name}-canary"
  artifact_s3_location = "s3://${var.canary_bucket}/canary/"
  execution_role_arn   = var.canary_role_arn
  handler              = "apiCanary.handler"
  zip_file             = var.canary_zip_path
  runtime_version      = "syn-nodejs-puppeteer-3.9"

  schedule {
    expression = "rate(5 minutes)"
  }
}
```

### OpsGenie Integration
1. Create OpsGenie API integration
2. Create SNS topic for alerts
3. Subscribe OpsGenie endpoint to SNS topic
4. Configure alarm actions to publish to SNS

**Reference:** Relay Canary Echo Server HTTP500 alarm

---

## DB/Queue Monitoring

**What:** CloudWatch alarms for CPU, Disk, Memory on databases; In-Flight/Failed messages for queues.

**Implementation:**
```hcl
# RDS CPU alarm
resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${var.db_name}-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_actions       = [var.opsgenie_sns_topic_arn]
  dimensions = {
    DBInstanceIdentifier = var.db_instance_id
  }
}

# SQS Dead Letter Queue alarm
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "${var.queue_name}-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_actions       = [var.opsgenie_sns_topic_arn]
  dimensions = {
    QueueName = var.dlq_name
  }
}
```

---

## Logging Configuration

**What:** Structured logging with appropriate log levels, shipped to a centralized logging system.

### Rust (tracing)
```rust
use tracing::{info, error, instrument};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

fn init_logging() {
    tracing_subscriber::registry()
        .with(tracing_subscriber::fmt::layer().json())
        .with(tracing_subscriber::EnvFilter::from_default_env())
        .init();
}

#[instrument(skip(password))]
async fn login(username: &str, password: &str) -> Result<User, Error> {
    info!(username, "Login attempt");
    // ...
}
```

### TypeScript (pino)
```typescript
import pino from 'pino';

const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  formatters: {
    level: (label) => ({ level: label }),
  },
  timestamp: pino.stdTimeFunctions.isoTime,
});

logger.info({ userId, action: 'login' }, 'User login attempt');
```

**Log retention:** Minimum 1 year specifically for audit/security event logs (auth attempts, authorization decisions, admin actions, data access, configuration changes) per SOC 2 Type 2 compliance. General application logs and error tracking (e.g. Sentry) do not require 1-year retention. Configure audit log groups in CloudWatch Logs:
```hcl
resource "aws_cloudwatch_log_group" "audit_logs" {
  name              = "/ecs/${var.service_name}/audit"
  retention_in_days = 365
}
```

---

## Distributed Tracing

**What:** OpenTelemetry instrumentation for cross-service request tracing.

### Rust
```rust
use opentelemetry::global;
use opentelemetry_sdk::trace::TracerProvider;
use tracing_opentelemetry::OpenTelemetryLayer;

fn init_tracing() {
    let provider = TracerProvider::builder()
        .with_simple_exporter(opentelemetry_jaeger::new_agent_pipeline().build_simple()?)
        .build();
    global::set_tracer_provider(provider);
}
```

### TypeScript
```typescript
import { NodeSDK } from '@opentelemetry/sdk-node';
import { JaegerExporter } from '@opentelemetry/exporter-jaeger';

const sdk = new NodeSDK({
  traceExporter: new JaegerExporter({
    endpoint: process.env.JAEGER_ENDPOINT,
  }),
});
sdk.start();
```

---

## Sentry Instrumentation (Frontend)

**What:** Client-side error tracking with Sentry.

```typescript
import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 0.1,
  beforeSend(event) {
    // Scrub PII if needed
    return event;
  },
});
```

**Alert configuration:** Create Sentry alert rules for error rate thresholds.

---

## status.reown.com Integration

**What:** Public status page showing service health.

**Process:**
1. Contact platform team to add service to status.reown.com
2. Integrate health check endpoint with status page monitoring
3. Configure incident communication workflow
