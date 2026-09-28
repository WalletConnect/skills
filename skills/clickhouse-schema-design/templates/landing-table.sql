-- Template: streaming landing table fed by a ClickPipe (Kinesis shown; Kafka
-- swaps the metadata columns for _topic/_partition/_offset), plus one typed
-- consumer with dedup and a bounded backfill.
--
-- Create the landing table HERE, in your migration tool, and point the pipe at
-- it as an existing table (Terraform: managed_table = false). Map exactly the
-- five pipe-side columns; ch_timestamp is added by ClickHouse and must NOT be
-- in the pipe's column list (DEFAULT/MATERIALIZED on pipe columns is unsupported).

-- ============================================================================
-- 1. Landing table: raw body + source metadata, nothing else
-- ============================================================================
CREATE TABLE IF NOT EXISTS landing.orders_stream
(
    raw                     String CODEC(ZSTD(3)),        -- _raw_message
    kinesis_timestamp       DateTime64(3, 'UTC'),         -- _timestamp
    kinesis_stream          LowCardinality(String),       -- _stream
    kinesis_sequence_number String,                       -- _sequence_number
    kinesis_key             String                        -- _key
)
ENGINE = MergeTree
-- Serves: MVs (block-at-a-time, no pruning needed) and operators asking
-- "what arrived in the last N minutes". Time-first is correct for this table only.
ORDER BY (kinesis_timestamp, kinesis_sequence_number)
-- Choose ONE of the two lifecycles and delete the other:
--   (a) replay source / audit trail: keep forever, no PARTITION BY, no TTL.
--   (b) buffer for MVs, never queried directly:
-- PARTITION BY toDate(kinesis_timestamp)
-- TTL toDateTime(kinesis_timestamp) + INTERVAL 7 DAY
COMMENT 'ClickPipe destination. Raw JSON per record, parsed by landing.*_mv. Lifecycle: (a) replay source.';

-- Ingest timestamp, outside the pipe mapping. Existing rows get the ALTER time.
ALTER TABLE landing.orders_stream
    ADD COLUMN IF NOT EXISTS ch_timestamp DateTime64(3) MATERIALIZED now64(3);

-- ============================================================================
-- 2. Typed consumer table: business key, producer version, dedup on merge
-- ============================================================================
CREATE TABLE IF NOT EXISTS core.orders
(
    order_id      String,
    customer_id   String,
    status        LowCardinality(String),
    amount        Decimal(38, 18),
    created_at    DateTime64(3, 'UTC'),        -- immutable: safe partition key
    updated_at    DateTime64(3, 'UTC'),
    version       UInt64,                      -- producer's monotonic version
    ingested_at   DateTime64(3, 'UTC')
)
ENGINE = ReplacingMergeTree(version)
PARTITION BY toYYYYMM(created_at)
-- Serves: per-customer order history, point lookups by (customer_id, order_id).
-- The full key identifies one logical row, which ReplacingMergeTree requires.
ORDER BY (customer_id, order_id);

-- ============================================================================
-- 3. MV: parse raw -> typed. Use *OrNull / *OrZero on anything the producer
--    does not guarantee: a throwing MV fails the pipe's insert.
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS landing.orders_mv TO core.orders AS
SELECT
    JSONExtractString(raw, 'order_id')                              AS order_id,
    JSONExtractString(raw, 'customer_id')                           AS customer_id,
    JSONExtractString(raw, 'status')                                AS status,
    toDecimal256OrZero(JSONExtractString(raw, 'amount'), 18)        AS amount,
    parseDateTime64BestEffortOrZero(JSONExtractString(raw, 'created_at'), 3) AS created_at,
    parseDateTime64BestEffortOrZero(JSONExtractString(raw, 'updated_at'), 3) AS updated_at,
    JSONExtractUInt(raw, 'version')                                 AS version,
    kinesis_timestamp                                               AS ingested_at
FROM landing.orders_stream
WHERE JSONExtractString(raw, 'type') = 'order';   -- route by discriminator

-- ============================================================================
-- 4. Backfill rows that landed before the MV existed. No POPULATE.
--    Bound strictly below the MV creation time; chunk by month on large tables.
-- ============================================================================
-- INSERT INTO core.orders
-- SELECT <same expressions as the MV>
-- FROM landing.orders_stream
-- WHERE JSONExtractString(raw, 'type') = 'order'
--   AND kinesis_timestamp <  '<MV creation time>'
--   AND kinesis_timestamp >= '<MV creation time minus 1 month>';

-- ============================================================================
-- 5. Verify
-- ============================================================================
-- Redelivery on the landing table (at-least-once shows up here first):
-- SELECT JSONExtractString(raw, 'event_id') id, count() c FROM landing.orders_stream
-- WHERE kinesis_timestamp > now() - INTERVAL 7 DAY GROUP BY id HAVING c > 1;
--
-- Nothing rejected:
-- SELECT count() FROM landing.orders_stream_clickpipes_error;
--
-- Typed layer agrees with landing for a recent window:
-- SELECT count() FROM landing.orders_stream WHERE JSONExtractString(raw,'type')='order' AND toDate(kinesis_timestamp) = yesterday();
-- SELECT count() FROM core.orders FINAL WHERE toDate(ingested_at) = yesterday();
