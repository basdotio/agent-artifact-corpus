# Payment Lifecycles & State Machines

## Model the objects separately

Do not cram everything into one `payments.status` column. Distinct objects have
distinct lifecycles:

| Object | What it represents |
|---|---|
| `payment_intent` / `order_payment` | The customer's intent to pay an amount for something. One per checkout. |
| `payment_attempt` / `charge` | One try against a PSP/card/bank. An intent can have many (retries, method switch). |
| `refund` | Money going back for a captured payment. Many per payment (partial refunds). |
| `dispute` / `chargeback` | Issuer-initiated reversal. Separate lifecycle with deadlines. |
| `payout` | Money leaving our platform to a merchant's bank. |
| `ledger_transaction` | The accounting effect. Never has a "status" that changes. it is posted or it doesn't exist. |

The intent's status is a *projection* of its attempts (e.g. intent is
`succeeded` once any attempt is `captured`).

## Reference lifecycles

Card payment attempt (auth + capture):
```
created → requires_action (3DS) → authorizing
authorizing → authorized | declined | failed | unknown
authorized → capturing → captured | capture_failed | unknown
authorized → voided            (cancel before capture)
authorized → expired           (auth window elapsed, ~7 days typical for cards)
captured   → partially_refunded → refunded
captured   → disputed → dispute_won | dispute_lost
```
Bank transfer / pay-by-transfer (common in NG): `created → awaiting_transfer →
received | expired | underpaid | overpaid`: under/over-payment are first-class
states, not errors.

Payout: `created → queued → submitted → paid | failed | returned | unknown`.
Note `paid → returned` is real: banks bounce payouts days later.

## Implementing the machine

1. **Explicit transition table**, in code and ideally in the DB:
   ```python
   TRANSITIONS = {
       "created":     {"authorizing", "requires_action", "failed"},
       "requires_action": {"authorizing", "failed", "expired"},
       "authorizing": {"authorized", "declined", "failed", "unknown"},
       "authorized":  {"capturing", "voided", "expired"},
       "capturing":   {"captured", "capture_failed", "unknown"},
       "unknown":     {"authorized", "declined", "captured", "failed"},
       "captured":    {"partially_refunded", "refunded", "disputed"},
       "partially_refunded": {"partially_refunded", "refunded", "disputed"},
       "disputed":    {"dispute_won", "dispute_lost"},
       # terminal: declined, failed, voided, expired, refunded, dispute_lost ...
   }
   ```
2. **Atomic, guarded transition**: compare-and-set in SQL:
   ```sql
   UPDATE payment_attempts
      SET status = 'authorized', updated_at = now(), version = version + 1
    WHERE id = $1 AND status = 'authorizing'
   RETURNING *;
   ```
   Zero rows updated = someone else moved it, or the transition is stale.
   Re-read and decide; never overwrite.
3. **Record every transition** in an append-only `payment_events` /
   `state_transitions` table (`from`, `to`, `reason`, `actor`, `source_event_id`,
   `occurred_at`, `recorded_at`) in the *same* DB transaction.
4. **Side effects belong to transitions, not to callers.** "On entering
   `captured`: post ledger entries, enqueue receipt email." Implement in one
   place so a webhook and an API call can't apply it twice or differently.
5. **Terminal states are terminal.** A late `authorized` webhook for a
   `voided` attempt is logged and ignored (or raises an alert), not applied.
6. **Monotonic progress.** Give states a rank so out-of-order events can't move
   an object backwards (see `webhooks-and-event-ordering.md`).

## Common bugs to look for
- Status set with plain `UPDATE … SET status = :new WHERE id = :id` (lost updates, illegal transitions).
- Booleans like `is_paid`, `is_refunded` instead of a state: combinations become contradictory.
- Treating PSP timeout as `failed` → customer retries → double charge.
- Intent marked `succeeded` on `authorized` for flows that need capture.
- No `expired` handling for auths or pending transfers; money appears "stuck".
- Refund allowed while a dispute is open (can cause double loss).
