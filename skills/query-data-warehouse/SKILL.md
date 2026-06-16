---
name: query-data-warehouse
description: Runs ad-hoc SQL queries against the Reown analytics data warehouse (AWS Athena, account 898587786287, eu-central-1) from the CLI. Use when a user wants to query warehouse/data-lake tables — e.g. counts of sessions, messages, projects, or any prod_warehouse / data lake table — via Athena, or asks "query the data warehouse / data lake / Athena". Covers SSO login, the right profile and workgroup, the start→poll→fetch flow, and where table/column definitions live.
---

# Query the Reown Data Warehouse (Athena)

## Goal
Run a SQL query against the Reown analytics warehouse via the AWS Athena CLI and return results, getting auth, profile, and workgroup right the first time.

## When to use
- A user wants data from `prod_warehouse.*` (or `staging_warehouse.*`) or raw `prod_data_lake.*` tables: counts, distinct values, aggregates, samples.
- A user says "query the data warehouse / data lake / Athena", or asks for a metric that lives in the warehouse.

## When not to use
- Authoring or running dbt models/transformations — that's the data-lake repo's `/dbt` command and `dbt/CLAUDE.md`.
- Authoring Hex semantic models — that's the `hex-semantic-model` skill in the data-lake repo.
- Querying application Postgres/Mongo/Redis directly — this skill is Athena only.

## Key facts (account & access)
- **Account** `898587786287`, **region** `eu-central-1`, AWS SSO session **`rs-relay-analytics`**.
- **Profile:** use **`Administrator-898587786287`** to *run* queries. The `Read-Only-898587786287` profile can authenticate but is **denied `athena:StartQueryExecution`** — it cannot start queries.
- **Workgroup:** use **`dbt_prod_workgroup`** (staging: `dbt_staging_workgroup`). It has its own S3 output location, so you do **not** pass `--result-configuration`. The `primary` workgroup has **no** output location configured — only use it if you also pass `--result-configuration OutputLocation=s3://...`.
- **Source of truth for tables/columns:** the **`reown-com/data-lake`** dbt project (`~/dev/data-lake`, search `dbt/sources/` and `dbt/models/`, e.g. `grep -ri <service> ~/dev/data-lake/dbt`). Read mappings from there rather than guessing.

## Query conventions
- The **`dt` partition column is a `DATE`** (not a string). Filter directly: `WHERE dt = CURRENT_DATE`. Do **not** `CAST(CURRENT_DATE AS VARCHAR)`. Keeping a `dt` predicate prunes partitions and keeps scans cheap.
- Any result with a `project_id` should be joined to **`prod_warehouse.dim_projects`** on `project_id` to add `project_name` (use an explicit `ON` join, not `USING`, if you also qualify the column with an alias).
- `get-query-results` pages at **1000 rows**. To get a total, prefer an **aggregate** (`COUNT(*)`, `COUNT(DISTINCT ...)`, `SUM(...)`) over counting returned rows.

## Default workflow
1. **Ensure SSO is valid.** SSO tokens expire. Login is interactive (opens a browser), so the **user** must run it — suggest they run it in-session with the `!` prefix:
   ```bash
   aws sso login --sso-session rs-relay-analytics
   ```
   Symptom of an expired token: `Token has expired and refresh failed`.
2. **Find the table/columns** in `~/dev/data-lake/dbt` if you don't already know them.
3. **Run the query** with the helper script (handles start → poll → fetch):
   ```bash
   skills/query-data-warehouse/scripts/athena-query.sh \
     "SELECT COUNT(*) FROM prod_warehouse.fact_relay__sessions WHERE dt = CURRENT_DATE"
   ```
   Or inline (start → poll → fetch):
   ```bash
   QID=$(aws athena start-query-execution \
     --profile Administrator-898587786287 --region eu-central-1 \
     --work-group dbt_prod_workgroup \
     --query-string "SELECT COUNT(*) FROM prod_warehouse.fact_relay__sessions WHERE dt = CURRENT_DATE" \
     --query 'QueryExecutionId' --output text)

   aws athena get-query-execution --profile Administrator-898587786287 --region eu-central-1 \
     --query-execution-id "$QID" --query 'QueryExecution.Status.State' --output text   # poll until SUCCEEDED

   aws athena get-query-results --profile Administrator-898587786287 --region eu-central-1 \
     --query-execution-id "$QID" --output table   # row 0 is the header
   ```
4. **Report the result.** If a query FAILED, read `QueryExecution.Status.StateChangeReason` for the cause.

## Smoke test (verify the setup works)
Run this first to confirm auth, profile, and workgroup are all good before writing a real query:
```bash
skills/query-data-warehouse/scripts/athena-query.sh \
  "SELECT COUNT(*) FROM prod_warehouse.fact_relay__sessions WHERE dt = CURRENT_DATE"
```
A single number (today's closed relay sessions) means everything works.

## Validation checklist
- [ ] SSO session valid (no "Token has expired"); if not, asked the user to `aws sso login --sso-session rs-relay-analytics`.
- [ ] Used the `Administrator-898587786287` profile (not Read-Only) to start the query.
- [ ] Used `--work-group dbt_prod_workgroup` (no `--result-configuration` needed).
- [ ] Table/column names verified against `~/dev/data-lake/dbt`.
- [ ] `dt` filtered as a DATE; `project_id` joined to `dim_projects` if names are wanted.
- [ ] Used an aggregate for totals (didn't count paged rows).

## Examples
### Example 1 — distinct projects with sessions today
Request: "How many unique project_ids had relay sessions today?"
```sql
SELECT COUNT(DISTINCT project_id)
FROM prod_warehouse.fact_relay__sessions
WHERE dt = CURRENT_DATE
```

### Example 2 — top projects by session count today, with names
Request: "Top 10 projects by sessions today, with project names."
```sql
SELECT s.project_id, p.project_name, COUNT(*) AS sessions
FROM prod_warehouse.fact_relay__sessions s
LEFT JOIN prod_warehouse.dim_projects p ON p.project_id = s.project_id
WHERE s.dt = CURRENT_DATE
GROUP BY s.project_id, p.project_name
ORDER BY sessions DESC
LIMIT 10
```

## Notes
- `fact_relay__sessions` holds one row per **closed** WebSocket session, so it reflects sessions that have ended, not currently-open ones.
- Region defaults to `eu-central-1`; if a query can't find a table, confirm Glue/Athena for that data lives in this account/region.
