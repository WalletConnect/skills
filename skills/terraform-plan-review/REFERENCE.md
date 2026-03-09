# Terraform Plan Review — Reference

## Plan Output Patterns

### Resource Action Indicators

| Symbol | Meaning | Regex Pattern |
|--------|---------|---------------|
| `+` | Create | `^\s*#.*will be created` |
| `~` | Update in-place | `^\s*#.*will be updated in-place` |
| `-` | Destroy | `^\s*#.*will be destroyed` |
| `-/+` | Replace (destroy then create) | `must be replaced` or `forces replacement` |
| `+/-` | Replace (create before destroy) | `create_before_destroy` |
| `<=` | Read (data source) | `^\s*#.*will be read` |

### Summary Line

```
Plan: X to add, Y to change, Z to destroy.
```

Regex: `Plan:\s*(\d+)\s*to add,\s*(\d+)\s*to change,\s*(\d+)\s*to destroy`

No-change: `No changes. Infrastructure is up-to-date.` or `No changes. Your infrastructure matches the configuration.`

### Force-Replacement Markers

Lines containing `# forces replacement` indicate an attribute change that requires resource recreation. Common triggers:

| Resource Type | Attribute | Why |
|---|---|---|
| `aws_instance` | `ami`, `instance_type` (some), `subnet_id` | Immutable instance properties |
| `aws_launch_template` | `image_id` | New AMI requires new template |
| `aws_db_instance` | `engine`, `username`, `identifier` | Engine/identity changes need recreation |
| `aws_s3_bucket` | `bucket` (name) | Bucket names are globally unique, immutable |
| `aws_iam_role` | `name` | Role name is immutable |
| `aws_lambda_function` | `function_name` | Function name is immutable |
| `google_compute_instance` | `name`, `machine_type`, `boot_disk` | Core instance properties |
| `google_sql_database_instance` | `name`, `database_version` | Instance identity |
| `azurerm_resource_group` | `location` | Region is immutable |

## High-Risk Resource Types

### Stateful / Data-Bearing (Destruction = Data Loss)

**AWS:**
- `aws_db_instance`, `aws_rds_cluster` — relational databases
- `aws_dynamodb_table` — NoSQL tables
- `aws_s3_bucket` — object storage (check if non-empty)
- `aws_ebs_volume`, `aws_efs_file_system` — block/file storage
- `aws_elasticache_cluster`, `aws_elasticache_replication_group` — cache with data
- `aws_kinesis_stream` — streaming data
- `aws_sqs_queue` — messages in flight
- `aws_secretsmanager_secret` — stored secrets
- `aws_kms_key` — encryption keys (destruction = data irrecoverable)

**GCP:**
- `google_sql_database_instance` — Cloud SQL
- `google_storage_bucket` — GCS
- `google_bigtable_instance` — Bigtable
- `google_redis_instance` — Memorystore
- `google_kms_crypto_key` — encryption keys
- `google_secret_manager_secret` — stored secrets

**Azure:**
- `azurerm_mssql_database`, `azurerm_postgresql_flexible_server` — databases
- `azurerm_storage_account` — blob/table/queue storage
- `azurerm_key_vault` — secrets and keys

### Networking (Changes = Connectivity/Exposure Risk)

- `aws_security_group`, `aws_security_group_rule` — firewall rules
- `aws_vpc`, `aws_subnet`, `aws_route_table` — network topology
- `aws_lb`, `aws_lb_listener`, `aws_lb_target_group` — load balancer config
- `aws_nat_gateway`, `aws_internet_gateway` — internet access
- `google_compute_firewall` — GCP firewall
- `google_compute_network`, `google_compute_subnetwork` — GCP VPC
- `azurerm_network_security_group` — Azure NSG

### IAM / Access Control (Changes = Permission Escalation Risk)

- `aws_iam_role`, `aws_iam_policy`, `aws_iam_role_policy` — IAM definitions
- `aws_iam_role_policy_attachment` — policy bindings
- `aws_iam_user`, `aws_iam_group` — identity resources
- `google_project_iam_member`, `google_project_iam_binding` — GCP IAM
- `google_service_account` — GCP service accounts
- `azurerm_role_assignment`, `azurerm_role_definition` — Azure RBAC

### DNS / Certificates (Changes = Availability Risk)

- `aws_route53_record`, `aws_route53_zone` — DNS
- `aws_acm_certificate` — TLS certificates
- `google_dns_record_set`, `google_dns_managed_zone` — GCP DNS
- `cloudflare_record` — Cloudflare DNS

## Common Drift Causes

| Cause | Symptoms in Plan |
|---|---|
| Manual console changes | Resources show updates not in code diff |
| Provider version bump | New default values, changed attribute schemas |
| Data source refresh | Data source outputs changed, downstream resources update |
| Module version update | Transitive resource changes from updated module |
| External automation | Changes made by other IaC pipelines or scripts |
| Default value changes | Provider or AWS service changed defaults |
| Implicit dependencies | Resource B changes because resource A's output changed |
| State file drift | State doesn't match reality (manual `terraform state` ops) |

## Risk Level Classification

### High Risk

- Destruction or replacement of any stateful/data-bearing resource
- IAM policy with `"Action": "*"` or `"Resource": "*"`
- Security group allowing `0.0.0.0/0` on sensitive ports
- KMS key deletion or disabling
- Route table changes affecting production subnets
- Force-replacement of resources with `prevent_destroy` lifecycle (will error, but indicates intent mismatch)
- Multiple unexpected changes with no code diff

### Medium Risk

- New IAM policies with bounded scope
- Security group changes with specific CIDR ranges
- Scaling changes (instance size, count, capacity)
- Load balancer listener or target group modifications
- DNS record changes
- Certificate replacements
- Unexpected changes traceable to provider/module updates

### Low Risk

- Tag-only changes
- Output value changes
- Description or name tag updates
- New resources that are purely additive
- Terraform provider or backend config changes
- Variable default value adjustments
- Comment-only code changes reflected in plan
