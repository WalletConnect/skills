# AWS Service Limits Reference

Quick reference for AWS service quotas that commonly cause production issues. Organized by service.

**Legend**:
- **Hard** = Cannot be increased
- **Soft** = Can request increase via Service Quotas console
- **Default** = Starting value, may vary by account age/region

---

## Lambda

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Execution timeout | 15 minutes (900s) | Hard | Use Step Functions for longer workflows |
| Sync invoke payload | 6 MB | Hard | Use S3 for larger payloads |
| Async invoke payload | 256 KB | Hard | |
| Concurrent executions | 1,000/region | Soft | New accounts may have lower limits |
| Function memory | 128 MB - 10,240 MB | Hard | |
| Deployment package (zip) | 50 MB (250 MB unzipped) | Hard | Use container images for larger |
| Container image size | 10 GB | Hard | |
| /tmp storage | 512 MB - 10,240 MB | Hard | |
| Environment variables | 4 KB total | Hard | |
| Layers per function | 5 | Hard | |
| Versions per function | 75 | Soft | |
| ENIs per function (VPC) | 250 | Soft | Can exhaust VPC ENI quota |
| Burst concurrency | 500-3000 (varies by region) | Hard | |

**Docs**: https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html

---

## API Gateway

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Integration timeout (REST) | 29 seconds | Soft | Can increase for Regional/Private APIs |
| Integration timeout (HTTP) | 30 seconds | Hard | |
| Throttle (account/region) | 10,000 RPS | Soft | |
| Burst limit | 5,000 requests | Hard | Cannot be changed |
| WebSocket connections | 500 | Soft | Per API, per stage |
| Payload size | 10 MB | Hard | |
| Routes per API | 300 | Soft | |
| APIs per region | 600 | Soft | |
| Stages per API | 10 | Soft | |
| API keys per account | 10,000 | Soft | |

**Docs**: https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html

---

## S3

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| PUT/POST/DELETE per prefix | 3,500 RPS | Soft | Auto-scales, but spike causes 503 |
| GET/HEAD per prefix | 5,500 RPS | Soft | Auto-scales, but spike causes 503 |
| Object size | 5 TB | Hard | |
| Single PUT size | 5 GB | Hard | Use multipart for larger |
| Multipart minimum | 5 MB per part (except last) | Hard | |
| Buckets per account | 100 | Soft | |
| Object key length | 1,024 bytes | Hard | |
| Metadata per object | 2 KB | Hard | |
| Tags per object | 10 | Hard | |
| Lifecycle rules per bucket | 1,000 | Hard | |

**Docs**: https://docs.aws.amazon.com/AmazonS3/latest/userguide/optimizing-performance.html

---

## DynamoDB

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Item size | 400 KB | Hard | Including attribute names |
| Partition throughput | 3,000 RCU / 1,000 WCU | Hard | Per partition |
| GSI per table | 20 | Soft | |
| LSI per table | 5 | Hard | Must be created at table creation |
| Projected attributes (GSI) | 100 | Hard | |
| Tables per region | 2,500 | Soft | |
| On-demand burst capacity | 2x previous peak | Hard | Within 30 min window |
| Transaction items | 100 | Hard | Per TransactWriteItems/TransactGetItems |
| Batch items | 25 (write) / 100 (get) | Hard | |
| Query/Scan result | 1 MB | Hard | Use pagination |
| Attribute name length | 64 KB | Hard | |
| Table name length | 255 chars | Hard | |

**Docs**: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ServiceQuotas.html

---

## SQS

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Message size | 256 KB | Hard | Use S3 for larger |
| In-flight messages (Standard) | 120,000 | Hard | Per queue |
| In-flight messages (FIFO) | 20,000 | Hard | Per queue |
| Message retention | 14 days max | Hard | |
| Visibility timeout | 12 hours max | Hard | |
| Delay seconds | 15 minutes max | Hard | |
| Long polling wait | 20 seconds max | Hard | |
| Batched messages | 10 | Hard | Per SendMessageBatch |
| FIFO throughput | 300 msg/s (3,000 with batching) | Hard | Per queue, without high throughput |
| FIFO high throughput | 70,000 msg/s | Hard | Per queue |
| Message groups (FIFO) | No limit | - | But ordering is per group |

**Docs**: https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-quotas.html

---

