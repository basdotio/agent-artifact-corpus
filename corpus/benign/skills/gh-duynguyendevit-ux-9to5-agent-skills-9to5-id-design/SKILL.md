---
name: 9to5-id-design
description: Choose and review primary-key ID strategy — database identity/sequence versus application UUID/ULID/UUIDv7/Snowflake, index locality, Oracle storage, generator lifetime, and exposure. Use for new keys, UUID versus auto-increment discussions, schema or migration review, IDs in APIs, or suspected duplicate or costly ID generation.
license: MIT
metadata:
  version: "1.0.1"
---

# ID Design

## Example output

Illustrative design review, not a finding about the current schema.

```text
Table: example_jobs
Requirement: two services share one Oracle database; ID needed before insert.
Candidate: explicit sequence, allocated with NEXTVAL before parent/child inserts.
Reason: shared uniqueness and preallocation without a worker-ID registry.
Trade-off: allocation depends on database availability; gaps are expected.
Ordering: allocation order is not commit order.
Storage: NUMBER is variable-length; no fixed 8-byte assumption.
Migration: add sequence/default and verify ORM allocation through the migration workflow.
Performance: not measured; no claim of an insert-throughput improvement.
```

Choose from requirements and measurements: uniqueness scope, who allocates the ID,
whether it must exist before insertion, ordering requirements, storage, and exposure.
Read `references/id-types.md` for examples and trade-offs, and
`references/your-schema.md` before making claims about the local repositories.

## Selection

| Requirement | Candidate | Check |
|---|---|---|
| Writers share one Oracle database | Identity or explicit sequence | Multiple sessions/RAC instances can safely use the same sequence; no manual writer ranges required. |
| Parent/children or event need an ID before insert | Explicit sequence NEXTVAL, optionally ORM allocation, or application ID | Preallocation is supported; identity retrieval and explicit sequence allocation differ. |
| Independent/disconnected producers need global IDs | UUIDv4, UUIDv7, ULID; possibly Snowflake | Random collision model or worker/clock coordination; retain a uniqueness constraint. |
| Prefer time-local index inserts | UUIDv7/ULID or sequence | Approximate locality is not global generation/commit order; evaluate right-edge contention. |
| Compact 64-bit application ID | Snowflake-style generator | Worker-ID ownership, clock rollback, sequence exhaustion and restart behavior. |
| Existing key crosses API/event boundaries | Keep it if its namespace and contract are adequate | A database counter can be a valid external identifier; no automatic migration requirement. |

## Oracle allocation and ordering

```sql
-- ID can be allocated before constructing or inserting parent and child records.
SELECT order_id_seq.NEXTVAL FROM dual;
-- Bind that value into both inserts in the business transaction.
```

Sequence allocation is independent of transaction commit/rollback. Gaps are normal.
Caching reduces allocation overhead but may lose unused cached values on failure.
`NOORDER` in RAC does not imply uniqueness risk. `ORDER` orders requests for sequence
values, not transaction commits or business events. Avoid claiming inserts always
arrive in sequence order or that sequence counters inherently serialize whole
transactions/create row-lock deadlocks. Measure the actual contention and workload.

## Storage on Oracle heap tables

| Representation | Payload characteristics |
|---|---|
| `NUMBER` | Variable length, 1–22 bytes; depends on value/precision, not a fixed 8-byte integer. |
| `RAW(16)` | 16 bytes for a full UUID/ULID binary value; validate byte ordering and conversion. |
| `VARCHAR2(36 BYTE)` UUID text | 36 bytes for conventional ASCII UUID text, plus storage overhead. |
| `CHAR(26 BYTE)` ULID text | Fixed 26-byte ASCII field; `CHAR(26 CHAR)` allows character semantics, not automatically 104 stored bytes. |

Use `VSIZE`, column metadata, segment statistics and driver mappings to compare real
costs. Wider keys affect the PK index, foreign-key columns and their indexes. Oracle
heap secondary indexes store ROWID, not an implicit copy of the primary key; IOTs
have different organization. Binary storage is often compact, but text can be an
intentional compatibility choice rather than a correctness failure.

## Generator and performance review

- Stateful generators need a safe lifetime and concurrency model. Recreating a
  Snowflake generator with the same worker/timestamp/sequence can collide.
- Do not assume all UUID libraries require an application singleton: check the actual
  API, entropy source and monotonic behavior. Benchmark before alleging CPU waste.
- UUIDv4 scatters index writes; sequential/time-prefixed keys improve locality but
  can concentrate concurrent writes. Neither is universally best for high-write Oracle.
- UUIDv7/ULID are time-prefixed, not global ordering guarantees. Clocks may differ or
  move backwards. Generator-specific monotonic behavior must be checked.
- `SYS_GUID()` returns a globally unique RAW value; do not equate its implementation
  or distribution with UUIDv4 without evidence.
- Reverse-key indexes can distribute monotonically increasing key writes but remove
  ordinary value-ordered range access. Apply only after measuring the trade-off.

## Exposure and workflow

1. Read the real DDL and generator/ORM mapping. Distinguish NUMBER from IDENTITY.
2. Establish uniqueness scope, offline needs and any pre-insert allocation requirement.
3. Verify format, stored width, foreign keys and generator lifecycle.
4. Measure index/insert behavior before recommending a PK migration.
5. Explain exposure: counters enable enumeration and may suggest volume; time prefixes
   disclose approximate creation time. Neither proves exact volume or replaces access
   control. Opaque IDs do not prevent IDOR without authorization.
6. State migration scope: referencing tables, indexes, serialization, APIs, compatibility,
   rollout and rollback. A stable existing key is not a defect merely because another
   format is newer.
7. Hand schema changes to `9to5-sql-migration`; index decisions to `9to5-oracle-index`;
   event-key consequences to `9to5-kafka`.
