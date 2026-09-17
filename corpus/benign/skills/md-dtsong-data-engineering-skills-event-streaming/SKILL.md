---
name: event-streaming
description: "Use this skill when building real-time or near-real-time data pipelines. Covers Kafka, Flink, Spark Streaming, Snowpipe, BigQuery streaming, materialized views, and batch-vs-streaming decisions. Common phrases: \"real-time pipeline\", \"Kafka consumer\", \"streaming vs batch\", \"low latency ingestion\". Do NOT use for batch integration patterns (use data-integration) or pipeline orchestration (use data-pipelines)."
model:
  preferred: sonnet
  acceptable: [sonnet, opus]
  minimum: sonnet
  allow_downgrade: false
  reasoning_demand: medium
version: 1.0.0
---

# Streaming Data Skill

Expert guidance for real-time and near-real-time data pipelines: continuous stream processing, event-driven architectures, and batch-vs-streaming decisions.

## When to Use

Activate when:
- Building or troubleshooting Kafka pipelines (producers, consumers, Connect)
- Implementing stream processing with Flink, Spark Streaming, or Kafka Streams
- Designing event-driven architectures or real-time analytics
- Configuring warehouse streaming ingestion (Snowpipe, BigQuery Storage Write API)
- Creating materialized views or dynamic tables
- Evaluating latency requirements (batch vs streaming)
- Handling schema evolution, exactly-once semantics, or idempotent processing
- Debugging consumer lag, backpressure, or checkpoint failures

Do NOT use for: batch ETL (use `dbt-transforms`), static data modeling, SQL optimization on analytical queries, data quality on static datasets, one-time migrations.

## Scope Constraints

- This skill covers architecture decisions, configuration patterns, and code generation for streaming systems.
- It does NOT manage infrastructure provisioning (Terraform, CloudFormation) or CI/CD pipelines.
- For Kafka security details, production tuning, and connector configs, load `references/kafka-deep-dive.md`.
- For Flink/Spark framework-specific APIs, load `references/flink-spark-streaming.md`.
- For warehouse-native streaming (Snowpipe, BigQuery, Dynamic Tables), load `references/warehouse-streaming-ingestion.md`.
- For testing and replay strategies, load `references/stream-testing-patterns.md`.
- Load only the reference file relevant to the current task.

## Model Routing

| reasoning_demand | preferred | acceptable | minimum |
|-----------------|-----------|------------|---------|
| medium | Sonnet | Sonnet, Opus | Sonnet |

## Core Principles

**Event Time over Processing Time.** Design for event time. Use watermarks with `WATERMARK FOR event_timestamp AS event_timestamp - INTERVAL 'N' SECOND` to handle out-of-order and late-arriving data.

**Exactly-Once vs At-Least-Once.** At-least-once with idempotent consumers is simpler and often sufficient. Use exactly-once for financial transactions; at-least-once for analytics dashboards.

**Backpressure Awareness.** Monitor consumer lag and implement rate limiting. Use Kafka buffering or Flink backpressure mechanisms to smooth traffic spikes. Alert when lag exceeds thresholds.

**Schema Evolution.** Use schema registries (Confluent, AWS Glue) from day one. Enforce BACKWARD compatibility for most production systems. Add new fields with defaults; never remove required fields without multi-phase migration.

**Idempotent Consumers.** Store offsets transactionally with output, use unique keys for upserts, avoid operations that accumulate state incorrectly on replay.

## Architecture Decision Matrix

| Architecture | Latency | Complexity | Best For |
|---|---|---|---|
| Traditional Batch | Hours-days | Low | Historical reporting, large aggregations |
| Micro-Batch (Spark Streaming) | Seconds-minutes | Medium | Near-real-time analytics, unified batch/stream |
| True Streaming (Flink, Kafka Streams) | Milliseconds-seconds | High | Real-time dashboards, fraud detection, alerting |
| Kappa Architecture | Milliseconds-seconds | Medium | Stream-first, immutable event log, reprocessing |
| Warehouse-Native Streaming | Seconds-minutes | Low | SQL-first teams, simple ingestion, BI integration |

## Stream Processing Framework Selection

