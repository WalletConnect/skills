---
name: clickhouse-schema-design
description: Expert guidance for designing, auditing, and optimizing ClickHouse tables — ORDER BY and primary key selection, data types and codecs, partitioning, MergeTree engine choice, materialized views (incremental and refreshable), data skipping indices, and query optimization. Use this skill whenever someone is writing or reviewing ClickHouse DDL, asks what the ORDER BY or partition key should be, mentions a slow ClickHouse query, wants to build or backfill a materialized view, is choosing between MergeTree engines, is hitting too-many-parts / memory-limit / mutation problems, is setting up or debugging a ClickPipe (Kinesis, Kafka) landing table or stream-to-table pipeline, or is modelling event, transaction, or log data into ClickHouse — even if they never say the words "review" or "best practice". Also use when porting a schema from Postgres, MySQL, BigQuery, Snowflake, or Redshift, because ClickHouse's indexing model is fundamentally different and naive ports perform badly.
---

# ClickHouse Schema Design

Guidance for engineers designing and reviewing ClickHouse tables.

The premise of this skill: ClickHouse rarely fails loudly. A bad `ORDER BY`, a `Nullable` column, or a daily partition key on a high-volume table will not error. It will just quietly cost 10–100x on every query and every merge, forever — and the ordering key cannot be changed after table creation. The cost of getting this right at design time is minutes. The cost of getting it wrong is a rebuild and a backfill.

So the job is to be specific and opinionated, not to list options.

---

## Step 0: Establish context before recommending anything

A schema recommendation is meaningless without knowing the query patterns. Never propose an `ORDER BY` without knowing what the table will be filtered on.

Gather these five things. Pull whatever is already in the conversation — do not re-ask for things the user has stated. Ask only for the genuine gaps, in one batch:

1. **Query shapes.** The top 3–5 queries by frequency: what appears in `WHERE`, what appears in `GROUP BY`, what the time range typically is. This is the single most important input.
2. **Volume and growth.** Rows today, rows/day ingested, expected size in a year. A 50M-row table and a 50B-row table want different answers.
3. **Mutability.** Append-only, or are there updates, late-arriving corrections, or deletes? Does the same logical entity get written more than once?
4. **Retention.** Is old data dropped, archived, or kept forever? Is there a compliance-driven deletion requirement?
5. **Deployment and arrival path.** Single node, replicated cluster, or ClickHouse Cloud? Affects engine names (`Replicated*`) and whether `ON CLUSTER` is needed. And how do rows arrive: batch inserts you control, or a ClickPipe / Kafka / Kinesis consumer that controls its own batching and owns part of the schema? A pipe-fed table has different rules — see Mode E.

If the user is impatient or the question is narrow, state the assumption you are making instead of blocking on the interview — e.g. "Assuming this is append-only event data queried mostly by recent time window; say so if not." Move forward with a concrete answer.

---

## Mode routing

Pick the mode from what the user brought:

| They brought | Mode | Go to |
|---|---|---|
| A description of data they need to store | **Design** | Mode A |
| Existing `CREATE TABLE` / migration / dbt model | **Audit** | Mode B |
| An agreed design, and want the SQL | **Generate** | Mode C |
| A slow query, or an operational symptom | **Diagnose** | Mode D |
| A ClickPipe / Kinesis / Kafka landing table, a pipe that is dropping or duplicating rows, or a stream that needs a home | **Ingest** | Mode E |

Modes combine. An audit usually ends with generated corrected DDL. A diagnosis often reveals a design problem and routes back to Mode A.

---

## Mode A — Design

Work in this order. Each decision constrains the next.

1. **Engine.** Start from `MergeTree`. Move off it only for a stated reason — dedup (`ReplacingMergeTree`), pre-aggregation (`SummingMergeTree`, `AggregatingMergeTree`), mutable rows (`CollapsingMergeTree`). See `references/table-engines.md`.
2. **ORDER BY.** The highest-leverage decision in the whole schema. See `references/keys-and-partitions.md`.
3. **Column types and codecs.** Free compression and scan-speed wins. See `references/data-types.md`.
4. **PARTITION BY.** Default to `toYYYYMM(<time column>)`. Justify anything finer. See `references/keys-and-partitions.md`.
5. **TTL**, if retention was stated.
6. **Materialized views**, only for query patterns the base table's ordering key cannot serve. See `references/materialized-views.md`.
7. **Skip indices**, last and only if a specific query needs them. See `references/skip-indices.md`.

