# Migration Plan: Event-Driven Order Notifications (v2)

*Prepared by the coding agent overnight, based on the repository, the incident history in `docs/incidents/`, and the Grafana dashboards linked from the README.*

## 1. Executive Summary

Our current order-notification system relies on a cron job (`notify_orders`) that runs every five minutes and polls the `orders` table for rows whose `status` has changed since the last run. While this approach has served us well, it is increasingly showing its limitations: the p95 delay between a status change and the customer receiving a notification currently sits at 4 minutes 40 seconds, the polling query accounts for roughly 18% of CPU on the primary Postgres instance during business hours, and we have had three incidents in the last quarter where overlapping cron runs sent duplicate emails. We send approximately 1.2 million notifications per day across email, SMS and push.

This document proposes migrating to an event-driven pipeline built on change data capture (CDC). Debezium will stream row-level changes from Postgres into a Kafka topic, and a new `notifier` service will consume those events and dispatch notifications through our existing provider integrations. The target is a p95 end-to-end delay below 10 seconds, the removal of the polling load from the primary, and a structural fix for the duplicate-send problem.

## 2. Current State

- `notify_orders` is a Python cron job deployed on the `jobs` host, scheduled with `*/5 * * * *`.
- Each run selects rows where `updated_at > last_run_at` and `status IN ('confirmed','shipped','delivered','refunded')`, renders templates, and calls the email (SendGrid), SMS (Twilio) and push (FCM) providers synchronously.
- `last_run_at` is stored in a single-row table. When a run takes longer than five minutes (which happens during peaks), the next run starts with a stale `last_run_at` and picks up the same rows again. This is the root cause of the duplicate-send incidents INC-2291, INC-2304 and INC-2342.
- There are 14 distinct code paths in the monolith that write to `orders.status`, which is relevant to the choice of approach below.

## 3. Options Considered

### 3.1 Transactional outbox

Each of the 14 write paths would insert a row into an `outbox` table inside the same transaction, and a relay would publish outbox rows to Kafka. This is the textbook approach and gives strong guarantees, but it requires touching all 14 write paths, several of which live in legacy modules with poor test coverage. We estimate 3 to 4 weeks of additional work and a meaningful regression risk. **Rejected for now**, although it remains the long-term ideal.

### 3.2 Postgres LISTEN/NOTIFY

Lightweight and built in, but notifications are not durable (anything sent while the consumer is disconnected is lost), and payloads are limited to 8000 bytes. **Rejected** because missed notifications are not acceptable.

### 3.3 Change data capture with Debezium (chosen)

Debezium reads the Postgres write-ahead log (WAL) through a logical replication slot and publishes every change to `orders` as an event. No application code changes are required, all 14 write paths are covered automatically, and events are durable in Kafka. **Chosen.**

## 4. Target Architecture

1. **Debezium connector** (`orders-cdc`) running on our existing Kafka Connect cluster, using the `pgoutput` plugin and a dedicated replication slot `debezium_orders`. It captures only the `orders` table and only the columns `id`, `status`, `version`, `merchant_id`, `customer_id`, `updated_at`.
2. **Kafka topic** `orders.status.v1` with 12 partitions, keyed by `order_id`, replication factor 3, retention 7 days.
3. **`notifier` service**, a new Go service in its own deployment with 3 replicas in a single consumer group. For each event it:
   - filters to the four notifiable statuses,
   - builds the idempotency key `order_id:status:version`,
   - checks and sets that key in Redis with a TTL of 72 hours (`SET NX EX`), skipping the event if the key already exists,
   - renders the template and calls the provider,
   - commits the Kafka offset only after the provider call succeeds.
4. **Delivery semantics** are at-least-once from Kafka, made effectively-once for customers by the Redis idempotency check.
5. **Ordering** is guaranteed per order because events are keyed by `order_id`, so all events for one order land on the same partition. There is no ordering guarantee across orders, which we do not need.

## 5. Rollout Plan

| Phase | Week | What happens | Exit criterion |
|---|---|---|---|
| 0 | 1 | Create topic, deploy Debezium connector, deploy `notifier` with sending disabled | Connector lag under 5 s for 3 days |
| 1 | 2 to 3 | Shadow mode: `notifier` consumes and logs the notification it *would* send; a comparison job diffs this against what cron actually sent | At least 99.9% match over 7 consecutive days |
| 2 | 4 | Feature flag `notif_pipeline_v2` turned on for 10% of merchants; cron skips merchants where the flag is on | No increase in support tickets about notifications |
| 3 | 5 | Flag at 50% of merchants | p95 delay under 10 s |
| 4 | 6 | Flag at 100%; cron job disabled but left deployed | 7 days without a rollback |
| 5 | 8 | Delete `notify_orders` and the `last_run_at` table | n/a |

During phases 2 to 4 both systems are live for different merchants. Because cron and `notifier` share the same Redis idempotency keys (we will backport the key check into cron in phase 0), a merchant who is moved between systems mid-flight will not receive duplicates.

## 6. Rollback

At any point before phase 5, rollback is a single flag change: turning `notif_pipeline_v2` off returns all merchants to cron within one cron cycle. We expect rollback to take under 5 minutes end to end. After phase 5 the cron code is gone and rollback would require a redeploy from the last tagged release.

## 7. Cost

- Kafka (managed, 3 brokers) and Kafka Connect add approximately $1,400 per month.
- Redis usage is negligible on the existing cluster (about 3.6 million keys at steady state given the 72-hour TTL).
- Removing the polling query frees about 18% of primary CPU during business hours, which lets us defer the planned primary upgrade (currently budgeted at $2,100 per month) by at least two quarters.

## 8. Risks and Mitigations

- **Replication slot growth.** If Debezium stops consuming, Postgres retains WAL for the slot indefinitely and can fill the disk. Mitigation: alert when slot lag exceeds 20 GB, and set `max_slot_wal_keep_size = 50GB` so that the primary is protected.
- **Schema changes to `orders`.** Renaming or dropping a captured column breaks the connector. Mitigation: add a CI check that fails migrations touching captured columns unless the connector config is updated in the same PR.
- **Duplicate sends during cutover.** Covered by the shared Redis idempotency key described in section 5.
- **Provider outages.** `notifier` retries with exponential backoff (max 5 attempts) and then writes the event to a dead-letter topic `orders.status.dlq.v1` for manual replay.

## 9. Open Questions

- **Kafka on-call ownership.** The platform team has not yet agreed to own Kafka on-call. Until they do, the orders team would carry the pager.
- **SMS rate limits.** Our Twilio account is limited to 100 messages per second. Cron naturally smoothed bursts by batching every five minutes; the event-driven pipeline will send as fast as events arrive, so a large batch of status changes (for example a bulk "shipped" update from a warehouse import) could exceed the limit. We have not decided whether to add a rate limiter in `notifier` or request a higher limit.

## 10. Recommendation

Proceed with phase 0 next week. The plan delivers a large latency improvement, removes a recurring incident class, and reduces load on the primary, with a low-risk rollback path through phase 4. The two open questions should be resolved before phase 2.
