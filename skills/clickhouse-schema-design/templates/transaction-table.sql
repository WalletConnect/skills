-- Records that get corrected or updated: keep the latest version per entity.
-- Replace <...> placeholders. Delete the commentary before shipping.

CREATE TABLE transactions
(
    -- Entity identity. Must be fully contained in ORDER BY for dedup to work.
    tenant_id       UInt64,
    transaction_id  UUID,

    -- Mutable fields
    status          LowCardinality(String),
    amount          Decimal(38, 18),
    currency        LowCardinality(String),

    -- Immutable: safe to partition on. Do NOT partition on updated_at --
    -- an update crossing a month boundary would create a second surviving row.
    created_at      DateTime CODEC(Delta, ZSTD(1)),
    created_date    Date MATERIALIZED toDate(created_at),

    -- Version column: highest wins on merge
    updated_at      DateTime CODEC(Delta, ZSTD(1)),

    -- Soft delete
    is_deleted      UInt8 DEFAULT 0
)
ENGINE = ReplacingMergeTree(updated_at, is_deleted)
PARTITION BY toYYYYMM(created_date)
ORDER BY (tenant_id, transaction_id);

-- Dedup is eventual: two versions coexist until parts merge.
-- Never let consumers query the raw table. Expose this view instead.
CREATE VIEW transactions_current AS
SELECT
    tenant_id,
    transaction_id,
    argMax(status,     updated_at) AS status,
    argMax(amount,     updated_at) AS amount,
    argMax(currency,   updated_at) AS currency,
    argMax(created_at, updated_at) AS created_at,
    max(updated_at)                AS updated_at
FROM transactions
GROUP BY tenant_id, transaction_id
HAVING argMax(is_deleted, updated_at) = 0;

-- Alternative read path, sometimes faster on narrow filters:
--   SELECT * FROM transactions FINAL WHERE tenant_id = 42
--   SETTINGS do_not_merge_across_partitions_select_final = 1;