## SNS

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Topics per account | 100,000 | Soft | |
| Subscriptions per topic | 12,500,000 | Soft | |
| Message size | 256 KB | Hard | |
| Filter policies per topic | 200 | Soft | |
| Filter policy size | 150 KB | Hard | |
| Publish requests | 30,000/s (varies by region) | Soft | |
| SMS spending | $1/month default | Soft | Must request increase |

**Docs**: https://docs.aws.amazon.com/general/latest/gr/sns.html

---

## Step Functions

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Execution history events | 25,000 | Hard | Use child executions for longer |
| Execution duration (Standard) | 1 year | Hard | |
| Execution duration (Express) | 5 minutes | Hard | |
| State machine definition | 1 MB | Hard | |
| Input/output per state | 256 KB | Hard | |
| Execution name length | 80 chars | Hard | |
| Concurrent executions | 1,000,000 | Soft | |
| Map state concurrency | 40 (inline) | Hard | Use Distributed Map for more |
| Distributed Map concurrency | 10,000 | Hard | |
| Activity pollers per ARN | 1,000 | Hard | |
| Sync execution payload | 256 KB | Hard | |

**Docs**: https://docs.aws.amazon.com/step-functions/latest/dg/service-quotas.html

---

## ECS/Fargate

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Tasks per service | 5,000 | Hard | |
| Services per cluster | 5,000 | Soft | |
| Clusters per region | 10,000 | Soft | |
| Container instances per cluster | 5,000 | Soft | |
| Task definition size | 64 KB | Hard | |
| Containers per task | 10 | Hard | |
| Task CPU (Fargate) | 16 vCPU max | Hard | |
| Task memory (Fargate) | 120 GB max | Hard | |
| Ephemeral storage (Fargate) | 200 GB max | Hard | Default 20 GB |
| Secrets per task | 100 | Hard | Including env vars from Secrets Manager |

**Docs**: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-quotas.html

---

## ALB/NLB (Elastic Load Balancing)

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Load balancers per target group | 5 | Hard | **Common production issue** |
| Target groups per ALB | 100 | Soft | |
| Targets per target group | 1,000 | Soft | |
| Targets per ALB | 1,000 | Hard | Across all target groups |
| Rules per ALB | 100 | Soft | Plus default rule |
| Conditions per rule | 5 | Hard | |
| Actions per rule | 5 | Hard | |
| Listeners per ALB | 50 | Soft | |
| Certificates per ALB | 25 | Soft | Plus default |
| Target groups per action (weighted) | 5 | Hard | For weighted routing |
| ALBs per region | 50 | Soft | |
| NLBs per region | 50 | Soft | |

**Docs**: https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-limits.html

---

## CloudWatch

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Alarms per region | No limit | - | But charged per alarm |
| Metrics per alarm | 10 | Hard | For metric math |
| Dashboards per account | 5,000 | Soft | |
| Widgets per dashboard | 500 | Hard | |
| Metrics per widget | 500 | Hard | |
| Metrics per dashboard | 2,500 | Hard | Across all widgets |
| PutMetricData requests | 1,000 datapoints/request | Hard | |
| GetMetricData TPS | 50 (no Insights) / 10 (with Insights) | Soft | |
| Metric retention (high-res) | 3 hours | Hard | Then aggregated |
| Metric retention (1-min) | 15 days | Hard | |
| Metric retention (5-min) | 63 days | Hard | |
| Metric retention (1-hour) | 15 months | Hard | |
| Log group name length | 512 chars | Hard | |
| Log event size | 256 KB | Hard | |

**Docs**: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_limits.html

---

## Cognito

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| User pools per region | 1,000 | Soft | |
| Users per user pool | 40,000,000 | Soft | |
| Groups per user pool | 10,000 | Hard | |
| Groups per user | 100 | Hard | |
| Identity providers per pool | 300 | Soft | |
| UserAuthentication RPS | 120 | Soft | **Common throttling issue** |
| UserCreation RPS | 50 | Soft | |
| UserRead RPS | 120 | Soft | |
| Custom attributes | 50 | Hard | |
| Attribute name length | 256 chars | Hard | |
| App clients per pool | 1,000 | Soft | |
| Resource servers per pool | 25 | Soft | |

**Docs**: https://docs.aws.amazon.com/cognito/latest/developerguide/quotas.html

