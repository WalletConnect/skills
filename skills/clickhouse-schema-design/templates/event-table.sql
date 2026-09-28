-- Append-only event / log stream.
-- Replace <...> placeholders. Delete the commentary before shipping.

CREATE TABLE events
(
    -- Dimensions you filter on, in ORDER BY prefix order
    tenant_id       UInt64,
    event_type      LowCardinality(String),

    -- Time
    event_time      DateTime CODEC(Delta, ZSTD(1)),
    event_date      Date MATERIALIZED toDate(event_time),

    -- Measures
    duration_ms     UInt32 CODEC(T64, ZSTD(1)),

    -- High-cardinality identifiers: kept, but not in the key
    session_id      UUID,
    user_id         UInt64 CODEC(ZSTD(1)),

    -- Variable payload. Extract anything you filter on into a real column.
    properties      JSON CODEC(ZSTD(3)),

    -- Ingestion metadata, useful for debugging backfills
    ingested_at     DateTime DEFAULT now() CODEC(Delta, ZSTD(1))
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_date)
-- Serves: "all events for tenant X in a date range", optionally narrowed by type.
-- Does NOT serve: lookups by session_id or user_id alone -- those scan.
ORDER BY (tenant_id, event_type, event_date, event_time)
TTL event_date + INTERVAL 365 DAY DELETE
SETTINGS ttl_only_drop_parts = 1;

-- Optional: point lookups on a secondary ID.
-- Verify with EXPLAIN indexes = 1 before keeping this.
-- ALTER TABLE events ADD INDEX idx_session session_id TYPE bloom_filter(0.01) GRANULARITY 4;
