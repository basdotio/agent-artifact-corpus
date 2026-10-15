# Webhooks, Out-of-Order & Delayed Events

## Assume the worst about delivery

Providers deliver **at least once**, **in any order**, possibly **hours or days
late**, sometimes **for objects you've never seen**, and occasionally
**forged** by attackers. Design for all of these.

## Receiving (the endpoint)

1. **Verify authenticity on the raw body bytes** before parsing: HMAC
   signature with the provider's secret using a constant-time compare
   (`hmac.compare_digest`, `crypto.timingSafeEqual`). Re-serialized JSON will
   not match. Where available, also check the timestamp (reject > ~5 min skew)
   to stop replays. Optional: IP allowlist as defence in depth, not as the only check.
2. **Persist to an inbox table, then return 2xx fast** (< a few seconds):
   ```sql
   CREATE TABLE webhook_inbox (
     id                BIGSERIAL PRIMARY KEY,
     provider          TEXT NOT NULL,
     provider_event_id TEXT NOT NULL,
     event_type        TEXT NOT NULL,
     object_id         TEXT,
     payload           JSONB NOT NULL,
     signature_ok      BOOLEAN NOT NULL,
     received_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
     processed_at      TIMESTAMPTZ,
     attempts          INT NOT NULL DEFAULT 0,
     last_error        TEXT,
     UNIQUE (provider, provider_event_id)
   );
   ```
   `ON CONFLICT DO NOTHING` → duplicate → still return 2xx.
   If the provider has no event ID, derive one from a hash of
   (object ID, event type, status, provider timestamp).
3. Never do business logic, PSP calls, or emails in the request thread. Slow
   handlers cause provider timeouts → retries → more duplicates.
4. Return non-2xx only when you want a redelivery (e.g. couldn't persist).

## Processing

- Worker pulls unprocessed inbox rows, processes each in its own DB tx, sets
  `processed_at` in the same tx as the business effect.
- Retry with exponential backoff; after N failures move to a dead-letter state
  and alert. Provide a replay tool.
- **Don't trust the payload for amounts/status when it matters**: for
  high-value transitions, fetch the object from the PSP API (the "thin
  event, fetch latest" pattern). This also neutralises ordering problems.
- Validate that the event's amount/currency/merchant match our record. A
  mismatch is an alert, not something to silently apply.

## Out-of-order events

Examples: `charge.refunded` arrives before `charge.succeeded`;
`payout.paid` after `payout.failed`; `transfer.successful` after you already
marked it `reversed`.

Strategies (combine them):
1. **Monotonic state ranks.** Only move forward:
   ```python
   RANK = {"created":0,"authorizing":1,"authorized":2,"capturing":3,
           "captured":4,"partially_refunded":5,"refunded":6}
   if RANK[new] <= RANK[current]: log_and_skip()
   ```
   Combined with the transition table; terminal states always win. Ranks suit the
   happy path only: `unknown`, `disputed` and `returned` are not ranked and need
   explicit transitions, because they legitimately move "backwards" in money terms.
2. **Compare provider timestamps / sequence numbers** where the provider
   supplies them; store `last_provider_event_at` on the object and ignore older events.
3. **Fetch current state from the provider** and reconcile to it, rather than
   applying the event's delta.
4. **Events for unknown objects:** don't drop. Park them (`status='deferred'`,
   `retry_after`) and retry later. the creating request may still be in flight.
   If it never appears, alert: it may be a payment you didn't initiate, or an
   orphan you need to refund.
5. **Contradictory events** (paid then failed; success after reversal) → apply
   the provider's latest truth via fetch, post compensating ledger entries,
   and raise an alert for review. Bank payouts genuinely can flip `paid → returned`.

## Delayed events

- Never block a user flow waiting for a webhook. Show `processing`, then
  resolve via webhook **or** a polling/resolver job, whichever comes first.
- Schedule a fallback poll for every pending object (`next_check_at`) so a lost
  webhook doesn't leave money in limbo.
- Expiry jobs: auths, pending bank transfers, payment links. When a payment
  arrives *after* expiry (common with bank transfers), don't drop it: credit
  it and either fulfil or auto-refund, per policy.
- Late refunds/chargebacks can arrive after a merchant was paid out → handle
  negative balances (see settlement reference).

## Sending webhooks to your own merchants

Mirror the same discipline outward: sign payloads (HMAC + timestamp), include
a unique `event_id`, retry with backoff for days, let merchants replay, document
that delivery is at-least-once and unordered, and keep events small ("thin")
with an API to fetch current state.

## Tests to write
- Same event delivered twice concurrently → one effect.
- Refund event before success event → final state correct, ledger balanced.
- Event for unknown payment → deferred, then applied once the payment exists.
- Invalid signature → rejected, nothing persisted as trusted.
- Webhook never arrives → resolver job settles the payment.
