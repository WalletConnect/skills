# Data types and codecs

## Contents
- [Why this matters more than it looks](#why-this-matters-more-than-it-looks)
- [Type selection table](#type-selection-table)
- [Nullable](#nullable)
- [LowCardinality](#lowcardinality)
- [Enum](#enum)
- [Numeric and money](#numeric-and-money)
- [Time](#time)
- [JSON and semi-structured data](#json-and-semi-structured-data)
- [Arrays, Maps, Nested](#arrays-maps-nested)
- [Codecs](#codecs)
- [Verifying your choices](#verifying-your-choices)

---

## Why this matters more than it looks

ClickHouse is I/O bound on most analytical queries. Column size translates almost linearly into scan time. Halving the on-disk size of the columns a query touches roughly halves the query time. Type and codec choices are therefore not cosmetic — they are the cheapest performance work available, and unlike the `ORDER BY`, most of them can be changed later with `ALTER`.

## Type selection table

| Data | Use | Not |
|---|---|---|
| Boolean flag | `UInt8` or `Bool` | `String` |
| Status, category, chain name (< 10k distinct) | `LowCardinality(String)` | `String` |
| Fixed known set that never changes | `Enum8` / `Enum16` | `String` |
| Hash / address (hex, fixed length) | `FixedString(N)` after stripping `0x`, or `String` | `LowCardinality(String)` |
| Counts, IDs | Smallest `UIntN` that fits | `Int64` by default |
| Money | `Decimal(38, 18)` or `UInt256` for wei | `Float64` |
| Ratios, scores | `Float32` if precision allows | `Float64` reflexively |
| Timestamp | `DateTime` (second) or `DateTime64(3)` (ms) | `String`, `UInt64` epoch |
| Date only | `Date` (2 bytes) or `Date32` | `DateTime` |
| IPv4 / IPv6 | `IPv4` / `IPv6` | `String` |
| UUID | `UUID` | `String` |
| Variable payload with unknown keys | `JSON` | one `String` blob |

## Nullable

Avoid it. `Nullable(T)` stores a separate `UInt8` mask column alongside the data, roughly doubling the read for narrow columns, and it blocks some optimizations (including use in certain index paths).

Use a sentinel instead:

```sql
-- Instead of
amount Nullable(Decimal(38, 18))

-- Prefer
amount Decimal(38, 18) DEFAULT 0
-- or, if 0 is a meaningful value and absence must be distinguishable,
amount Decimal(38, 18) DEFAULT 0,
has_amount UInt8 DEFAULT 0
```

Keep `Nullable` only where the distinction between "zero" and "unknown" is genuinely load-bearing for correctness — financial reconciliation is a legitimate case. **Never make a column in the `ORDER BY` nullable.**

## LowCardinality

`LowCardinality(String)` dictionary-encodes the column. Typical wins are 5–20x on repeated strings, plus faster `GROUP BY` because comparisons happen on dictionary positions.

- **Use below roughly 10,000 distinct values.** Chain names, statuses, currency codes, country codes, wallet names, error types.
- **Do not use above that.** Above ~100k distinct values it is actively slower than plain `String` — dictionary maintenance costs exceed the savings.
- It composes: `LowCardinality(Nullable(String))` is valid but inherits the `Nullable` penalty.
- Wrapping numeric types (`LowCardinality(UInt8)`) is rarely worth it; the raw type is already small.

Check whether a column qualifies:
```sql
SELECT uniqExact(status) FROM events;
```

## Enum

`Enum8` / `Enum16` is more compact than `LowCardinality` and validates at insert time — an unknown value is rejected.

That validation is the catch: adding a value requires an `ALTER TABLE ... MODIFY COLUMN`, and an insert with an unlisted value fails outright. Use `Enum` for genuinely closed sets (`'debit'`, `'credit'`). Use `LowCardinality(String)` for anything that might grow, which in practice is most things fed by an upstream system you do not control.

## Numeric and money

**Never use `Float` for money.** Floating point cannot represent decimal fractions exactly, and errors accumulate across aggregations. Use:

- `Decimal(38, 18)` for general fiat/crypto amounts, or
- `UInt256` for raw on-chain integer amounts (wei-style), scaled at query time, or
- `Decimal64(2)` for plain fiat cents.

For integers, pick the narrowest type that fits the domain. `UInt32` covers 4.29 billion — enough for most ID columns, and half the size of `UInt64`. The difference is real on billion-row tables.

## Time

- `DateTime` — 4 bytes, second resolution. The default choice.
- `DateTime64(3)` — 8 bytes, millisecond resolution. Use only if sub-second precision is actually needed.
- `Date` — 2 bytes. Excellent as a partition key and as a secondary ordering column.

A common and good pattern is to store both a precise timestamp and a materialized date column:

```sql
event_time DateTime CODEC(Delta, ZSTD(1)),
event_date Date MATERIALIZED toDate(event_time)
```

The `Date` column costs almost nothing after compression and makes partitioning and date-range filters clean.

Store timestamps in UTC. Attaching a timezone to the column type (`DateTime('UTC')`) documents intent and avoids server-timezone surprises.

## JSON and semi-structured data

The `JSON` type is now production-grade: it dynamically infers and stores subcolumns, so nested fields get columnar storage and per-field compression rather than being reparsed at query time.

Use it when the schema is **genuinely variable** — third-party webhook payloads, heterogeneous event metadata.

Do not use it as a shortcut for a schema you already know. Extract the fields you filter, join, or aggregate on into real typed columns. A hybrid is usually right:

```sql
event_type LowCardinality(String),
merchant_id UInt64,
amount Decimal(38, 18),
payload JSON                       -- everything else, rarely filtered
```

Never store JSON as a `String` and parse it at query time. That is the worst of both worlds.

## Arrays, Maps, Nested

- `Array(T)` is well-supported and fast. Good for tags, token lists, multi-value attributes.
- `Map(K, V)` is convenient but reads the whole map to access one key. If you repeatedly access specific keys, promote them to columns.
- `Nested` is effectively parallel arrays. Useful for repeated substructures (e.g. transfer legs within a transaction), but joins and array functions get verbose. Consider a separate table if you query the substructure independently.

## Codecs

Codecs apply before the general compression codec and exploit structure in the data. Specify as `CODEC(specialized, general)`.

| Codec | Use for | Example |
|---|---|---|
| `Delta` | Monotonic or slowly-changing values | timestamps, block numbers, sequential IDs |
| `DoubleDelta` | Near-constant-interval sequences | regular-interval metrics |
| `Gorilla` | Slowly-changing floats | gauges, prices sampled frequently |
| `T64` | Integers using a small part of their range | small ints stored in wide types |
| `ZSTD(1..3)` | General-purpose, the default choice | strings, most columns |
| `LZ4` | When CPU matters more than size | very hot columns |

Practical defaults:

```sql
event_time    DateTime        CODEC(Delta, ZSTD(1)),
block_number  UInt64          CODEC(DoubleDelta, ZSTD(1)),
merchant_id   UInt64          CODEC(ZSTD(1)),
amount        Decimal(38, 18) CODEC(ZSTD(1)),
status        LowCardinality(String),          -- already dictionary-encoded
payload       JSON            CODEC(ZSTD(3))  -- verbose, compresses well
```

Notes:
- `Delta` on a random-order column makes things *worse*. Only apply it where values are correlated with the sort order.
- `ZSTD(3)` and above trade meaningful CPU for modest size gains. Reserve for large, cold, verbose columns.
- Do not add codecs to `LowCardinality` columns; dictionary encoding already did the work.

## Verifying your choices

Measure rather than assume. Per-column compressed size:

```sql
SELECT
    name,
    type,
    formatReadableSize(sum(column_data_compressed_bytes))   AS compressed,
    formatReadableSize(sum(column_data_uncompressed_bytes)) AS uncompressed,
    round(sum(column_data_uncompressed_bytes)
        / nullIf(sum(column_data_compressed_bytes), 0), 2)  AS ratio
FROM system.parts_columns
WHERE active AND database = currentDatabase() AND table = 'events'
GROUP BY name, type
ORDER BY sum(column_data_compressed_bytes) DESC;
```

Sort by compressed size and work top-down — the largest three columns almost always contain all the available wins. A ratio below ~3 on a string column usually means a missing `LowCardinality`; a low ratio on a timestamp usually means a missing `Delta`.