---

## Secrets Manager

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Secrets per region | 500,000 | Soft | |
| Secret value size | 64 KB | Hard | |
| Secret versions | ~100 (labeled) | - | Unlabeled versions cleaned up |
| Labels per version | 20 | Hard | |
| GetSecretValue RPS | 10,000 | Soft | Per region |
| Rotation Lambda timeout | Must complete quickly | - | Default Lambda limits apply |

**Docs**: https://docs.aws.amazon.com/secretsmanager/latest/userguide/reference_limits.html

---

## EventBridge

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Rules per event bus | 300 | Soft | |
| Targets per rule | 5 | Hard | |
| Event buses per account | 100 | Soft | |
| Invocations per second | 10,000 (varies) | Soft | Per region |
| PutEvents entries | 10 | Hard | Per request |
| Event size | 256 KB | Hard | |
| Archive retention | 1 day to indefinite | - | |

**Docs**: https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-quota.html

---

## RDS

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| DB instances per region | 40 | Soft | |
| Read replicas per instance | 15 (Aurora) / 5 (others) | Hard | |
| Manual snapshots per region | 100 | Soft | |
| Storage per instance | 64 TB (most engines) | Hard | |
| Parameter groups per region | 50 | Soft | |
| Option groups per region | 20 | Soft | |
| Security groups per instance | 5 | Soft | |
| Subnet groups per region | 50 | Soft | |
| Subnets per subnet group | 20 | Hard | |
| Tags per resource | 50 | Hard | |
| Connections (varies by instance) | Instance-dependent | Hard | Based on memory |

**Docs**: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Limits.html

---

## VPC

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| VPCs per region | 5 | Soft | |
| Subnets per VPC | 200 | Soft | |
| IPv4 CIDR blocks per VPC | 5 | Soft | |
| IPv6 CIDR blocks per VPC | 5 | Hard | |
| Route tables per VPC | 200 | Soft | |
| Routes per route table | 50 | Soft | |
| Security groups per VPC | 2,500 | Soft | |
| Rules per security group | 60 inbound + 60 outbound | Soft | |
| Security groups per ENI | 5 | Soft | |
| Network ACLs per VPC | 200 | Soft | |
| Rules per ACL | 20 | Soft | |
| Elastic IPs per region | 5 | Soft | |
| NAT Gateways per AZ | 5 | Soft | |
| VPC Endpoints per region | 50 | Soft | |
| VPC Peering connections | 50 active | Soft | |

**Docs**: https://docs.aws.amazon.com/vpc/latest/userguide/amazon-vpc-limits.html

---

## IAM

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Users per account | 5,000 | Soft | |
| Groups per account | 300 | Soft | |
| Roles per account | 1,000 | Soft | |
| Managed policies per account | 1,500 | Soft | |
| Policies per user/role/group | 10 | Soft | |
| Inline policy size | 2,048 chars | Hard | |
| Managed policy size | 6,144 chars | Hard | |
| Role trust policy size | 2,048 chars | Hard | |
| Groups per user | 10 | Hard | |
| Access keys per user | 2 | Hard | |
| MFA devices per user | 8 | Hard | |
| Instance profiles per account | 1,000 | Soft | |
| SAML providers per account | 100 | Hard | |
| OIDC providers per account | 100 | Soft | |

**Docs**: https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_iam-quotas.html

---

## CloudFormation

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Stacks per region | 2,000 | Soft | |
| Stack sets per account | 100 | Soft | |
| Resources per stack | 500 | Hard | |
| Outputs per stack | 200 | Hard | |
| Parameters per stack | 200 | Hard | |
| Mappings per template | 200 | Hard | |
| Template size (S3) | 1 MB | Hard | |
| Template size (direct) | 51,200 bytes | Hard | |
| Nested stack depth | 5 | Hard | |

**Docs**: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cloudformation-limits.html

---

## KMS

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| CMKs per region | 100,000 | Soft | |
| Aliases per CMK | 50 | Hard | |
| Grants per CMK | 50,000 | Hard | |
| Cryptographic operations | 5,500-30,000 RPS | Soft | Varies by key type/region |
| Symmetric operations | 50,000-100,000+ RPS | Soft | Shared across account |
| RSA operations | 500-2,000 RPS | Soft | |
| ECC operations | 300-1,000 RPS | Soft | |