Present the result as: the DDL, then a short rationale per decision, then explicitly name what this design is *bad* at. That last part matters — every ClickHouse ordering key optimizes some queries and deoptimizes others, and the user needs to know which queries they have just made slow.

---

## Mode B — Audit existing DDL

Read the DDL, then report findings in this exact format:

```
## Verdict
[APPROVED — no blocking issues] or [N findings, M blocking]

## Findings

| Severity | Location | Finding | Why it matters | Fix |
|---|---|---|---|---|
| 🔴 | ORDER BY | ... | ... | ... |
| 🟡 | col `amount_usd` | ... | ... | ... |
| 🟢 | col `status` | ... | ... | ... |

## Corrected DDL
[full rewritten CREATE TABLE]

## Migration note
[whether this needs a table rebuild + backfill, or can be done with ALTER]
```

Severity definitions — apply them honestly, don't inflate:

- 🔴 **Blocking.** Will cause real pain at scale and requires a table rebuild to fix later. Wrong `ORDER BY`, over-granular partitioning, an engine that can't express the required semantics.
- 🟡 **Costly.** Measurable waste in storage, memory, or query time. Fixable with `ALTER`. `Nullable` where not needed, missing `LowCardinality`, oversized integer types, missing codecs.
- 🟢 **Minor.** Style, naming, or a marginal improvement.

Always state clearly whether a fix requires a rebuild. `ORDER BY` and `PARTITION BY` cannot be altered on an existing table; column types and codecs usually can. Users consistently underestimate this, and a finding without a migration path is not actionable.

If the DDL is genuinely fine, say `APPROVED` and stop. Do not manufacture 🟢 findings to look thorough.

---

## Mode C — Generate DDL

Produce runnable SQL, not pseudocode. Use `templates/` as starting points:

- `templates/event-table.sql` — append-only event or log stream
- `templates/transaction-table.sql` — records with corrections/dedup via `ReplacingMergeTree`
- `templates/materialized-view.sql` — incremental MV with `AggregatingMergeTree` target and a safe backfill
- `templates/landing-table.sql` — ClickPipe landing table, typed `ReplacingMergeTree` consumer, routing MV, bounded backfill

Rules for generated DDL:
- Always include explicit `ENGINE`, `ORDER BY`, `PARTITION BY`, and `SETTINGS index_granularity` only if deviating from the default.
- Always add a comment above the `ORDER BY` naming the queries it serves.
- Never emit `POPULATE` on a materialized view against a table that already has data. Emit the create-then-backfill pattern instead.
- If the deployment is replicated, use `Replicated*` engines and `ON CLUSTER`.

---

## Mode D — Diagnose

Start with evidence, not guesses. Ask for or run these before theorizing:

```sql
-- Did the query use the primary index, and how much did it skip?
EXPLAIN indexes = 1 <query>;

-- What actually happened
SELECT query_duration_ms, read_rows, read_bytes, memory_usage, result_rows
FROM system.query_log
WHERE type = 'QueryFinish' AND query_id = '<id>'
ORDER BY event_time DESC LIMIT 1;

-- Part health
SELECT table, partition, count() AS parts, sum(rows), formatReadableSize(sum(bytes_on_disk))
FROM system.parts WHERE active AND database = '<db>'
GROUP BY table, partition ORDER BY parts DESC LIMIT 20;
```

The diagnostic that matters most: compare `read_rows` to the number of rows the query logically needed. If ClickHouse read 4 billion rows to return 200, the primary index was not used, and the cause is almost always that the `WHERE` clause does not hit a prefix of the `ORDER BY`.

Symptom-to-cause table and full diagnostic queries: `references/query-optimization.md`.

---

## Mode E — Streaming ingestion

For tables fed by ClickPipes (Kinesis, Kafka and compatibles) or any long-running consumer that issues its own inserts. Detect it: a `clickpipe:` user inserting in `system.query_log`, or a `<table>_clickpipes_error` sibling table.

The shape that works is **landing table → materialized views → typed tables**:

1. The pipe writes the raw message body plus source metadata into a thin landing table ordered by `(arrival_timestamp, sequence)`. Time-first is correct here and nowhere else in this skill.
2. Materialized views parse `raw` and route into typed tables, each with its own business-key `ORDER BY`.
3. The first typed table is a `ReplacingMergeTree` keyed on business identity, because delivery is at-least-once and every pipe restart or replay redelivers.

Rules that override the general guidance when a pipe is involved:

