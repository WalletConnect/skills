# Data skipping indices

## The one thing to understand first

A skip index stores a small summary per block of granules (`GRANULARITY N` granules per index entry) and lets ClickHouse skip blocks that cannot contain matching rows.

It only helps when **matching rows are clustered in the physical sort order**. If the values you filter on are scattered uniformly across the table, every block is a candidate, nothing gets skipped, and you have paid write-amplification and storage for zero benefit.

This is why skip indices are the *last* tool to reach for, after `ORDER BY`, projections, and materialized views. Most skip indices added in practice do nothing. Add one only with a specific query in mind, and verify with `EXPLAIN indexes = 1` before and after.

## Index types

| Type | Syntax | Good for |
|---|---|---|
| `minmax` | `TYPE minmax` | Numeric or date columns correlated with sort order |
| `set` | `TYPE set(max_rows)` | Low-cardinality columns, clustered values |
| `bloom_filter` | `TYPE bloom_filter(fp_rate)` | Equality on high-cardinality columns |
| `tokenbf_v1` | `TYPE tokenbf_v1(size, hashes, seed)` | Whole-word search in text |
| `ngrambf_v1` | `TYPE ngrambf_v1(n, size, hashes, seed)` | Substring / `LIKE '%x%'` search |

## Syntax

```sql
ALTER TABLE payments
    ADD INDEX idx_payer payer_id TYPE bloom_filter(0.01) GRANULARITY 4;

-- Only affects new data; existing parts need materializing
ALTER TABLE payments MATERIALIZE INDEX idx_payer;
```

`GRANULARITY N` means one index entry per N granules (N × 8,192 rows). Lower N gives finer skipping and a larger index. 1–4 is typical.

Or at creation:

```sql
CREATE TABLE payments (
    ...,
    INDEX idx_payer payer_id TYPE bloom_filter(0.01) GRANULARITY 4,
    INDEX idx_amount amount TYPE minmax GRANULARITY 1
)
ENGINE = MergeTree
ORDER BY (merchant_id, event_date);
```

## When each actually works

**`minmax`** — the cheapest and most often useful. Works when the column is monotonic or strongly correlated with the sort order. A `minmax` on `amount` for a `WHERE amount > 1000000` filter works well if large payments cluster; it does nothing if they are uniformly scattered.

**`set(max_rows)`** — stores the distinct values per block, up to `max_rows`. Effective when a low-cardinality column has long runs. `set(100)` on `status` works if statuses cluster by time; it fails if every block contains every status. `set(0)` means unlimited, which is usually a mistake.

**`bloom_filter(fp_rate)`** — equality only (`=`, `IN`). Genuinely useful for high-cardinality lookup columns that are *not* in the ordering key, such as finding all rows for a given `transaction_hash`. This is the most common legitimate use: point lookups on a secondary ID. `0.01` is a reasonable default false-positive rate.

**`tokenbf_v1`** — tokenizes on non-alphanumeric boundaries and bloom-filters the tokens. For `hasToken(message, 'timeout')` style searches in log text.

**`ngrambf_v1`** — for substring matching where tokens do not help. Expensive to build and store; use only when `LIKE '%...%'` is a real, frequent query.

## Verifying

This is the whole discipline. Before adding:

```sql
EXPLAIN indexes = 1
SELECT count() FROM payments WHERE payer_id = 12345;
```

Note the granules selected. Add the index, materialize it, run the same `EXPLAIN`, and compare. If granule count did not drop substantially, **drop the index**:

```sql
ALTER TABLE payments DROP INDEX idx_payer;
```

Also check actual rows read:

```sql
SELECT read_rows, read_bytes, query_duration_ms
FROM system.query_log
WHERE type = 'QueryFinish' AND query LIKE '%payer_id = 12345%'
ORDER BY event_time DESC LIMIT 2;
```

## Costs

- Built and maintained on every insert and merge — write throughput drops.
- Stored on disk alongside the data.
- `MATERIALIZE INDEX` on a large existing table is a long-running mutation.
- Multiple unhelpful indices compound all of the above.

## Alternatives to try first

| Problem | Better tool |
|---|---|
| Filtering on a column not in the key, frequently | Change the `ORDER BY` (if the table can be rebuilt) |
| Two competing filter patterns | Projection, or a second table fed by an MV |
| Repeated aggregate over a dimension | Materialized view |
| Point lookups on a secondary ID | Bloom filter — this is the legitimate case |
| Joining a small dimension | `Dictionary`, not an index |
