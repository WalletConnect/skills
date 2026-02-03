# Data Retention & Privacy Remediation Guide

## Data Retention Policy

**What:** Define how long different types of data are retained.

### Policy Template
```markdown
# Data Retention Policy: [Service Name]

## Data Categories

| Data Type | Retention Period | Deletion Method | Legal Basis |
|-----------|-----------------|-----------------|-------------|
| User account data | Account lifetime + 30 days | Soft delete, then hard delete | Contract |
| Transaction logs | 7 years | Archive to cold storage | Legal requirement |
| Application logs | 1 year | Auto-expire in CloudWatch | Legitimate interest |
| Session data | 24 hours | Redis TTL | Contract |
| Analytics events | 2 years | BigQuery partition expiration | Consent |

## Implementation

### CloudWatch Log Retention
Set via Terraform or console - minimum 1 year for SOC 2.

### Database Retention
- Implement soft delete with `deleted_at` timestamp
- Run cleanup job for records older than retention period
- Archive to S3 Glacier for legal hold data

### S3 Lifecycle Rules
Configure automatic transitions and expirations.
```

### Terraform Implementation
```hcl
# CloudWatch log retention
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.service_name}"
  retention_in_days = 365  # 1 year minimum for SOC 2
}

# S3 lifecycle rules
resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    id     = "archive-old-data"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 365
      storage_class = "GLACIER"
    }

    expiration {
      days = 2555  # 7 years
    }
  }
}
```

---

## GDPR: Personal Data Identification

**What:** Document what personal data the service collects and processes.

### Data Inventory Template
```markdown
# Personal Data Inventory: [Service Name]

## Data Collected

| Field | Category | Purpose | Legal Basis | Shared With |
|-------|----------|---------|-------------|-------------|
| Email | Contact | Account creation | Contract | SendGrid (processor) |
| IP Address | Technical | Security, analytics | Legitimate interest | None |
| Wallet Address | Identifier | Service functionality | Contract | Blockchain (public) |
| Name | Identity | Account display | Contract | None |

## Data Processing Activities

| Activity | Purpose | Legal Basis | Recipients |
|----------|---------|-------------|------------|
| Account creation | Provide service | Contract | Internal DB |
| Analytics | Improve service | Legitimate interest | BigQuery |
| Email notifications | Communication | Consent | SendGrid |

## Data Storage Locations

| Location | Data Types | Encryption | Access Control |
|----------|------------|------------|----------------|
| AWS RDS (us-east-1) | User accounts | AES-256 | IAM roles |
| Redis (ElastiCache) | Sessions | In-transit | VPC only |
| S3 | File uploads | AES-256 | IAM + bucket policy |
```

---

## GDPR: Data Subject Access Request (DSAR)

**What:** Process for users to request a copy of their data.

### Implementation Checklist
- [ ] Create DSAR endpoint or process
- [ ] Document all data locations to query
- [ ] Implement data export format (JSON/CSV)
- [ ] Set up verification process
- [ ] Define response timeline (max 30 days)

### API Endpoint Example
```typescript
// POST /api/dsar/request
app.post('/api/dsar/request', authenticate, async (req, res) => {
  const userId = req.user.id;

  // Create DSAR request record
  const request = await db.dsarRequests.create({
    userId,
    status: 'pending',
    requestedAt: new Date(),
    dueDate: addDays(new Date(), 30),
  });

  // Queue background job to collect data
  await queue.add('process-dsar', { requestId: request.id });

  // Send confirmation email
  await email.send(req.user.email, 'dsar-confirmation', {
    requestId: request.id,
    dueDate: request.dueDate,
  });

  res.json({ requestId: request.id, status: 'pending' });
});

// Background job
async function processDsar(requestId: string) {
  const request = await db.dsarRequests.findById(requestId);
  const userId = request.userId;

  // Collect data from all sources
  const data = {
    profile: await db.users.findById(userId),
    transactions: await db.transactions.findByUserId(userId),
    preferences: await db.preferences.findByUserId(userId),
    activityLog: await db.activityLog.findByUserId(userId),
    // Add all relevant data sources
  };

  // Generate export file
  const exportFile = await generateExportFile(data);

  // Upload to secure location
  const downloadUrl = await uploadToS3(exportFile, `dsar/${requestId}.zip`);

  // Update request status
  await db.dsarRequests.update(requestId, {
    status: 'completed',
    downloadUrl,
    completedAt: new Date(),
  });

  // Notify user
  await email.send(request.user.email, 'dsar-ready', { downloadUrl });
}
```