**Docs**: https://docs.aws.amazon.com/kms/latest/developerguide/limits.html

---

## Aurora

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| DB instances (shared with RDS) | 40 | Soft | Across RDS, Aurora, Neptune, DocumentDB |
| Read replicas per cluster | 15 | Hard | |
| Max connections | Instance-dependent | Hard | Based on memory; T2/T3 much lower |
| Table size (MySQL) | 64 TiB | Hard | |
| Table size (PostgreSQL) | 32 TiB | Hard | |
| Cluster identifier length | 63 chars | Hard | |
| Parameter groups per region | 50 | Soft | |
| Cluster parameter groups | 50 | Soft | |
| Serverless v2 max_connections | Capped at 2,000 | Hard | When min ACU is 0 or 0.5 |
| Storage auto-scaling max | 128 TiB | Hard | |

**Docs**: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/CHAP_Limits.html

---

## Athena

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Active DML queries | 200 (us-east-1) / 20 (other) | Soft | **Common throttling issue** |
| Active DDL queries | 20 | Soft | |
| Query timeout | 30 minutes | Hard | |
| Query result size | Unlimited | - | But S3 storage costs apply |
| Workgroups per account | 1,000 | Soft | |
| Prepared statements per workgroup | 1,000 | Hard | |
| Tags per workgroup | 50 | Hard | |
| Capacity reservation min DPUs | 24 | Hard | |
| Workgroups per reservation | 20 | Hard | |
| DPUs per DML query | 4-124 (auto) | Hard | DDL uses 4 DPUs |

**Docs**: https://docs.aws.amazon.com/athena/latest/ug/service-limits.html

---

## Glue

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Concurrent job runs per account | 50 | Soft | **Common limit** |
| Max concurrent job runs per job | Configurable | Soft | MaxConcurrentRuns parameter |
| DPUs per job | 2 min, 10 default | - | Python shell: 0.0625 or 1 |
| Job timeout | 2,880 min default | Hard | Max 7 days (10,080 min) |
| Crawlers per account | 1,000 | Soft | |
| Jobs per account | 1,000 | Soft | |
| Triggers per account | 1,000 | Soft | |
| Development endpoints | 25 | Soft | |
| Job queue timeout | 15 min or 10 retries | Hard | For job queuing feature |
| ENIs per job | Equal to DPUs | Hard | Consumes VPC IP addresses |

**Docs**: https://docs.aws.amazon.com/glue/latest/dg/troubleshooting-service-limits.html

---

## ElastiCache (Redis)

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Nodes per region | 300 | Soft | |
| Nodes per cluster | 250 | Hard | Including shards |
| Shards per cluster | 250 | Hard | |
| Replicas per shard | 5 | Hard | |
| Connections per node | 65,000 | Hard | maxclients not modifiable |
| Parameter groups per region | 150 | Soft | |
| Subnet groups per region | 150 | Soft | |
| Subnets per subnet group | 20 | Soft | |
| Security groups per cluster | 1 | Hard | |
| Serverless max connections | 65,000 | Hard | |

**Docs**: https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/quota-limits.html

---

## DocumentDB

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| DB instances (shared) | 40 | Soft | Shared with RDS/Aurora/Neptune |
| Instances per cluster | 16 | Hard | 1 primary + 15 replicas |
| Connections per instance | 4,500 max | Hard | Varies by instance type |
| Open cursors per instance | 450 | Hard | Varies by instance type |
| Storage per cluster | 128 TiB | Hard | |
| Clusters per region | 40 | Soft | |
| Cluster parameter groups | 50 | Soft | |
| Manual snapshots | 100 | Soft | |
| Elastic cluster shards | 32 | Hard | |
| DCU per shard | 2 GiB memory each | - | |

**Docs**: https://docs.aws.amazon.com/documentdb/latest/developerguide/limits.html

---

## Kinesis Data Streams

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Shards per region | 20,000 (us-east-1) / 1,000-6,000 (other) | Soft | Recently increased |
| Write throughput per shard | 1 MB/s, 1,000 records/s | Hard | |
| Read throughput per shard | 2 MB/s | Hard | |
| Read transactions per shard | 5/s | Hard | GetRecords limit |
| Record size | 1 MB | Hard | Before base64 encoding |
| Data retention | 24 hours default | Soft | Up to 365 days |
| GetRecords per call | 10,000 records / 10 MB | Hard | |
| Enhanced fan-out consumers | 20 | Soft | Per stream |
| On-demand streams per account | 50 | Soft | |
| On-demand write capacity | 200 MB/s, 200K records/s | Hard | Auto-scales to 2x peak |

