# Infrastructure Primitives Remediation Guide

## Runbook Documentation

**What:** Comprehensive documentation for operating the service.

### Runbook Template
```markdown
# Runbook: [Service Name]

## Service Overview
- **Purpose:** [What the service does]
- **Owner:** [Team/Individual]
- **Slack:** #team-channel
- **On-call:** [PagerDuty/OpsGenie rotation]

## Architecture
[Diagram or description of service components]

## Common Failure Modes

### High CPU Usage
**Symptoms:** Response times increase, health checks timeout
**Diagnosis:**
1. Check CloudWatch CPU metrics
2. Check for runaway processes: `top` or `htop`
3. Check for memory leaks causing GC pressure

**Resolution:**
1. Scale up instances: `aws ecs update-service --desired-count 4`
2. Identify and fix the root cause
3. Deploy fix

### Database Connection Exhaustion
**Symptoms:** "too many connections" errors in logs
**Diagnosis:**
1. Check RDS connection count metric
2. Check for connection leaks in application

**Resolution:**
1. Restart affected tasks (drains connections)
2. Increase max_connections if needed
3. Implement connection pooling

### Out of Disk Space
**Symptoms:** Write failures, service crashes
**Diagnosis:**
1. Check EBS volume metrics
2. Identify large files: `du -sh /*`

**Resolution:**
1. Clear log files: `truncate -s 0 /var/log/app.log`
2. Expand EBS volume
3. Configure log rotation

## Troubleshooting Steps
1. Check service health: `curl https://service.example.com/health`
2. Check logs: CloudWatch Logs > /ecs/[service-name]
3. Check metrics: CloudWatch Dashboards > [service-dashboard]
4. Check dependencies: [list of dependent services and their health endpoints]

## Escalation Contacts
- L1: On-call engineer (OpsGenie)
- L2: Team lead (@team-lead)
- L3: Platform team (#platform-support)

## Recovery Procedures
### Full Service Restart
```bash
aws ecs update-service --cluster prod --service myservice --force-new-deployment
```

### Database Failover
[Steps specific to your DB setup]
```

---

## Infrastructure as Code

**What:** All infrastructure defined in Terraform or CDK - no manual console changes.

### Terraform Structure
```
terraform/
├── environments/
│   ├── prod/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   └── staging/
├── modules/
│   ├── ecs-service/
│   ├── rds/
│   └── alb/
└── README.md
```

### CDK Structure
```
cdk/
├── bin/
│   └── app.ts
├── lib/
│   ├── service-stack.ts
│   └── database-stack.ts
├── cdk.json
└── package.json
```

**Anti-patterns to avoid:**
- Manual console changes (use `terraform import` if needed)
- Hardcoded values (use variables)
- Secrets in code (use AWS Secrets Manager)

---

## Autoscaling Configuration

**What:** Automatic scaling based on metrics to handle traffic spikes.

### ECS Service Autoscaling (Terraform)
```hcl
resource "aws_appautoscaling_target" "ecs" {
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "service/${var.cluster_name}/${var.service_name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "${var.service_name}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
```

---

## Health Check Endpoint

**What:** Endpoint that verifies service health including dependencies.

### Rust (Axum)
```rust
use axum::{routing::get, Json, Router};
use serde::Serialize;

#[derive(Serialize)]
struct HealthResponse {
    status: &'static str,
    checks: Vec<HealthCheck>,
}

#[derive(Serialize)]
struct HealthCheck {
    name: &'static str,
    status: &'static str,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<String>,
}

async fn health_check(State(state): State<AppState>) -> Json<HealthResponse> {
    let mut checks = vec![];

    // Database check
    let db_status = match state.db.ping().await {
        Ok(_) => HealthCheck { name: "database", status: "healthy", error: None },
        Err(e) => HealthCheck { name: "database", status: "unhealthy", error: Some(e.to_string()) },
    };
    checks.push(db_status);

    // Redis check
    let redis_status = match state.redis.ping().await {
        Ok(_) => HealthCheck { name: "redis", status: "healthy", error: None },
        Err(e) => HealthCheck { name: "redis", status: "unhealthy", error: Some(e.to_string()) },
    };
    checks.push(redis_status);

    let all_healthy = checks.iter().all(|c| c.status == "healthy");

    Json(HealthResponse {
        status: if all_healthy { "healthy" } else { "unhealthy" },
        checks,
    })
}
```

### TypeScript (Express)
```typescript
app.get('/health', async (req, res) => {
  const checks = [];

  // Database check
  try {
    await db.query('SELECT 1');
    checks.push({ name: 'database', status: 'healthy' });
  } catch (error) {
    checks.push({ name: 'database', status: 'unhealthy', error: error.message });
  }

  // Redis check
  try {
    await redis.ping();
    checks.push({ name: 'redis', status: 'healthy' });
  } catch (error) {
    checks.push({ name: 'redis', status: 'unhealthy', error: error.message });
  }

  const allHealthy = checks.every(c => c.status === 'healthy');
  res.status(allHealthy ? 200 : 503).json({
    status: allHealthy ? 'healthy' : 'unhealthy',
    checks,
  });
});
```

---

## Multi-AZ Deployment

**What:** Run at least 2 instances across availability zones for high availability.

### Terraform ECS Configuration
```hcl
resource "aws_ecs_service" "main" {
  name            = var.service_name
  cluster         = var.cluster_id
  task_definition = aws_ecs_task_definition.main.arn
  desired_count   = 2  # Minimum 2 for HA

  deployment_configuration {
    minimum_healthy_percent = 50
    maximum_percent         = 200
  }

  network_configuration {
    subnets = var.private_subnet_ids  # Multiple AZs
    security_groups = [var.security_group_id]
  }
}
```

---

## Secrets Management

**What:** Store secrets in AWS Secrets Manager or similar - never in code or env vars.

### Terraform Secrets Manager
```hcl
resource "aws_secretsmanager_secret" "db_credentials" {
  name = "${var.service_name}/db-credentials"
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
  })
}
```

### ECS Task Definition with Secrets
```hcl
resource "aws_ecs_task_definition" "main" {
  # ...
  container_definitions = jsonencode([{
    name = var.service_name
    secrets = [
      {
        name      = "DB_PASSWORD"
        valueFrom = aws_secretsmanager_secret.db_credentials.arn
      }
    ]
  }])
}
```

### Application Code (Rust)
```rust
use aws_sdk_secretsmanager::Client;

async fn get_secret(client: &Client, secret_name: &str) -> Result<String, Error> {
    let response = client
        .get_secret_value()
        .secret_id(secret_name)
        .send()
        .await?;

    Ok(response.secret_string().unwrap().to_string())
}
```

**Anti-patterns to avoid:**
- Secrets in `.env` files committed to git
- Secrets in environment variables in task definitions
- Hardcoded secrets in code
