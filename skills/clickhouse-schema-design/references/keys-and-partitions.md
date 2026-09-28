# Ordering keys, primary keys, and partitions

## Contents
- [How the sparse index actually works](#how-the-sparse-index-actually-works)
- [Choosing the ORDER BY](#choosing-the-order-by)
- [PRIMARY KEY vs ORDER BY](#primary-key-vs-order-by)
- [Granularity](#granularity)
- [Partitioning](#partitioning)
- [TTL](#ttl)
- [Projections: the escape hatch](#projections-the-escape-hatch)

---

## How the sparse index actually works

Data is physically sorted on disk by the `ORDER BY` columns and split into **granules** of 8,192 rows (default). ClickHouse stores one index entry per granule — the value of the key columns at the granule's first row. This is why the index stays small enough to sit in RAM even on petabyte tables: 8.87M rows produce about 1,083 index entries, not 8.87M.

Querying works by binary search over those entries to find candidate granules, then reading only those granules from each column file.

Two consequences that drive every design decision:

1. **Pruning is range-based, not lookup-based.** ClickHouse finds a contiguous range of granules. If matching rows are scattered across the whole table, every granule is a candidate and you scan everything, index or not.
2. **The sort order also determines compression.** Columns correlated with the sort order compress dramatically better. Reordering a key can cut table size by half without changing a single value.

## Choosing the ORDER BY

Rules, in priority order:

**1. Put columns that appear in nearly every query's `WHERE` clause first.** Pruning only works on a prefix. `ORDER BY (a, b, c)` prunes for `WHERE a = ...`, and for `WHERE a = ... AND b = ...`, but barely at all for `WHERE c = ...` alone. This overrides the cardinality rule below — a column you always filter on belongs first even if it is high cardinality.

**2. Then order remaining columns by ascending cardinality.** Low-cardinality columns early create large contiguous runs, which means better pruning for later columns and better compression.

**3. Put the timestamp late, not first — usually.** A common mistake is `ORDER BY (event_time, user_id)` on a table that is actually queried per-user. Since inserts arrive roughly in time order anyway, partitioning already gives coarse time pruning; use the key for the dimension you filter on.

The exception: if the dominant access pattern genuinely is "last N hours across everything" (log search, monitoring), time-first is correct.

**4. Keep it short.** Three to four columns is typical. Every extra column enlarges the index and slows merges, and columns after the first two or three rarely contribute pruning.

**5. Include enough columns to make rows unique if using `ReplacingMergeTree`** — dedup happens on the full ordering key.

### Worked examples

Data: payment events, queried mostly as "all activity for a given merchant in a date range", sometimes "all activity for a given asset".

```sql
-- Good
ORDER BY (merchant_id, event_date, asset_symbol, event_time)
```
`merchant_id` first because it is in every query. `event_date` second for range scans within a merchant.

```sql
-- Bad
ORDER BY (event_time)
```
Every merchant query scans the entire time range.

```sql
-- Also bad
ORDER BY (event_id)
```
A unique ID gives perfect ordering and zero pruning — nothing is ever filtered by it in analytics.

### When query patterns conflict

If half your queries filter by `merchant_id` and half by `asset_symbol`, one ordering key cannot serve both. Options, in order of preference:

1. **Pick the dominant pattern** and accept scans for the other, if the secondary pattern is rare or narrow.
2. **Add a projection** for the second pattern (see below) — same table, duplicated storage.
3. **Build a second table fed by a materialized view**, ordered differently. More storage, more moving parts, but full control.
4. **Skip index** on the secondary column — only if it correlates with the physical order. Usually it does not. See `skip-indices.md`.

## PRIMARY KEY vs ORDER BY

They are separate clauses. If you specify only `ORDER BY`, the primary key defaults to it — this is what most tables do and it is fine.

Specifying `PRIMARY KEY` separately is useful when you want fine sort order (for compression or dedup) but a coarser index (to keep it small in memory). The primary key **must be a prefix** of the `ORDER BY`.

```sql
ORDER BY (merchant_id, event_date, asset_symbol, event_time)
PRIMARY KEY (merchant_id, event_date)
```

Reach for this on very large tables where the index itself is consuming meaningful memory.

## Granularity

`index_granularity` defaults to 8192. Leave it alone unless you have a specific reason:

- **Lower it** (e.g. 1024) for tables with very wide rows or point-lookup-ish access, where reading 8,192 rows to return one is wasteful.
- **Raise it** for very large tables with pure scan workloads, to shrink the index.

Adaptive granularity (`index_granularity_bytes`, default 10MB) already handles wide rows automatically, so manual tuning is rarely needed.

## Partitioning

**Partitioning exists for data lifecycle management, not query speed.** Its real value: dropping, moving, detaching, or archiving a whole partition is a metadata operation. It integrates with TTL and tiered storage, so retention policies and hot/cold storage work without custom orchestration.

It can improve query performance when you filter on a column that is *not* in the primary key. It can also *hurt* performance, because each partition is stored and merged separately.

### Rules

- **Default: `PARTITION BY toYYYYMM(event_date)`.** Correct for the large majority of time-series tables.
- **Target partition count in the hundreds.** A few thousand is a warning sign. Tens of thousands is a broken cluster.
- **Each partition should hold a meaningful amount of data** — roughly ≥1GB or ≥10M rows. Many tiny partitions means many tiny parts, constant merging, and a `too many parts` error eventually.
- **Never partition by a high-cardinality column.** `PARTITION BY user_id` or `PARTITION BY transaction_hash` will take the table down.
- **Only go daily** if the table is genuinely high-volume (billions of rows/month) *and* you need daily retention granularity.
- **Do not partition at all** if the table is small (under ~10M rows) or has no retention policy. `PARTITION BY tuple()` is a legitimate answer.

### Multi-column partitioning

`PARTITION BY (toYYYYMM(event_date), region)` multiplies partition count by the cardinality of `region`. Only do this with a small, fixed set of values and a real operational need to drop by that dimension.

## TTL

TTL deletes or moves data at the part level, and works cleanly with partitioning.

```sql
-- Drop rows after 90 days
TTL event_date + INTERVAL 90 DAY DELETE

-- Move to cold storage after 30 days, delete after a year
TTL event_date + INTERVAL 30 DAY TO VOLUME 'cold',
    event_date + INTERVAL 365 DAY DELETE
```

Column-level TTL can drop individual columns while keeping the row — useful for expiring PII while keeping aggregatable fields:

```sql
ip_address String TTL event_date + INTERVAL 30 DAY
```

TTL merges consume resources. On large tables, set `ttl_only_drop_parts = 1` so ClickHouse drops whole parts instead of rewriting them — much cheaper, at the cost of coarser deletion timing.

## Projections: the escape hatch

A projection is an alternate sort order of the same data, stored inside the table and chosen automatically by the optimizer.

```sql
ALTER TABLE payments ADD PROJECTION p_by_asset (
  SELECT * ORDER BY (asset_symbol, event_time)
);
ALTER TABLE payments MATERIALIZE PROJECTION p_by_asset;
```

This is the only way to add an alternate ordering to an existing table without rebuilding it.

Trade-offs: it duplicates the data, it is not used for every query shape, and `MATERIALIZE` on a large table is a long-running operation. Prefer fixing the `ORDER BY` at design time; use projections when the table already exists and a rebuild is not worth it.