**Docs**: https://docs.aws.amazon.com/streams/latest/dev/service-sizes-and-limits.html

---

## Kinesis Data Firehose

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Delivery streams per region | 5,000 (us-east-1) / 2,000 (other) | Soft | |
| Direct PUT throughput | 5 MB/s (us-east-1) / 1 MB/s (other) | Soft | |
| Direct PUT records | 500,000/s (us-east-1) / 100,000/s (other) | Soft | |
| Direct PUT requests | 2,000/s (us-east-1) / 1,000/s (other) | Soft | |
| Record size | 1,000 KB | Hard | Before base64 |
| PutRecordBatch | 500 records / 4 MB | Hard | Per request |
| Buffer interval | 60-900 seconds | Hard | |
| Dynamic partitions | 500 active | Soft | |
| Retry duration (Redshift/OpenSearch) | 0-7,200 seconds | Hard | |
| Data retention (DirectPut unavailable) | 24 hours | Hard | |

**Docs**: https://docs.aws.amazon.com/firehose/latest/dev/limits.html

---

## EFS

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| File systems per account | 1,000 | Soft | |
| Connections per file system | 25,000 | Hard | |
| Access points per file system | 120 | Hard | |
| Mount targets per file system per AZ | 1 | Hard | |
| Mount targets per VPC | 400 | Hard | |
| Security groups per mount target | 5 | Hard | |
| File size max | 47.9 TiB | Hard | |
| Directory depth | 1,000 levels | Hard | |
| Hard links per file | 177 | Hard | |
| Per-client throughput | 1,500 MiBps (Elastic) / 500 MiBps (other) | Hard | |
| Read IOPS (Elastic) | 250,000 (frequent) / 90,000 (infrequent) | Soft | |
| Write IOPS (Elastic) | 50,000 | Soft | |

**Docs**: https://docs.aws.amazon.com/efs/latest/ug/limits.html

---

## ECR

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Repositories per region | 100,000 | Soft | Increased from 10,000 in 2024 |
| Images per repository | 10,000 | Soft | |
| Image manifest size | 4 MB | Hard | |
| Layer part size | 10 MB min / 10 GB max | Hard | |
| Tags per image | 1,000 | Hard | |
| Lifecycle policy rules | 50 | Hard | |
| Pull through cache rules | 100 | Soft | |
| Replication rules | 25 | Soft | |

**Docs**: https://docs.aws.amazon.com/AmazonECR/latest/userguide/service-quotas.html

---

## SSM Parameter Store

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Parameters per account | 10,000 (standard) | Soft | Unlimited with advanced tier |
| Parameter value size (standard) | 4 KB | Hard | |
| Parameter value size (advanced) | 8 KB | Hard | |
| GetParameter TPS | 1,000 default / 10,000 high | Soft | **Enable high throughput for scale** |
| GetParameters TPS | 100 | Soft | |
| PutParameter TPS | 100 | Soft | |
| Parameter policies | 10 per parameter | Hard | |
| Parameter name length | 1,024 chars | Hard | |
| Parameter history | 100 versions | Hard | |

**Docs**: https://docs.aws.amazon.com/general/latest/gr/ssm.html

---

## Organizations

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Accounts per organization | No hard limit | Soft | Start with invitation limit |
| Root per organization | 1 | Hard | |
| OUs per parent | 1,000 | Soft | |
| OU nesting depth | 5 levels | Hard | |
| Policies per type per root | 5 | Hard | SCPs attached to root |
| Policies per type per OU | 5 | Hard | |
| Policies per type per account | 5 | Hard | |
| SCPs per organization | 1,000 | Soft | |
| SCP document size | 5,120 bytes | Hard | |
| Tag policies per org | 1,000 | Soft | |
| Delegated administrators | 3 per service | Hard | |
| API: DescribeAccount | 20 TPS | Hard | Per account |
| Control Tower: Accounts per OU | 1,000 directly nested | Hard | |
| Control Tower: Account enrollment | 1,000/week | Hard | |

