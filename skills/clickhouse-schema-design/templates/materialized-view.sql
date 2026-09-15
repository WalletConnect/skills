-- Incremental materialized view with an AggregatingMergeTree target,
-- plus the safe backfill sequence. Run the steps in this order.

-- ---------------------------------------------------------------
-- STEP 1: target table
-- ORDER BY must match the MV's GROUP BY exactly, or rows never collapse.
-- ---------------------------------------------------------------
CREATE TABLE events_daily
(
    tenant_id      UInt64,
    event_date     Date,
    event_type     LowCardinality(String),

    event_count    AggregateFunction(count),
    unique_users   AggregateFunction(uniq, UInt64),
    total_duration AggregateFunction(sum, UInt32),
    p99_duration   AggregateFunction(quantiles(0.99), UInt32)
)
ENGINE = AggregatingMergeTree
PARTITION BY toYYYYMM(event_date)
ORDER BY (tenant_id, event_date, event_type);

-- ---------------------------------------------------------------
-- STEP 2: the view. From this moment forward, new inserts are captured.
-- Create this BEFORE backfilling. Never use POPULATE on a live table.
-- ---------------------------------------------------------------
CREATE MATERIALIZED VIEW events_daily_mv TO events_daily AS
SELECT
    tenant_id,
    toDate(event_time) AS event_date,
    event_type,
    countState()                       AS event_count,
    uniqState(user_id)                 AS unique_users,
    sumState(duration_ms)              AS total_duration,
    quantilesState(0.99)(duration_ms)  AS p99_duration
FROM events
GROUP BY tenant_id, event_date, event_type;

-- ---------------------------------------------------------------
-- STEP 3: backfill history, in bounded chunks, strictly BELOW the
-- cutoff timestamp from step 2. Overlap causes silent double-counting.
-- Repeat per month; verify each chunk before moving to the next.
-- ---------------------------------------------------------------
INSERT INTO events_daily
SELECT
    tenant_id,
    toDate(event_time) AS event_date,
    event_type,
    countState(),
    uniqState(user_id),
    sumState(duration_ms),
    quantilesState(0.99)(duration_ms)
FROM events
WHERE event_time >= '2026-08-01 00:00:00'
  AND event_time <  '2026-09-01 00:00:00'
GROUP BY tenant_id, event_date, event_type;

-- ---------------------------------------------------------------
-- STEP 4: verify. These two should agree.
-- ---------------------------------------------------------------
-- SELECT count() FROM events WHERE toDate(event_time) = '2026-08-15';
-- SELECT countMerge(event_count) FROM events_daily WHERE event_date = '2026-08-15';

-- ---------------------------------------------------------------
-- STEP 5: read interface. Consumers use this, never the state columns.
-- ---------------------------------------------------------------
CREATE VIEW events_daily_readable AS
SELECT
    tenant_id,
    event_date,
    event_type,
    countMerge(event_count)             AS events,
    uniqMerge(unique_users)             AS users,
    sumMerge(total_duration)            AS total_duration_ms,
    quantilesMerge(0.99)(p99_duration)  AS p99_ms
FROM events_daily
GROUP BY tenant_id, event_date, event_type;
