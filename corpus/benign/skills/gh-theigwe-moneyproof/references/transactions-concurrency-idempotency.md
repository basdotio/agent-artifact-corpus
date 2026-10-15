# Transactions, Concurrency & Idempotency

## Database transactions

- One business operation = one DB transaction covering: state transition +
  ledger entries + transition/audit log + outbox message. All or nothing.
- Use `READ COMMITTED` + explicit row locks / conditional updates for most
  flows. Use `SERIALIZABLE` for small, complex invariant checks, and **always
  wrap in a retry loop** for serialization failures (SQLSTATE `40001`) and
  deadlocks (`40P01`).
- Keep transactions short. **No HTTP/PSP/bank calls, no emails, no queue
  publishes inside them.** Use the transactional outbox.

## Concurrency patterns

**Compare-and-set state transition** (preferred for status changes):
```sql
UPDATE refunds SET status='processing' WHERE id=$1 AND status='pending';
-- check rowcount == 1
```

**Pessimistic lock for balance checks** (debit wallet, refund against captured):
```sql
BEGIN;
SELECT captured_minor, refunded_minor FROM payments WHERE id=$1 FOR UPDATE;
-- app: if refunded_minor + $amt > captured_minor → reject
UPDATE payments SET refunded_minor = refunded_minor + $amt WHERE id=$1;
INSERT INTO refunds (...);
COMMIT;
```
Or push the check into the DB:
```sql
UPDATE payments SET refunded_minor = refunded_minor + $2
 WHERE id = $1 AND refunded_minor + $2 <= captured_minor;
```
plus `CHECK (refunded_minor <= captured_minor)`.

**Optimistic locking** (`version` column) for low-contention edits; retry on
conflict a bounded number of times.

**Lock ordering:** when locking multiple rows (transfer A→B), lock in a
deterministic order (by ID) to avoid deadlocks.

**Classic race conditions to test for:**
- Two concurrent refunds each passing the "remaining amount" check.
- Two payout jobs picking the same merchant balance (use
  `SELECT … FOR UPDATE SKIP LOCKED` for job queues).
- Webhook and API both completing the same payment.
- Check-then-insert on idempotency keys without a unique constraint.

## Idempotency: inbound API

Every mutating endpoint (`POST /payments`, `/refunds`, `/payouts`, `/transfers`)
accepts an `Idempotency-Key` header (required for money-moving endpoints).

```sql
CREATE TABLE idempotency_keys (
  merchant_id     BIGINT NOT NULL,
  key             TEXT   NOT NULL,
  request_hash    TEXT   NOT NULL,       -- hash of method+path+canonical body
  status          TEXT   NOT NULL,       -- in_progress | completed
  response_code   INT,
  response_body   JSONB,
  resource_id     TEXT,
  locked_until    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (merchant_id, key)
);
```
Flow:
1. `INSERT … ON CONFLICT DO NOTHING` with status `in_progress`.
2. If conflict: load row.
   - Different `request_hash` → `422` (key reused with a different payload).
   - `completed` → return the stored response verbatim.
   - `in_progress` and lock not expired → `409` (concurrent duplicate).
3. Do the work; store the final response **in the same tx as the business
   effect** where possible, then mark `completed`.
4. Expire keys after a documented window (24h–7d), never sooner than client
   retry horizons.

Only cache *deterministic* outcomes. A `500` caused by our crash should leave
the key retryable; a `402 card_declined` is a final answer and is cached.

## Idempotency: outbound to PSPs/banks

- Create the `payment_attempt`/`payout` row **before** calling out; use its ID
  (or a derived key) as the PSP's idempotency key / merchant reference.
- On timeout/5xx: retry **with the same key**. Never generate a new key for a
  retry of the same attempt. That's how double charges happen.
- If the PSP has no idempotency support, use a unique `reference` you control,
  and **query by reference** before retrying.
- A genuinely new attempt (customer clicks pay again after a decline) gets a new
  attempt row and a new key.

## Idempotency: internal consumers

- Every queue/event consumer dedupes on a message ID via a unique constraint
  (`processed_messages(consumer, message_id)`) inserted in the same tx as the effect.
- Ledger posting is idempotent via `ledger_transactions.idempotency_key UNIQUE`
  (e.g. `capture:{attempt_id}`, `refund:{refund_id}`, `fee:{attempt_id}`).
  This is the last line of defence against double-posting.

## Transactional outbox

```
BEGIN;
  UPDATE payouts SET status='queued' WHERE id=$1 AND status='created';
  INSERT INTO outbox (aggregate_id, type, payload) VALUES (...);
COMMIT;
```
A worker reads the outbox (`FOR UPDATE SKIP LOCKED`), performs the external
call/publish, marks sent. Delivery is at-least-once, so the receiver must be
idempotent.

## Handling "unknown" outcomes

Timeouts, connection resets and 5xx after sending mean the operation **may have
happened**. Pattern:
1. Mark attempt `unknown` with `next_check_at`.
2. A resolver job queries the PSP by our reference with backoff.
3. Webhooks can also resolve it.
4. Escalate to manual review after N hours; never auto-fail a payout that may
   have been sent.