---

## GDPR: Right to be Forgotten

**What:** Process for users to request deletion of their data.

### Implementation Checklist
- [ ] Create deletion request endpoint
- [ ] Document all data locations to delete
- [ ] Implement cascading deletes
- [ ] Handle data shared with processors
- [ ] Maintain deletion audit log
- [ ] Define exceptions (legal holds)

### API Endpoint Example
```typescript
// DELETE /api/account
app.delete('/api/account', authenticate, async (req, res) => {
  const userId = req.user.id;

  // Verify identity (e.g., require password confirmation)
  const { password } = req.body;
  if (!await verifyPassword(userId, password)) {
    return res.status(401).json({ error: 'Invalid password' });
  }

  // Check for legal holds
  const holds = await checkLegalHolds(userId);
  if (holds.length > 0) {
    return res.status(409).json({
      error: 'Account cannot be deleted due to legal hold',
      holds,
    });
  }

  // Queue deletion job
  await queue.add('delete-account', { userId });

  // Immediate anonymization
  await db.users.update(userId, {
    email: `deleted-${userId}@deleted.local`,
    name: 'Deleted User',
    status: 'pending_deletion',
  });

  // Revoke all sessions
  await sessions.revokeAll(userId);

  res.json({ message: 'Account scheduled for deletion' });
});

// Background job
async function deleteAccount(userId: string) {
  // Delete from all data sources
  await db.transactions.deleteByUserId(userId);
  await db.preferences.deleteByUserId(userId);
  await db.activityLog.deleteByUserId(userId);
  await db.files.deleteByUserId(userId);

  // Notify processors to delete
  await notifyProcessors(userId, 'delete');

  // Final user deletion
  await db.users.delete(userId);

  // Audit log (anonymized)
  await db.auditLog.create({
    action: 'account_deleted',
    anonymizedId: hashUserId(userId),
    timestamp: new Date(),
  });
}
```

---

## Privacy Policy Updates

**What:** Ensure privacy policy reflects actual data collection.

### Checklist
- [ ] Review all data collected by service
- [ ] Update privacy policy to reflect new data types
- [ ] Document third-party processors
- [ ] Include data retention periods
- [ ] Describe user rights (access, deletion, portability)
- [ ] Get legal review
- [ ] Publish and notify users of changes

---

## Data Processing Agreements (DPAs)

**What:** Legal agreements with third-party data processors.

### Processors Requiring DPAs
- Cloud providers (AWS, GCP)
- Email services (SendGrid, Mailgun)
- Analytics (Amplitude, Mixpanel)
- Error tracking (Sentry)
- Payment processors (Stripe)
- Any service that processes user data

### DPA Checklist
- [ ] Identify all third-party processors
- [ ] Request/sign DPA with each processor
- [ ] Document processor details in data inventory
- [ ] Review DPAs annually
- [ ] Update if processing changes

### Documentation Template
```markdown
# Third-Party Processors

| Processor | Purpose | Data Shared | DPA Signed | Review Date |
|-----------|---------|-------------|------------|-------------|
| AWS | Infrastructure | All | Yes (part of agreement) | 2025-01 |
| SendGrid | Email | Email addresses | Yes | 2025-03 |
| Sentry | Error tracking | Error context | Yes | 2025-02 |
| Stripe | Payments | Payment info | Yes (part of agreement) | 2025-01 |
```