- The pipe controls batching. `async_insert` and insert-side settings do not apply; tune pipe memory and the destination table instead. Expect an insert every ~5 seconds on low-volume streams.
- The pipe's mapped columns are a contract. Add columns with `ALTER` freely (an ingest timestamp via `MATERIALIZED now64(3)` is the standard one); never rename, drop, or retype a mapped column.
- A materialized view that throws fails the pipe's insert. Use `*OrNull` / `*OrZero` conversions on anything the producer does not guarantee, and test the MV `SELECT` against real `raw` before creating it.
- Start position is fixed at pipe creation. Recreating a pipe either skips records or replays the whole retention window; decide which before touching it, and protect it with `prevent_destroy`.

When auditing, run the pipe-fed checklist in the reference in addition to Mode B. Full detail, monitoring queries, virtual columns, auth and cross-account setup: `references/streaming-ingestion.md`.

---

## The non-negotiables

Quick reference. Each is expanded in the reference files.

1. **`ORDER BY` is the index.** There is no separate index to add later, and it cannot be changed after creation. Projections are the only escape hatch, at the cost of duplicated data.
2. **A filter only prunes if it hits a prefix of the `ORDER BY`.** Filtering on the third key column alone scans everything.
3. **Order the key by cardinality ascending**, subject to rule 2 — put the column you always filter on first, even if it is high cardinality.
4. **Partitioning is a data-lifecycle tool, not a query-speed tool.** Its job is `DROP PARTITION`, TTL, and storage tiering as metadata operations.
5. **Keep total partition count in the hundreds.** `toYYYYMM()` is the default. Daily partitions on a high-volume table produce part explosion and merge pressure.
6. **Avoid `Nullable`.** It adds a second column and disables some optimizations. Use a sentinel or default unless null genuinely differs from zero/empty.
7. **`LowCardinality(String)` below roughly 10,000 distinct values.** Above that it starts to hurt.
8. **Use the narrowest type that fits, then add a codec.** `Delta, ZSTD` for timestamps and monotonic IDs; `ZSTD` for most strings; `T64` for sparse integers.
9. **Do not treat `ALTER UPDATE` / `ALTER DELETE` as routine.** Mutations rewrite whole parts. Model corrections as appends.
10. **Never schedule `OPTIMIZE TABLE ... FINAL`.** It forces full merges and will eventually take longer than the interval between runs.
11. **Insert in large batches** (10k–100k+ rows), or enable `async_insert`. Many small inserts are the leading cause of too-many-parts.
12. **A materialized view reads the inserted block, not the table.** It cannot see history, cannot join against the full source, and does not fire on merges or mutations.
13. **Skip indices are a last resort** and only help when the indexed column correlates with physical sort order. Verify with `EXPLAIN indexes = 1` before and after — an unverified skip index is usually pure write-amplification.
14. **A pipe-fed landing table is thin, raw, and time-ordered, and everything downstream deduplicates.** ClickPipes delivers at-least-once, owns its mapped columns, and fails the whole insert when a materialized view throws. Parse in MVs, not in the pipe mapping.

---

## Reference files

Read the one that matches the decision at hand rather than all of them.

| File | Covers |
|---|---|
| `references/keys-and-partitions.md` | `ORDER BY` selection, `PRIMARY KEY` vs `ORDER BY`, granules, partitioning, projections |
| `references/data-types.md` | Type selection, `LowCardinality`, `Nullable`, `Enum`, `JSON`, compression codecs |
| `references/table-engines.md` | MergeTree family, dedup patterns, `FINAL` vs `argMax`, replication |
| `references/materialized-views.md` | Incremental vs refreshable, aggregate states, chaining, safe backfill |
| `references/skip-indices.md` | Index types, when they help, how to verify |
| `references/query-optimization.md` | `EXPLAIN`, `system.query_log`, JOIN strategy, symptom-to-cause table |
| `references/streaming-ingestion.md` | ClickPipes (Kinesis, Kafka): landing-table pattern, virtual columns, ownership rules, at-least-once dedup, batching, replay, IAM/cross-account, error tables, monitoring, Cloud quirks, pipe-fed audit checklist |

External sources worth citing to users:
- ClickHouse best practices: https://clickhouse.com/docs/best-practices
- Sparse primary index deep dive: https://clickhouse.com/docs/guides/best-practices/sparse-primary-indexes
- Altinity Knowledge Base (operational issues): https://kb.altinity.com/
- ClickPipes docs (Kinesis, Kafka, error tables, scaling): https://clickhouse.com/docs/integrations/clickpipes