**Docs**: https://docs.aws.amazon.com/organizations/latest/userguide/orgs_reference_limits.html

---

## Amazon MQ

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Brokers per region | 50 | Soft | |
| Configurations per region | 100 | Soft | |
| ActiveMQ wire-level connections | Instance-dependent | Hard | Based on instance type |
| RabbitMQ connections per node | Instance-dependent | Hard | Based on instance type |
| Storage per broker | Instance-dependent | Hard | EFS or EBS backed |
| Users per broker (ActiveMQ) | 250 | Soft | |
| Security groups per broker | 5 | Hard | |
| Tags per broker | 50 | Hard | |

**Docs**: https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/amazon-mq-limits.html

---

## Amazon Managed Prometheus (AMP)

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Active series per workspace | 1 billion max | Soft | Dynamically scaled |
| Ingestion rate per workspace | Auto-scaled | Soft | Token bucket algorithm |
| Workspaces per region | 25 | Soft | |
| Label name length | 128 chars | Hard | |
| Label value length | 2,048 chars | Hard | |
| Labels per metric | 70 | Hard | |
| Query time range | 32 days | Hard | |
| Query samples | 50 million | Hard | |
| Samples older than | 1 hour refused | Hard | |
| Alert manager config size | 1 MB | Hard | |
| Rule groups per workspace | 100 | Soft | |

**Docs**: https://docs.aws.amazon.com/prometheus/latest/userguide/AMP_quotas.html

---

## Amazon Managed Grafana (AMG)

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Workspaces per region | 5 | Soft | |
| Users per workspace | 5,000 | Soft | |
| Teams per workspace | 500 | Soft | |
| Dashboards per workspace | 2,000 | Soft | |
| Folders per workspace | 500 | Soft | |
| Data sources per workspace | 100 | Soft | |
| Alerts per workspace | 1,000 | Soft | |
| API keys per workspace | 100 | Hard | |
| Notification channels | 200 | Soft | |

**Docs**: https://docs.aws.amazon.com/grafana/latest/userguide/AMG_quotas.html

---

## ACM (Certificate Manager)

| Limit | Value | Type | Notes |
|-------|-------|------|-------|
| Certificates per region | 2,500 | Soft | |
| Certificates per year (requested) | 2,500 | Soft | |
| Domain names per certificate | 10 | Soft | |
| Private CAs per region | 200 | Soft | |
| Certificates per CA | 1,000,000 | Hard | |

**Docs**: https://docs.aws.amazon.com/acm/latest/userguide/acm-limits.html

---

## Quick Reference: Most Commonly Hit Limits

| Service | Limit | Why It Hurts |
|---------|-------|--------------|
| ALB | 5 LBs per target group | Architecture redesign needed |
| Lambda | 15 min timeout | Long processes fail silently |
| Lambda | 6 MB sync payload | API integrations break |
| API Gateway | 29s timeout | Downstream timeouts cascade |
| Cognito | 120 RPS auth | Auth outage during traffic spike |
| Step Functions | 25,000 events | Long workflows fail |
| S3 | 3,500/5,500 RPS per prefix | Throttling during burst |
| DynamoDB | 400 KB item size | Data modeling constraints |
| CloudFormation | 500 resources | Must split into nested stacks |
| Athena | 20 concurrent queries (non us-east-1) | Query queue builds up |
| Glue | 50 concurrent job runs | ETL pipelines stall |
| Kinesis | 1 MB/s per shard write | Throughput bottleneck |
| DocumentDB | 4,500 connections per instance | Connection exhaustion |
| ElastiCache | 65,000 connections per node | Redis single-threaded bottleneck |
| EFS | 25,000 connections per FS | Shared filesystem contention |
| SSM Parameter Store | 1,000 TPS default | Lambda cold starts throttled |
| Aurora Serverless v2 | 2,000 max_connections | Low ACU connection cap |
| Organizations | 5 SCPs per entity | Policy management complexity |

---

## Requesting Limit Increases

1. **Service Quotas Console**: https://console.aws.amazon.com/servicequotas/
2. **AWS CLI**: `aws service-quotas request-service-quota-increase`
3. **Support Case**: For limits not in Service Quotas

Allow 1-2 weeks for increases. Some limits require architecture review.
