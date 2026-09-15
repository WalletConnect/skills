# Materialized views

## Contents
- [The mental model](#the-mental-model)
- [Incremental vs refreshable](#incremental-vs-refreshable)
- [Building an incremental MV](#building-an-incremental-mv)
- [Aggregate states](#aggregate-states)
- [Safe backfill](#safe-backfill)
- [Chaining](#chaining)
- [Refreshable MVs](#refreshable-mvs)
- [The Null-table fan-out pattern](#the-null-table-fan-out-pattern)
- [Failure modes](#failure-modes)

---

## The mental model

**A ClickHouse materialized view is an insert trigger, not a view.** It does not store anything itself and it does not query the source table. When a block of rows is inserted into the source table, ClickHouse runs the MV's `SELECT` **over that block only** and writes the result to a target table.

Everything surprising about materialized views follows from that one sentence:

- It cannot see historical data. Creating an MV does nothing to rows already in the table.
- It cannot join against the full source table in a way that stays correct — the left side is only the new block.
- It does not fire on merges, mutations, or `ALTER`.
- It fires on every insert, so its cost is paid on the write path.
- If its `SELECT` throws, **the original insert fails**. A broken MV breaks ingestion.

This is also why they scale so well: computation shifts to insert time and only ever touches new data, which is why an incremental MV over a petabyte table stays cheap.

## Incremental vs refreshable

| | Incremental | Refreshable |
|---|---|---|
| Trigger | Every insert into source | Schedule (`REFRESH EVERY ...`) |
| Scope | New block only | Full re-execution over the whole dataset |
| Freshness | Real time | As fresh as the interval |
| Cost | Proportional to new data | Proportional to total data |
| Joins | Only against small dimension tables | Any join |
| Consistency | Eventually consistent (merges are async) | Atomic swap on each refresh |

**Default to incremental.** They support all aggregation functions, scale to petabytes, and in most cases have no appreciable impact on cluster performance.

**Use refreshable when** the computation is incompatible with block-at-a-time processing: multi-table joins, global ranking or windowing, full denormalization, dedup across the entire history. Refreshable MVs can also express dependencies on one another, which lets them replace a simple scheduled DAG.

One caveat to name explicitly to users: incremental MVs are eventually consistent, because the merge of partial aggregate states is asynchronous. Fine for dashboards and analytics. Not fine as the authority for a real-time correctness decision — a balance check or a limit enforcement — where "correct once merges finish" is a gap.

## Building an incremental MV

Always create the target table explicitly. Do not use the implicit `.inner` table form — you cannot manage its schema, TTL, or partitioning, and it makes backfills and schema changes far harder.

```sql
-- 1. Target table
CREATE TABLE payments_daily
(
    merchant_id   UInt64,
    event_date    Date,
    asset_symbol  LowCardinality(String),
    payment_count AggregateFunction(count),
    unique_payers AggregateFunction(uniq, UInt64),
    total_amount  AggregateFunction(sum, Decimal(38, 18))
)
ENGINE = AggregatingMergeTree
PARTITION BY toYYYYMM(event_date)
ORDER BY (merchant_id, event_date, asset_symbol);

-- 2. The view
CREATE MATERIALIZED VIEW payments_daily_mv TO payments_daily AS
SELECT
    merchant_id,
    toDate(event_time)   AS event_date,
    asset_symbol,
    countState()                 AS payment_count,
    uniqState(payer_id)          AS unique_payers,
    sumState(amount)             AS total_amount
FROM payments
GROUP BY merchant_id, event_date, asset_symbol;
```

The `GROUP BY` in the MV aggregates within each inserted block. `AggregatingMergeTree` then merges those partial results across blocks over time.

The target table's `ORDER BY` should match the MV's `GROUP BY`. Mismatches silently produce rows that never collapse.

## Aggregate states

The `-State` / `-Merge` pair is what makes partial aggregation work.

- In the MV: `countState()`, `sumState(x)`, `uniqState(x)`, `avgState(x)`, `quantilesState(0.5, 0.99)(x)`
- On read: `countMerge(col)`, `sumMerge(col)`, `uniqMerge(col)`, `avgMerge(col)`, `quantilesMerge(0.5, 0.99)(col)`

Reading an `AggregateFunction` column without `-Merge` returns binary garbage. Always read through a `GROUP BY`:

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

Wrap this in a plain `VIEW` so consumers never touch the state columns directly.

**Why states rather than plain sums:** states are re-aggregatable. Daily `uniqState` values can be merged into a correct monthly unique count. Daily `uniq` *results* cannot — summing them double-counts. If there is any chance the aggregate will be rolled up to a coarser grain later, use states.

Where every measure is a plain additive sum or count and will never be rolled up differently, `SummingMergeTree` with plain `sum()` is simpler and fine.

## Safe backfill

`POPULATE` is convenient and wrong for anything live: rows inserted *while* `POPULATE` runs are missed, silently. Never emit it against a table that is receiving writes.

The safe pattern is three steps, in this order:

```sql
-- 1. Create the MV first. From this moment, new inserts are captured.
CREATE MATERIALIZED VIEW payments_daily_mv TO payments_daily AS
SELECT ... FROM payments GROUP BY ...;

-- 2. Note the cutoff. Everything after this is already handled by the MV.
--    Use a timestamp safely before MV creation.

-- 3. Backfill history in bounded chunks, below the cutoff.
INSERT INTO payments_daily
SELECT
    merchant_id,
    toDate(event_time) AS event_date,
    asset_symbol,
    countState(),
    uniqState(payer_id),
    sumState(amount)
FROM payments
WHERE event_time <  '2026-09-01 00:00:00'
  AND event_time >= '2026-08-01 00:00:00'
GROUP BY merchant_id, event_date, asset_symbol;
```

Chunk by month (or day on large tables) rather than backfilling everything in one statement — a single huge `INSERT SELECT` will hit memory limits and leave you unsure what landed.

Overlap between the backfill window and the MV's live capture causes double-counting, and `AggregatingMergeTree` will not detect it. Verify before and after:

```sql
SELECT count() FROM payments WHERE event_date = '2026-08-15';
SELECT countMerge(payment_count) FROM payments_daily WHERE event_date = '2026-08-15';
```

## Chaining

An MV can read from another MV's target table, letting you build daily → monthly rollups.

```sql
CREATE MATERIALIZED VIEW payments_monthly_mv TO payments_monthly AS
SELECT
    merchant_id,
    toStartOfMonth(event_date) AS month,
    countMergeState(payment_count) AS payment_count,
    uniqMergeState(unique_payers)  AS unique_payers
FROM payments_daily
GROUP BY merchant_id, month;
```

Note `-MergeState`: it merges the incoming states and emits a new state. Using `-State` on an already-`State` column is a type error; using `-Merge` produces a final value that cannot be rolled up further.

Keep chains shallow. Two levels is manageable; three or more becomes hard to reason about and hard to backfill, since each level must be backfilled in order.

## Refreshable MVs

```sql
CREATE MATERIALIZED VIEW merchant_summary
REFRESH EVERY 1 HOUR
TO merchant_summary_table AS
SELECT
    m.merchant_id,
    m.name,
    count()      AS lifetime_payments,
    sum(p.amount) AS lifetime_volume
FROM payments AS p
INNER JOIN merchants AS m ON p.merchant_id = m.merchant_id
GROUP BY m.merchant_id, m.name;
```

The syntax is identical to an incremental MV apart from the `REFRESH` clause. The query runs immediately and then on the interval, and the result set is swapped into the target table atomically — readers never see a partial state.

Use `DEPENDS ON` to order dependent refreshes:

```sql
CREATE MATERIALIZED VIEW downstream
REFRESH EVERY 1 HOUR DEPENDS ON merchant_summary
TO downstream_table AS SELECT ...;
```

Monitor them — a refresh that takes longer than its interval will quietly fall behind:

```sql
SELECT view, status, last_refresh_time, last_success_duration_ms, exception
FROM system.view_refreshes;
```

## The Null-table fan-out pattern

When you need several differently-ordered derived tables from one stream but do not need the raw rows, insert into a `Null` table and hang multiple MVs off it.

```sql
CREATE TABLE payments_ingest (...) ENGINE = Null;

CREATE MATERIALIZED VIEW mv_by_merchant TO payments_by_merchant AS
SELECT ... FROM payments_ingest;

CREATE MATERIALIZED VIEW mv_by_asset TO payments_by_asset AS
SELECT ... FROM payments_ingest;
```

One insert path, several target tables, each with its own ordering key, and no storage spent on raw rows. This is also the cleanest answer to the "my queries filter on two different dimensions" problem.

## Failure modes

| Symptom | Cause |
|---|---|
| MV is empty after creation | Expected — MVs do not see history. Backfill. |
| Inserts started failing after adding an MV | The MV's `SELECT` throws. Test it standalone against a sample block. |
| Counts are roughly double | Backfill window overlapped live MV capture. |
| `uniq` totals are wrong when rolled up | Stored final values instead of `uniqState`. |
| Reading returns binary junk | Missing `-Merge` on an `AggregateFunction` column. |
| Target table keeps growing, never collapses | Target `ORDER BY` does not match the MV's `GROUP BY`. |
| Join in an incremental MV returns partial results | The left side is only the new block. Use a `Dictionary` for small lookups, or a refreshable MV. |
| Ingestion slowed noticeably | Too many MVs on one source table; each fires per insert. |
