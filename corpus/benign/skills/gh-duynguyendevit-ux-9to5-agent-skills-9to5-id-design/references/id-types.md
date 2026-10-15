# ID families and trade-offs

## Identity and explicit sequences

Oracle identity columns use a sequence internally. An explicit sequence can be queried
before inserting the row, or allocated through an ORM optimizer. Choose identity when
insert-time generation fits; choose a sequence when preallocation is useful.

```sql
SELECT order_id_seq.NEXTVAL FROM dual;
```

Pros: simple uniqueness across sessions sharing the database, compact numeric values,
no application worker-ID registry, mature driver/ORM support.

Costs: database availability for fresh allocations, possible allocation round trips,
right-edge index contention under some workloads, and a namespace that independent
databases must coordinate if their records will be merged. Cache/allocation tuning can
reduce round trips; measure before treating generation as a bottleneck.

Sequence values are independent of transaction outcome. Gaps can follow rollbacks,
cache loss, deletes or reserved values. RAC `NOORDER` preserves uniqueness; it permits
out-of-order values across instances. `ORDER` orders allocation requests, not commits.
Multiple writers sharing the sequence do not need manually partitioned number ranges.
Oracle NUMBER is variable-length (1–22 bytes), not a fixed-width BIGINT.

## UUIDv4

A UUID is 128 bits; version 4 has 122 random bits after version/variant bits. Use a
reputable random generator and a database uniqueness constraint. No worker-ID
coordination is normally needed, but collision probability is not literally zero.

Pros: offline/distributed generation, broad tooling, no embedded creation timestamp.
Costs: 16-byte binary payload (36 ASCII characters as conventional text), scattered
index writes and possible cache/page-split overhead. InnoDB clustering consequences
differ from Oracle heap storage. Random keys can reduce right-edge hot spots; compare
measured throughput, waits and footprint instead of banning them on every busy table.

## Snowflake-style IDs

Typically a 64-bit layout combining timestamp, worker identity and per-time-unit
sequence; exact bit allocation is implementation-specific.

Pros: compact representation, local allocation, broadly time-local inserts.
Costs: globally unique worker assignment within the relevant namespace, clock rollback
handling, capacity per time unit, restart and stale-worker rules. StatefulSet ordinals
alone are not unique across multiple deployments. Generator recreation can reset a
sequence and collide. IDs from separate workers are not strict global event order.

Range allocation from a central service can be a valid alternative: it trades ordering,
gaps and service dependence against fewer round trips. Interleaved ranges do not imply
the same distribution or performance as uniformly random UUIDv4 keys.

## ULID and UUIDv7

Both are 128-bit, time-prefixed formats using a 48-bit millisecond timestamp.
ULID has an 80-bit randomness component and a 26-character Base32 representation.
UUIDv7 reserves version/variant bits and has 74 remaining bits available for randomness
and optional monotonic/sub-millisecond schemes described by RFC 9562.

Pros: distributed generation with time locality and no worker registry in random-based
implementations. Costs: clock assumptions, timestamp exposure and 16-byte binary keys.
ULID monotonic factories and UUIDv7 implementations differ; verify same-millisecond
and clock-rollback behavior. Neither format guarantees global commit order.

Store binary when driver/query conventions support it; test round-trip conversion and
binary sort order. UUIDv7 conventionally formats as 36 characters, ULID as 26; do not
use one format's text-length rule for the other.

## Sources

- Oracle sequence pseudocolumns and pre-insert NEXTVAL:
  https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Sequence-Pseudocolumns.html
- Sequence CACHE/ORDER/NOORDER semantics:
  https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/CREATE-SEQUENCE.html
- Oracle data types and storage:
  https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Data-Types.html
- UUID layouts and monotonicity options: https://www.rfc-editor.org/rfc/rfc9562.html
- ULID specification: https://github.com/ulid/spec
