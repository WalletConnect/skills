# Streaming ingestion: ClickPipes, Kinesis, Kafka

## Contents
- [What ClickPipes is](#what-clickpipes-is)
- [The landing-table pattern](#the-landing-table-pattern)
- [Virtual columns](#virtual-columns)
- [Who owns the landing table](#who-owns-the-landing-table)
- [Delivery semantics and dedup](#delivery-semantics-and-dedup)
- [Batching, parts, and latency](#batching-parts-and-latency)
- [Start position and replay](#start-position-and-replay)
- [Authentication and cross-account Kinesis](#authentication-and-cross-account-kinesis)
- [Error table and system.clickpipes_log](#error-table-and-systemclickpipes_log)
- [Downstream materialized views](#downstream-materialized-views)
- [ClickHouse Cloud specifics that bite audits](#clickhouse-cloud-specifics-that-bite-audits)
- [Audit checklist for a pipe-fed table](#audit-checklist-for-a-pipe-fed-table)

---

## What ClickPipes is

ClickPipes is ClickHouse Cloud's managed ingestion service. It runs outside the database as its own compute (sized in replicas, CPU millicores, and memory), reads from a source, and issues ordinary `INSERT`s into a destination table. Streaming sources: Kafka and Kafka-compatible (Confluent, Redpanda, MSK, Event Hubs, WarpStream), Amazon Kinesis, Pub/Sub. Also object storage (S3, GCS, Azure Blob) and CDC (Postgres, MySQL, MongoDB).

From the database's point of view a pipe is just a user. In `system.query_log` its inserts appear as user `clickpipe:<service-uuid>:<pipe-uuid>` with `http_user_agent = 'clickpipes/v1 (type:kinesis; id:...)'`. That is how you find them.

Three consequences that shape every design decision below:

1. **The pipe decides the batch size and cadence, not you.** `async_insert`, `max_insert_block_size`, and every other insert-side setting in this skill's other files do not apply. You tune the pipe (memory, replicas) or the destination table, not the insert.
2. **The pipe knows only the columns it was told to map.** Everything else about the table is the database's business.
3. **A pipe is a long-lived consumer with a position.** Recreating it is not a no-op: it either skips records or replays them.

## The landing-table pattern

Do not point a pipe at a typed, business-shaped table. Land the raw message plus source metadata in a thin table, and do all parsing in materialized views downstream.

```sql
CREATE TABLE landing.orders_stream
(
    raw                     String CODEC(ZSTD(3)),      -- _raw_message: the full JSON
    kinesis_timestamp       DateTime64(3, 'UTC'),       -- _timestamp: approximate arrival
    kinesis_stream          LowCardinality(String),     -- _stream
    kinesis_sequence_number String,                     -- _sequence_number
    kinesis_key             String,                     -- _key: partition key
    ch_timestamp            DateTime64(3) MATERIALIZED now64(3)   -- added by ALTER, see ownership
)
ENGINE = MergeTree
-- Time-first is correct here: the only readers are MVs (which see blocks, not the table)
-- and operators asking "what arrived in the last N minutes".
ORDER BY (kinesis_timestamp, kinesis_sequence_number);
```

Why raw-first:

- **Schema drift is the normal case.** Producers add fields, rename them, and ship both camelCase and snake_case for a while. A `String` column absorbs all of that; a typed pipe mapping fails the row into the error table.
- **Replay is free.** When you find a parsing bug or need a new typed table, `INSERT INTO typed SELECT ... FROM landing WHERE kinesis_timestamp BETWEEN ...` rebuilds it without touching the source stream, whose retention is hours or days.
- **One pipe fans out to many consumers.** A single landing table can feed a payments table, a merchants table, and an events table through separate MVs, each with its own `ORDER BY`. See `materialized-views.md`, Null-table fan-out — a landing table is that pattern with the raw rows kept.

Rules for the landing table itself:

- `ORDER BY (<arrival timestamp>, <sequence number or (partition, offset)>)`. This is the one place in this skill where time-first is right by default.
- Keep it thin. Five or six columns. Anything derived from `raw` belongs in a downstream MV, or at most in a `MATERIALIZED` column you add yourself.
- `PARTITION BY` only if you will set a TTL. A landing table that is a buffer for MVs (nothing queries it directly) should get `PARTITION BY toDate(ts)` plus `TTL ts + INTERVAL 7 DAY`. A landing table that is also your replay source and audit trail should keep everything and stay unpartitioned or monthly.
- Compress `raw` hard. It is 70–90% of the table. `CODEC(ZSTD(3))` is the right default; it is written once and read only by MVs and backfills.
- Never `Nullable` on a landing column. The pipe always supplies every mapped field.

## Virtual columns

These are the only source fields a streaming pipe can map besides the message body. Map them explicitly in the pipe's field mappings; use the types shown.

**Kinesis**

| Virtual column | Type | Meaning |
|---|---|---|
| `_raw_message` | `String` | Full record payload |
| `_timestamp` | `DateTime64(3)` | Approximate arrival timestamp at Kinesis |
| `_stream` | `String` | Stream name — worth `LowCardinality` |
| `_sequence_number` | `String` | Per-shard monotonic sequence; a 56-digit decimal, so it stays `String` |
| `_key` | `String` | Partition key set by the producer |

**Kafka and compatible**

| Virtual column | Type | Meaning |
|---|---|---|
| `_raw_message` | `String` | Full message (JSON only recommended) |
| `_timestamp` | `DateTime64(3)` | Message timestamp |
| `_topic` | `String` | Topic |
| `_partition` | `Int32` | Partition |
| `_offset` | `Int64` | Offset within the partition |
| `_key` | `String` | Message key; `_key.a.b` extracts a field from a structured key |
| `_header_keys` / `_header_values` | `Array(String)` | Parallel arrays of record headers |

For Kafka, `(_partition, _offset)` is the natural uniqueness key and the natural second ordering column after the timestamp.

Formats: JSON for both; Kafka also supports Avro via a schema registry and Protobuf; Kinesis supports Protobuf via an uploaded descriptor. With `_raw_message` mapped to a `String`, the pipe does not enforce a schema on the body, which is the point of the landing pattern.

## Who owns the landing table

A pipe can create its destination (`managed_table = true` in Terraform; "create new table" in the console) or write into a table that already exists. Prefer the second. Create the landing table in your migration tool, then point the pipe at it. This keeps the schema in version control, decouples migration order from pipe creation, and makes the pipe's column list a pure mapping rather than a DDL source of truth.

Whichever way it was created, the pipe treats its mapped columns as a contract:

- **Every column the pipe declares must have a source mapping.** You cannot declare a column on the pipe side and leave it to a `DEFAULT`; `DEFAULT` expressions on pipe-declared columns are unsupported.
- **Columns the pipe does not know about are fine.** Add them with a plain `ALTER TABLE ... ADD COLUMN` on the database side. The standard use is an ingest timestamp: `ch_timestamp DateTime64(3) MATERIALIZED now64(3)`. The pipe never sees it; ClickHouse fills it on every insert. Existing rows get the value at the time of the `ALTER`, not their true arrival time.
- **Never rename or drop a mapped column, and never change its type to something the mapped value cannot be cast to.** The pipe's next insert fails, and every record goes to the error table until you fix it.
- **`ORDER BY` and `PARTITION BY` cannot change**, as on any MergeTree table. If the landing key is wrong, the fix is a new table, a new pipe (or a repointed one), a backfill from the old table, and then a swap.
- **Adding a materialized view downstream is invisible to the pipe** until the MV throws. Then the pipe's insert fails. See the next section.

## Delivery semantics and dedup

Streaming pipes are **at-least-once**. A pipe restart, a rebalance, a scaling event, or a recreation with an early start position will redeliver records the destination already has. The database's insert-block deduplication (`replicated_deduplication_window`, default 10,000 blocks / 1 hour) only catches a byte-identical block replayed inside that window, which covers a retried insert and nothing else. High-throughput pipes churn through the window fast; widen it if you rely on it at all.

So: **the landing table will contain duplicates eventually, and nothing downstream may assume otherwise.** Handle it once, at the first typed table:

```sql
-- Typed table keyed on the business identity of a record, versioned by the
-- producer's own version if it has one, else by arrival time.
CREATE TABLE core.orders
(
    order_id     String,
    version      UInt64,            -- from the message; monotonic per order_id
    ...
    ingested_at  DateTime64(3)
)
ENGINE = ReplacingMergeTree(version)
PARTITION BY toYYYYMM(created_at)      -- an immutable column, never the version
ORDER BY (customer_id, order_id);      -- the full key must identify one logical row
```

Two things the skill's `ReplacingMergeTree` guidance already says, which matter doubly here: read with `FINAL` or `argMax` (duplicates survive until a merge), and never derive the partition key from a column that changes between versions (the redelivered copy lands in another partition and never collapses).

Check the landing table for redelivery directly — it is the fastest way to learn whether the pipe has been restarting:

```sql
SELECT JSONExtractString(raw, 'eventID') AS id, count() AS copies
FROM landing.orders_stream
WHERE kinesis_timestamp > now() - INTERVAL 7 DAY
GROUP BY id HAVING copies > 1
ORDER BY copies DESC LIMIT 20;
```

## Batching, parts, and latency

A streaming pipe flushes a batch when it reaches roughly 100,000 rows or ~30MB per GB of pipe memory, **or after 5 seconds**, whichever comes first. On a low-volume stream the 5-second timer always wins, so you get an insert every few seconds with a handful of rows in it. That is expected, not a misconfiguration. End-to-end latency from arrival to queryable is then a few seconds; `ch_timestamp - kinesis_timestamp` measures it directly.

Small frequent inserts mean many small parts. Background merges keep up comfortably at hundreds of inserts per hour. Signs they are not: `system.parts` shows hundreds of active parts per partition, or `Too many parts` appears in `system.clickpipes_log`. Fixes, in order:

1. Give the pipe more memory. Larger blocks per flush, fewer parts. This is the tuning knob `async_insert` would be on a normal client.
2. Coarsen the landing table's partitioning. Daily partitions multiply the part count by the number of days receiving late data.
3. Reduce the number of MVs firing per insert. Each MV adds its own parts in its own target table on every batch.
4. Do not schedule `OPTIMIZE ... FINAL`. Same rule as everywhere else.

Scaling the pipe horizontally (more replicas) helps throughput, not part count. Kafka pipes work best with roughly as many consumers as partitions; a Kinesis pipe with one shard has nothing to parallelise. Two or more replicas is what gives the pipe availability-zone redundancy.

## Start position and replay

The start position is set once, at creation, and ignored afterwards:

- **Kinesis**: `LATEST` (only new records) or `TRIM_HORIZON` (everything still in the stream's retention, 24 hours by default, configurable up to 365 days).
- **Kafka**: earliest or latest offset, or a timestamp.

This makes pipe recreation a data decision, not an infrastructure one. Recreating with `LATEST` loses whatever arrived while the pipe was gone. Recreating with `TRIM_HORIZON` replays the whole retention window, which lands as duplicates in the landing table and is only harmless because the typed layer deduplicates. Before recreating a pipe: note the last `kinesis_timestamp` / `_offset` in the landing table, choose the start position deliberately, and verify counts afterwards.

Protect production pipes from accidental recreation. In Terraform, `lifecycle { prevent_destroy = true }` on every `clickhouse_clickpipe`.

The pipe's live position is visible in the database. A Kinesis pipe keeps a checkpoint table in the destination database named `kinesis_clickpipe_<pipe-uuid>`, engine `KeeperMap`, with one row per shard: `(shard_id, sequence_number)`. Read it to see exactly where the pipe is; compare its `sequence_number` with `max(kinesis_sequence_number)` in the landing table to confirm they agree. Never drop, rename, or write to it: it is the consumer offset, and losing it forces the pipe back to its configured start position. These tables are pipe internals, not schema, and an audit should ignore them (the same goes for the `<table>_clickpipes_error` siblings).

Kinesis enhanced fan-out gives the pipe a dedicated 2MB/s read pipe per shard instead of sharing the 5 reads/second/shard limit with other consumers. Turn it on when the stream has other consumers (Firehose, Lambda) and the pipe starts falling behind; it costs extra and needs `RegisterStreamConsumer` / `SubscribeToShard` permissions.

## Authentication and cross-account Kinesis

Two options: **IAM credentials** (an access key pair for a user with read permissions on the stream) or **IAM role** (a role in the stream's account whose trust policy allows ClickHouse Cloud's AWS account to assume it). Prefer the role: no long-lived secret, and it is the only way to read a stream in another account.

The role or user needs, on the stream ARN: `DescribeStream`, `GetShardIterator`, `GetRecords`, `ListShards`, `SubscribeToShard`, `DescribeStreamConsumer`, `RegisterStreamConsumer`, `DeregisterStreamConsumer`, plus `ListStreams` on `*` (used during pipe validation, cannot be scoped). If the stream is KMS-encrypted, `kms:Decrypt` on the key, scoped with `kms:ViaService = kinesis.<region>.amazonaws.com`.

Two AWS constraints worth stating to anyone designing the upstream:

- **ClickPipes reads cross-account and cross-region.** A service in `eu-central-1` can consume a stream in `us-east-1` in another account.
- **DynamoDB Streams to Kinesis is same-region only.** A DynamoDB table can only feed a Kinesis stream in its own region. So a multi-region DynamoDB setup needs one stream per region and one pipe per stream, all writing to the same landing table. Global tables replicate across regions, so stream them from **one** region only or every write arrives N times.

## Error table and system.clickpipes_log

Two places to look when rows are missing.

**`<destination>_clickpipes_error`** is created by the pipe next to the destination table. It receives records that failed to parse or insert (schema mismatch, type cast failure, an MV throwing), with a 7-day TTL:

```
error_timestamp   DateTime
error_type        LowCardinality(String)
error_msg         String
record_key        String
record_value      String        -- the original message; replay it from here
record_timestamp  DateTime64(3)
record_partition  Int32
record_offset     Int64
```

An empty error table is the normal state. Anything in it is a schema or MV bug, and since `record_value` holds the full message, you can reinsert the fixed rows straight from it inside the 7 days.

**`system.clickpipes_log`** holds operational events (connectivity, throttling, `Too many parts`, auth failures), also 7 days, keyed by `clickpipe_id`.

Monitoring queries worth putting on a dashboard:

```sql
-- Freshness: how far behind is the landing table?
SELECT now() - max(kinesis_timestamp) AS lag_seconds FROM landing.orders_stream;

-- Ingest latency distribution (needs the MATERIALIZED ch_timestamp column)
SELECT quantiles(0.5, 0.99)(ch_timestamp - kinesis_timestamp)
FROM landing.orders_stream WHERE kinesis_timestamp > now() - INTERVAL 1 DAY;

-- Pipe insert cadence and batch size
SELECT toStartOfHour(event_time) AS h, count() AS inserts, avg(written_rows) AS rows_per_insert
FROM system.query_log
WHERE type = 'QueryFinish' AND query_kind = 'Insert' AND user LIKE 'clickpipe:%'
  AND has(tables, 'landing.orders_stream') AND event_time > now() - INTERVAL 1 DAY
GROUP BY h ORDER BY h;

-- Anything rejected?
SELECT error_type, count(), max(error_timestamp), any(error_msg)
FROM landing.orders_stream_clickpipes_error GROUP BY error_type;

-- Operational errors
SELECT event_time, log_level, error_type, message
FROM system.clickpipes_log WHERE log_level IN ('Error', 'Warning')
ORDER BY event_time DESC LIMIT 50;
```

Alert on lag (the pipe stopped) and on a non-zero error table (a schema or MV change broke ingestion), not on insert count, which is noisy on low-volume streams.

## Downstream materialized views

Everything in `materialized-views.md` applies; three patterns are specific to a landing table.

**Route by a field in the payload.** One landing table, one MV per consumer, each filtering on a discriminator:

```sql
CREATE MATERIALIZED VIEW buy_xp.events_mv TO buy_xp.events AS
SELECT
    toUUID(JSONExtractString(raw, 'event_id'))             AS event_id,
    JSONExtractString(raw, 'payment_id')                    AS payment_id,
    JSONExtractString(raw, 'event_type')                    AS event_type,
    parseDateTime64BestEffort(JSONExtractString(raw, 'ts')) AS ts,
    JSONExtractRaw(raw, 'payload')                          AS payload_raw,
    kinesis_timestamp                                       AS ingested_at
FROM landing.actor_events
WHERE JSONExtractString(raw, 'actor') = 'BUY_XP';
```

Every MV on the landing table parses `raw` on every insert. Ten MVs means ten `JSONExtract` passes per batch. Cheap at hundreds of rows per batch; measure at hundreds of thousands, and if it matters, extract the discriminator once into a `MATERIALIZED` column on the landing table so the `WHERE` is a column compare.

**Unwrap envelopes.** CloudWatch Logs subscriptions, SNS, and similar deliver one record wrapping N events. Land the envelope with a short TTL, `ARRAY JOIN` it into a per-event table, and skip control messages:

```sql
CREATE MATERIALIZED VIEW landing.logs_unwrap_mv TO landing.log_events AS
SELECT
    JSONExtractString(ev, 'id')                                  AS event_id,
    fromUnixTimestamp64Milli(JSONExtractInt(ev, 'timestamp'))    AS event_time,
    JSONExtractString(raw, 'logGroup')                           AS log_group,
    JSONExtractString(ev, 'message')                             AS message
FROM landing.logs_envelope
ARRAY JOIN JSONExtractArrayRaw(raw, 'logEvents') AS ev
WHERE JSONExtractString(raw, 'messageType') = 'DATA_MESSAGE';
```

**Backfill after adding an MV.** The MV sees only new blocks. Rows already in the landing table need an explicit `INSERT INTO typed SELECT ... FROM landing WHERE kinesis_timestamp < '<mv creation time>'`. `POPULATE` with a `TO` table is not allowed on current Cloud versions and would race the pipe anyway. Overlap with the live window produces duplicates; that is acceptable only because the typed table is a `ReplacingMergeTree` keyed on business identity. If it is a plain `MergeTree`, bound the backfill strictly below the MV creation time.

A broken MV breaks the pipe: if the `SELECT` throws on some record (a `toUUID` on a malformed id, a `JSONExtractInt` on a string), the whole insert fails and the batch lands in the error table. Test every new MV `SELECT` against a sample of `raw` before creating it, and prefer the `OrNull` / `OrZero` function variants (`toUUIDOrNull`, `toUInt64OrZero`) on fields the producer does not guarantee.

## ClickHouse Cloud specifics that bite audits

- `SHOW CREATE TABLE` shows `ENGINE = SharedMergeTree('/clickhouse/tables/{uuid}/{shard}', '{replica}')` or `SharedReplacingMergeTree(...)`. That is what you get when you wrote `MergeTree`; do not "fix" it, and do not write `Replicated*` or `ON CLUSTER` on Cloud.
- `system.parts_columns` and `system.columns` byte counts can read **zero** for some SharedMergeTree tables. Use `system.parts` (`bytes_on_disk`, `data_uncompressed_bytes`, `rows`) or `system.tables` (`total_bytes`, `total_rows`) for sizes, and treat a 0-byte per-column result as "unknown", not "empty".
- `_block_offset` and similar `_`-prefixed columns appearing in `system.parts_columns` are engine internals, not schema.
- `kinesis_clickpipe_<uuid>` (`KeeperMap`) tables and `<table>_clickpipes_error` tables are created by ClickPipes in the destination database. Leave them alone and exclude them from audits and from any "drop everything in this schema" migration.
- A pipe's inserts count against the service's compute like any other insert. Idle services scale down; a pipe flushing every 5 seconds keeps the service awake. Budget accordingly.

## Audit checklist for a pipe-fed table

Run through this in Mode B whenever a table is a ClickPipes destination, on top of the normal checks. A table is pipe-fed if `system.query_log` shows a `clickpipe:` user inserting into it, or a `<name>_clickpipes_error` sibling exists.

| Check | Expected | If not |
|---|---|---|
| Body stored as `raw String`, parsing in MVs | Yes | 🔴 if typed columns are mapped directly from the stream and the producer schema is not frozen |
| `ORDER BY (arrival_ts, sequence)` | Yes | 🟡 anything else; the readers are MVs, so a business key buys nothing here |
| Mapped columns `Nullable` | No | 🟡 drop `Nullable`; the pipe always supplies them |
| `raw` codec | `ZSTD(3)` or better | 🟡 `ALTER ... MODIFY COLUMN raw String CODEC(ZSTD(3))`, applies to new parts |
| Ingest timestamp column | `MATERIALIZED now64(3)`, added by `ALTER`, not in the pipe mapping | 🟢 add it; it is the only way to measure latency |
| TTL | Present if the table is a buffer; absent if it is the replay source | 🟢 decide which it is and say so in a `COMMENT` |
| Downstream dedup | First typed table is `ReplacingMergeTree` on business identity | 🔴 without it, every pipe restart double-counts |
| Duplicate probe on landing | Zero or near-zero | 🟡 the pipe is restarting; check `system.clickpipes_log` |
| Error table | Empty | 🔴 rows present means ingestion is currently dropping data |
| Terraform | `prevent_destroy = true`, `managed_table = false` with the table owned by migrations | 🟡 |
| Global DynamoDB tables | Streamed from one region only | 🔴 otherwise every write is duplicated per region |
