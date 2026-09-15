# Query optimization and diagnosis

## Contents
- [Symptom to cause](#symptom-to-cause)
- [The core diagnostic](#the-core-diagnostic)
- [Reading EXPLAIN](#reading-explain)
- [system.query_log](#systemquery_log)
- [Part health](#part-health)
- [JOINs](#joins)
- [Query rewrites that reliably help](#query-rewrites-that-reliably-help)
- [Mutations and deletes](#mutations-and-deletes)

---

## Symptom to cause

| Symptom | Most likely cause | Go to |
|---|---|---|
| Query reads far more rows than it returns | `WHERE` does not hit an `ORDER BY` prefix | [Core diagnostic](#the-core-diagnostic) |
| `Memory limit exceeded` on `GROUP BY` | High-cardinality grouping key, or a JOIN materializing a huge right side | [JOINs](#joins) |
| `Too many parts` | Small frequent inserts, or over-granular partitioning | [Part health](#part-health) |
| Inserts slow or failing after a schema change | A materialized view's `SELECT` is throwing | `materialized-views.md` |
| Query fast on one node, slow on cluster | Distributed JOIN pulling data across shards | [JOINs](#joins) |
| Numbers wrong / duplicated | Reading a `ReplacingMergeTree` without `FINAL` or `argMax` | `table-engines.md` |
| Gradual slowdown over months | Partition count growth, or unmerged parts accumulating | [Part health](#part-health) |
| `ALTER` hangs forever | It is a mutation rewriting every part | [Mutations](#mutations-and-deletes) |

## The core diagnostic

Almost every "ClickHouse is slow" report resolves to one number: **rows read versus rows logically needed**.

```sql
SELECT
    query_duration_ms,
    formatReadableQuantity(read_rows) AS rows_read,
    formatReadableSize(read_bytes)    AS bytes_read,
    formatReadableSize(memory_usage)  AS memory,
    result_rows
FROM system.query_log
WHERE type = 'QueryFinish'
  AND event_time > now() - INTERVAL 1 HOUR
ORDER BY query_duration_ms DESC
LIMIT 10;
```

If `read_rows` is within an order of magnitude of the table's total row count while `result_rows` is small, the primary index was not used. The fix is a schema change, not a query tweak — go to `keys-and-partitions.md`.

If `read_rows` is already small and the query is still slow, the problem is compute: a JOIN, a high-cardinality `GROUP BY`, or expensive per-row functions.

## Reading EXPLAIN

```sql
EXPLAIN indexes = 1
SELECT sum(amount) FROM payments
WHERE merchant_id = 42 AND event_date >= '2026-01-01';
```

The output shows each index in play and, critically, `Granules: X/Y` — granules selected out of total. `1083/1083` means no pruning happened at all. `12/1083` means the index is doing its job.

Other forms worth knowing:

```sql
EXPLAIN PLAN actions = 1 <query>;     -- logical plan, what got pushed down
EXPLAIN PIPELINE <query>;             -- execution pipeline and parallelism
EXPLAIN ESTIMATE <query>;             -- estimated parts/rows/marks to read
```

## system.query_log

Find the expensive patterns rather than individual slow queries — `normalized_query_hash` groups structurally identical queries:

```sql
SELECT
    normalized_query_hash,
    any(query)                          AS sample,
    count()                             AS runs,
    round(avg(query_duration_ms))       AS avg_ms,
    formatReadableQuantity(avg(read_rows)) AS avg_rows_read,
    formatReadableSize(max(memory_usage))  AS peak_mem
FROM system.query_log
WHERE type = 'QueryFinish'
  AND event_time > now() - INTERVAL 7 DAY
GROUP BY normalized_query_hash
ORDER BY sum(query_duration_ms) DESC
LIMIT 20;
```

Sorting by *total* time rather than average surfaces the queries that actually cost the cluster — a 200ms query run 50,000 times a day matters more than a 40-second monthly report.

Failures:

```sql
SELECT event_time, query_duration_ms, exception, left(query, 200)
FROM system.query_log
WHERE type = 'ExceptionWhileProcessing'
  AND event_time > now() - INTERVAL 1 DAY
ORDER BY event_time DESC LIMIT 20;
```

## Part health

```sql
SELECT
    table,
    partition,
    count()                                  AS parts,
    sum(rows)                                AS rows,
    formatReadableSize(sum(bytes_on_disk))   AS size
FROM system.parts
WHERE active AND database = currentDatabase()
GROUP BY table, partition
ORDER BY parts DESC
LIMIT 20;
```

Healthy: a handful of parts per partition, each reasonably large. Unhealthy: dozens or hundreds of parts in one partition, or hundreds of partitions each holding a few thousand rows.

Causes and fixes:

- **Many small inserts.** Batch to 10k–100k+ rows, or enable `async_insert = 1` with `wait_for_async_insert = 0` and tune `async_insert_max_data_size`. This is the fix, not `Buffer` tables.
- **Over-granular partitioning.** Requires a rebuild with a coarser partition key.
- **Merges falling behind.** Check `system.merges` and `system.mutations`; may be a resource constraint rather than a schema problem.

Do **not** respond to this with scheduled `OPTIMIZE TABLE ... FINAL`. It forces a full merge of every partition, competes with normal merges, and grows superlinearly with table size until it takes longer than its own schedule interval. It is a one-off maintenance tool, not a cron job.

## JOINs

ClickHouse builds a hash table from the **right** table in memory. Put the small table on the right. This is the opposite reflex from some other engines and is the most common cause of `Memory limit exceeded`.

Preference order:

1. **`Dictionary` + `dictGet()`** for small, stable dimension lookups. Held in memory, no join at all, dramatically faster.
   ```sql
   SELECT dictGet('merchants_dict', 'name', merchant_id) AS merchant, sum(amount)
   FROM payments GROUP BY merchant_id;
   ```
2. **Denormalize at write time.** Write `merchant_name` into the fact table. Storage is cheap; `LowCardinality` makes it nearly free.
3. **Subquery with `IN`** instead of a join, when you only need filtering:
   ```sql
   WHERE merchant_id IN (SELECT merchant_id FROM merchants WHERE tier = 'enterprise')
   ```
4. **Filter before joining.** Push `WHERE` into a subquery on each side so the hash table is built from a reduced set.
5. **A real `JOIN`**, small table on the right, as the last resort.

On clusters, a join between two `Distributed` tables can ship data across shards. Use `GLOBAL JOIN` when the right side is small enough to broadcast, and co-locate by shard key when it is not.

## Query rewrites that reliably help

**Select only needed columns.** `SELECT *` on a 200-column table reads 200 column files. This matters far more in a columnar store than a row store.

**Filter on the raw key column, not a function of it.** `WHERE toDate(event_time) = '2026-01-01'` may prevent index use; `WHERE event_time >= '2026-01-01' AND event_time < '2026-01-02'` will not.

**Use `PREWHERE` for a cheap, highly selective filter** on a small column — it reads that column first and only reads the rest for surviving rows. Usually applied automatically, but worth forcing when the automatic choice is wrong.

**Approximate when exactness is not required.** `uniq()` is far cheaper than `uniqExact()`. `quantile()` beats `quantileExact()`. On dashboards this is almost always the right trade.

**Aggregate before joining**, not after.

**Use `LIMIT ... BY`** rather than window functions for per-group top-N.

**Prefer `argMax(a, b)` over a self-join** for latest-value lookups.

## Mutations and deletes

`ALTER TABLE ... UPDATE` and `ALTER TABLE ... DELETE` are asynchronous mutations that **rewrite every affected part**. On a large table this takes hours, competes with merges, and cannot be cancelled cleanly mid-part.

Monitor them:

```sql
SELECT database, table, mutation_id, command, parts_to_do, is_done, latest_fail_reason
FROM system.mutations
WHERE NOT is_done;
```

Alternatives, in order:

1. **`DROP PARTITION`** if the data to remove aligns with partitions. Metadata-only, instant.
2. **TTL** for age-based deletion.
3. **`ReplacingMergeTree` with a version and `is_deleted` column** for row-level updates and soft deletes — model changes as appends. See `table-engines.md`.
4. **Lightweight `DELETE`** (`DELETE FROM t WHERE ...`) marks rows deleted rather than rewriting parts immediately. Much cheaper than a mutation, but the rows still occupy space until merged, and it is not free at scale.
5. **Lightweight `UPDATE`** (`UPDATE t SET col = expr WHERE ...`, beta as of 25.x/26.x) writes a *patch part* holding only the changed columns and rows. Reads apply the patch immediately; merges fold it into the base parts later. Latency is that of an `INSERT ... SELECT`, not a rewrite. Requires the table settings `enable_block_number_column = 1` and `enable_block_offset_column = 1`; works on `MergeTree`, `ReplacingMergeTree`, and the collapsing engines, including `Shared*` on Cloud. Limits that keep it out of the routine path: cannot touch primary-key or partition-key columns, is designed for small updates (roughly under 10% of the table), adds read-side cost while patches are unmerged, disables skip indices and projections on patched parts, and each statement makes a part, so frequent small updates hit too-many-parts. And like every mutation, **materialized views do not see it**. Use it for occasional corrections on a table with no derived tables; keep versioned appends as the default.
6. **A real mutation**, accepted as a rare one-off with a maintenance window.

If GDPR-style deletion by user is a hard requirement, design for it up front: either partition by something that lets you drop cleanly, or use `ReplacingMergeTree` soft deletes from day one. Retrofitting it onto a plain `MergeTree` table with billions of rows is genuinely painful.