| Framework | Latency | SQL | Managed | Best For |
|---|---|---|---|---|
| Kafka Streams | ms | KSQL (separate) | No | Microservices, JVM apps |
| Apache Flink | ms | Flink SQL | AWS KDA, Confluent | Complex event processing, large state |
| Spark Structured Streaming | seconds | Spark SQL | Databricks, EMR | Unified batch/stream, ML integration |
| ksqlDB | ms | Streaming SQL | Confluent Cloud | SQL-first simple transforms |
| Apache Beam/Dataflow | seconds | Limited | GCP Dataflow | Multi-cloud, GCP native |

## Windowing Patterns

| Pattern | Description | Use Case |
|---|---|---|
| Tumbling | Fixed, non-overlapping intervals | Hourly aggregations, regular reporting |
| Sliding | Fixed, overlapping intervals | Moving averages, trend detection |
| Session | Gap-based, variable size | User sessions, activity bursts |
| Global | Custom trigger-controlled | Accumulate until condition met |

Configure watermarks to balance latency vs completeness. Shorter watermark delay = lower latency but may drop late data. Longer delay = higher completeness but delayed results. Handle late arrivals with side outputs (Flink) or allowed lateness windows.

## State Management & Checkpointing

**State backends**: RocksDB (disk, large state GB-TB), in-memory (fast, limited by heap), managed (cloud platforms).

**Checkpointing**: Periodic snapshots of state and positions. Shorter intervals (30s-1min) = faster recovery + more overhead. Longer intervals (5-10min) = less overhead + slower recovery.

**State TTL**: Expire old state to prevent unbounded growth. Set TTL based on business logic.

**Savepoints**: Manual checkpoints for planned downtime. Always take a savepoint before production deployments.

## Schema Compatibility Modes

| Mode | Allowed Changes | Use When |
|---|---|---|
| BACKWARD | Delete fields, add optional | Consumers upgrade first (most common) |
| FORWARD | Add fields, delete optional | Producers upgrade first |
| FULL | Backward + Forward only | Upgrade order unpredictable |

## Monitoring Essentials

| Metric | Alert Threshold |
|---|---|
| Consumer Lag | > 1M messages or > 5 min |
| Throughput | < 50% baseline |
| Error Rate | > 0.1% for critical pipelines |
| Checkpoint Duration | > 2x interval |
| Backpressure Ratio | > 10% sustained |
| Partition Skew | Max/min ratio > 3x |

**Alert tiers**: Critical (page) = consumer stopped, error spike, EOS violation. Warning (hours) = elevated lag, slow checkpoints. Info (trends) = rebalancing, schema changes.

## Security Posture

Generates Kafka configs, stream processing code, and warehouse streaming pipelines. See [Security & Compliance Patterns](../shared-references/data-engineering/security-compliance-patterns.md).

**Credentials**: Kafka broker auth (SASL/mTLS), Schema Registry auth, warehouse connections. All secrets via environment variables.

**Kafka auth**: Use SASL/SCRAM or mTLS. Never PLAINTEXT in production. Use `ConfigProvider` for connector secrets from Vault/AWS SM.

| Capability | Tier 1 (Cloud-Native) | Tier 2 (Regulated) | Tier 3 (Air-Gapped) |
|---|---|---|---|
| Kafka producer/consumer | Deploy to dev | Generate for review | Generate only |
| Flink/Spark jobs | Submit to dev | Generate for review | Generate only |
| Warehouse streaming | Configure dev | Generate configs | Generate only |

## Reference Files

- **[Kafka Deep Dive](references/kafka-deep-dive.md)** — Architecture, EOS, Connect, ksqlDB, security, production tuning
- **[Flink & Spark Streaming](references/flink-spark-streaming.md)** — DataStream API, Flink SQL, watermarks, state backends, deployment
- **[Warehouse Streaming Ingestion](references/warehouse-streaming-ingestion.md)** — Snowpipe Streaming, Dynamic Tables, BigQuery Storage Write API
- **[Stream Testing Patterns](references/stream-testing-patterns.md)** — Embedded Kafka, testcontainers, stream replay, backfill patterns
