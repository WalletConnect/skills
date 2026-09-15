# Table engines

## Contents
- [Choosing](#choosing)
- [MergeTree](#mergetree)
- [ReplacingMergeTree](#replacingmergetree)
- [Reading deduplicated data correctly](#reading-deduplicated-data-correctly)
- [SummingMergeTree](#summingmergetree)
- [AggregatingMergeTree](#aggregatingmergetree)
- [CollapsingMergeTree and VersionedCollapsingMergeTree](#collapsingmergetree-and-versionedcollapsingmergetree)
- [Replication](#replication)
- [Non-MergeTree engines worth knowing](#non-mergetree-engines-worth-knowing)

---

## Choosing

| Situation | Engine |
|---|---|
| Append-only facts, no dedup needed | `MergeTree` |
| Same logical row arrives more than once; keep the latest | `ReplacingMergeTree(version)` |
| Pre-aggregated sums over a fixed dimension set | `SummingMergeTree` |
| Pre-aggregated with `uniq`, `avg`, quantiles, etc. | `AggregatingMergeTree` |
| Rows that need true mutation (state machine) | `VersionedCollapsingMergeTree` |
| Small static lookup, queried as a dimension | `Join` or `Dictionary` |

Default to `MergeTree`. Every other engine trades away simplicity for a specific behaviour, and that behaviour always comes with a read-side cost that engineers underestimate.

## MergeTree

The base engine. Inserts create immutable parts; a background process merges them. Nothing is deduplicated, nothing is aggregated, nothing is rewritten.

```sql
CREATE TABLE events (
    merchant_id UInt64,
    event_time  DateTime CODEC(Delta, ZSTD(1)),
    event_date  Date MATERIALIZED toDate(event_time),
    event_type  LowCardinality(String),
    amount      Decimal(38, 18)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_date)
ORDER BY (merchant_id, event_date, event_time);
```

## ReplacingMergeTree

Keeps the last row per `ORDER BY` tuple, where "last" is decided by the version column. Rows with the same ordering key are collapsed **during merges**.

```sql
CREATE TABLE payments (
    payment_id  UUID,
    merchant_id UInt64,
    status      LowCardinality(String),
    amount      Decimal(38, 18),
    updated_at  DateTime,
    is_deleted  UInt8 DEFAULT 0
)
ENGINE = ReplacingMergeTree(updated_at, is_deleted)
PARTITION BY toYYYYMM(updated_at)
ORDER BY (merchant_id, payment_id);
```

The second argument (`is_deleted`) is optional and marks soft deletes, which are removed on merge when `clean_deleted_rows` is enabled.

**The thing that catches everyone:** deduplication is eventual and partition-scoped. Two versions of the same row can coexist indefinitely if they are in different parts that have not merged — and rows in *different partitions* never dedup against each other. If your partition key is derived from a mutable column (like `updated_at` above), the same `payment_id` updated across a month boundary will produce two surviving rows.

Practical implication: if the version column can change the partition, partition by an immutable column (`created_at`) instead, or accept the duplicate and handle it on read.

## Reading deduplicated data correctly

Never assume the table is deduplicated at read time. Three options:

**1. `FINAL`** — correct, and much faster than its reputation on modern versions, especially with `do_not_merge_across_partitions_select_final = 1`.

```sql
SELECT * FROM payments FINAL WHERE merchant_id = 42;
```

**2. `argMax` aggregation** — usually the fastest at scale, and explicit about intent:

```sql
SELECT
    payment_id,
    argMax(status, updated_at) AS status,
    argMax(amount, updated_at) AS amount,
    max(updated_at)            AS updated_at
FROM payments
WHERE merchant_id = 42
GROUP BY payment_id
HAVING argMax(is_deleted, updated_at) = 0;
```

**3. `LIMIT 1 BY`** — concise for row-level latest:

```sql
SELECT * FROM payments
WHERE merchant_id = 42
ORDER BY updated_at DESC
LIMIT 1 BY payment_id;
```

Whichever you pick, wrap it in a normal (non-materialized) `VIEW` so that consumers — dashboards, BI tools, analysts — cannot accidentally query the raw table and get duplicates. This is the single most common source of wrong numbers in ClickHouse deployments.

## SummingMergeTree

Collapses rows with identical ordering keys by summing all other numeric columns. Useful as a materialized view target for simple counters.

```sql
ENGINE = SummingMergeTree
ORDER BY (merchant_id, event_date, event_type)
```

Restricted to sums. The moment you need `uniq`, `avg`, or a quantile, move to `AggregatingMergeTree`. Same eventual-consistency caveat as `ReplacingMergeTree`: always aggregate on read (`SELECT sum(cnt) ... GROUP BY ...`), never assume merging has happened.

## AggregatingMergeTree

Stores partial aggregation states (`AggregateFunction(...)`) and merges them. The workhorse target for incremental materialized views. Covered in detail in `materialized-views.md`.

```sql
CREATE TABLE payments_daily (
    merchant_id     UInt64,
    event_date      Date,
    payment_count   AggregateFunction(count),
    unique_payers   AggregateFunction(uniq, UInt64),
    total_amount    AggregateFunction(sum, Decimal(38, 18))
)
ENGINE = AggregatingMergeTree
ORDER BY (merchant_id, event_date);
```

Read with `-Merge`, always with a `GROUP BY`:

```sql
SELECT
    merchant_id,
    countMerge(payment_count) AS payments,
    uniqMerge(unique_payers)  AS payers,
    sumMerge(total_amount)    AS volume
FROM payments_daily
WHERE event_date >= today() - 30
GROUP BY merchant_id;
```

## CollapsingMergeTree and VersionedCollapsingMergeTree

These implement true row mutation by writing a cancelling row (`sign = -1`) followed by the new row (`sign = 1`).

```sql
ENGINE = VersionedCollapsingMergeTree(sign, version)
```

Powerful, and genuinely hard to operate — the producer must reliably emit the exact prior row state to cancel it. In practice `ReplacingMergeTree` plus `argMax` on read covers most needs with far less risk. Reach for collapsing engines only when you need running sums that must net out correctly without a `GROUP BY` on read, and the producer can guarantee cancel rows.

## Replication

On a cluster, prefix the engine: `ReplicatedMergeTree`, `ReplicatedReplacingMergeTree`, etc.

```sql
CREATE TABLE events ON CLUSTER '{cluster}' (...)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/events', '{replica}')
```

Use the macro form (`{shard}`, `{replica}`) rather than hardcoding paths, or restoring a replica becomes painful. On ClickHouse Cloud, replication is implicit — write plain `MergeTree` and the service handles it.

Note that replicated tables deduplicate *identical insert blocks* automatically (by block checksum, within a window). This is insert idempotency, not row deduplication — it protects against retried inserts, not against genuinely duplicate business data.

## Non-MergeTree engines worth knowing

- **`Dictionary`** — small lookup tables held in memory, queried with `dictGet()`. Far faster than joining a dimension table, and the right answer for merchant names, token metadata, chain registries.
- **`Null`** — discards everything written to it. The standard pattern for a table that exists only to trigger materialized views without storing raw rows.
- **`Buffer`** — buffers small inserts in memory before flushing. A workaround for many-small-inserts, but it loses data on crash and complicates reads. Prefer `async_insert` instead.
- **`S3` / `Iceberg` / `Delta`** — query external object storage in place. Useful for cold data and lakehouse integration.
