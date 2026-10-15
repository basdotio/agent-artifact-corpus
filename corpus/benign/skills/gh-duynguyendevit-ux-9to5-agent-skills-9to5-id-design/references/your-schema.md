# Local schema evidence

Repository observations are a starting point, not a live database inventory. Recheck
the target checkout and migration history before asserting a current schema fact.

## Corrected inventory interpretation

The earlier grep counted 68 NUMBER primary-key declarations, **not 68 verified identity
columns**. Recreated tables can also appear multiple times. A numeric datatype alone
does not identify its generator. The previous global "never used" counts for RAW,
SYS_GUID and UUIDv7 lacked a durable scan scope; do not repeat them as verified facts.

For the target table, inspect IDENTITY clauses, explicit sequences, DEFAULT expressions,
triggers, ORM mappings and application constructors. On a live authorized schema:

```sql
SELECT table_name, column_name, generation_type, sequence_name
FROM user_tab_identity_cols;

SELECT table_name, column_name, data_type, data_length, char_length, char_used
FROM user_tab_columns
WHERE table_name = :table_name;
```

Use the exact dictionary case: quoted lowercase objects do not appear under uppercase
names. SQL reference DDL is not proof of deployment.

## Outbox example

`common-outbox/files/outbox-oracle.sql` declares `outbox_id` and `aggregate_id` as
VARCHAR2(36). Inspect the application producer to determine each value's origin;
aggregate_id may be an externally supplied business identity, not a generated UUID.
The claim/cleanup indexes are keyed by producer/status/time, independent of the PK.

UUID text width is a structural cost, not evidence of a measured performance defect.
Changing aggregate identifiers affects contracts and referencing records, not just
storage. Keep existing serialization compatible during any approved migration.

## Measurement

```sql
SELECT index_name, blevel, leaf_blocks, distinct_keys, clustering_factor
FROM user_indexes
WHERE table_name = :table_name;

SELECT segment_name, segment_type, ROUND(bytes / 1024 / 1024, 1) AS mb
FROM user_segments
WHERE segment_name IN (
    SELECT index_name FROM user_indexes WHERE table_name = :table_name
);

SELECT sequence_name, cache_size, order_flag
FROM user_sequences;
```

Clustering factor estimates table-block visits when traversing index order. It is
not a direct measurement of insert cost, fragmentation or page splits. Combine it
with workload plans, logical reads, index space, insert latency and contention waits.
Measure actual value sizes with VSIZE when width matters.

Prefer the existing correct convention for a stable table. For a new foreign key,
use a numeric surrogate only if it has the required uniqueness, identity semantics
and referential constraint; its width alone is not enough. A key migration touches
referencing tables/indexes, event/API contracts, conversions and rollout compatibility.
