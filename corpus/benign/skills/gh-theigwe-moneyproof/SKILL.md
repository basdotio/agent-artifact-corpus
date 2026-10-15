---
name: moneyproof
description: Best practices for designing, writing and reviewing backend code that moves money: payment lifecycles and state machines, DB transactions and concurrency, idempotency, webhooks and out-of-order events, settlement, payouts, refunds, card authorisations and declines, compliance and limits, and financial correctness (integer minor units or decimals, append-only double-entry ledger, audit trails). Use whenever a task touches payments, wallets, balances, charges, transfers, payouts, refunds, ledgers, PSP integrations (Stripe, Paystack, Flutterwave, Adyen, etc.), webhook handlers, or any schema or code that stores or computes money, even if the user doesn't say "payments". Also use when reviewing such code for bugs.
---

# Moneyproof: Payment Systems Backend

Money code fails differently from ordinary code: a bug doesn't crash, it silently
creates or destroys money, double-charges a customer, or pays a merchant twice.
Every decision below exists to make those outcomes **impossible by construction**
or **detectable within minutes**.

## How to use this skill

1. Read the **Non-negotiables** below. They apply to every payment task.
2. Open only the reference file(s) the task touches:

| Task touches… | Read |
|---|---|
| Payment/refund/payout statuses, transitions, lifecycle design | `references/lifecycle-and-state-machines.md` |
| Amounts, currencies, balances, ledger tables, rounding, fees, audit trail, invariants | `references/ledger-and-financial-correctness.md` |
| DB transactions, locking, race conditions, retries, idempotency keys | `references/transactions-concurrency-idempotency.md` |
| Webhook endpoints, PSP callbacks, event processing, out-of-order or late events, reconciliation | `references/webhooks-and-event-ordering.md` |
| Card auth/capture/void, decline codes, 3DS, retries on decline | `references/card-authorisation-and-declines.md` |
| Settlement, merchant balances, payouts, refunds, chargebacks | `references/settlement-payouts-refunds.md` |
| KYC/AML, velocity limits, risk rules, PCI scope, data retention | `references/compliance-risk-limits.md` |

3. Starting a new system? Begin from `assets/ledger_schema.sql` (PostgreSQL) and
   adapt it rather than inventing a balance column.
4. Before finishing, run the **Review checklist** at the end of this file against
   the code you wrote or reviewed, and state any item you deliberately didn't meet.

## Non-negotiables

1. **Never use floats for money.** Store integer minor units (`BIGINT` kobo/cents)
   with an explicit ISO-4217 currency, or `NUMERIC(p,s)` with a fixed scale. In
   code use integers or an arbitrary-precision decimal type (`decimal.Decimal`,
   `BigDecimal`, `shopspring/decimal`, `dinero.js`/`big.js`). Never parse money
   from JSON into a native float; read it as a string or integer, and send
   amounts as decimal strings or integer minor units, never JSON numbers.
2. **Amount and currency travel together.** A bare number is a bug. Never add
   amounts in different currencies; FX is an explicit, recorded conversion.
3. **Balances are derived, not stored-and-mutated.** The source of truth is an
   append-only, double-entry ledger where every transaction's entries sum to
   zero per currency. A cached balance is allowed only if updated in the same DB
   transaction as the entries and verifiably recomputable from them.
4. **Never UPDATE or DELETE financial history.** Corrections are new reversing
   entries. Enforce with DB permissions/triggers, not just convention.
5. **Every state change goes through an explicit state machine** with an allowed
   transition table, guarded in the database (`UPDATE … WHERE status = :expected`),
   not by an `if` in application memory.
6. **Every externally-triggered mutation is idempotent.** API calls take an
   idempotency key; webhook handlers dedupe on the provider event ID; outbound
   PSP calls send our own idempotency key so *our* retries are safe too.
7. **The PSP/bank is the source of truth for what happened externally; our
   ledger is the source of truth for what we owe.** Reconcile the two daily,
   automatically, and alert on any diff.
8. **Unknown is a real state.** A timeout from a PSP does not mean failure. Mark
   the attempt `pending`/`unknown`, then resolve by querying the PSP or waiting for
   the webhook. Never blindly retry a charge or payout with a new key.
9. **External calls never happen inside a DB transaction that holds locks.**
   Use: persist intent → commit → call PSP → persist result (or an outbox).
10. **Everything is auditable:** who/what/when/why for every money movement and
    every state transition, with correlation IDs linking request → payment →
    ledger transaction → PSP reference → webhook event.

## Default architecture to reach for

```
API (idempotency key) ──► Payment service ──► DB tx: insert payment(status=created)
                                                     + outbox row
                                    │ commit
                                    ▼
                          Outbox worker ──► PSP API (our idempotency key)
                                    │
           PSP webhook ──► Inbox table (unique provider_event_id) ──► 200 OK fast
                                    │
                          Event processor: lock payment row, validate transition,
                          apply state change + ledger entries in ONE DB tx
                                    │
                          Daily reconciliation job: PSP reports vs ledger
```

Prefer this inbox/outbox shape over "do everything inline in the request". It
is what makes retries, crashes and duplicate deliveries harmless.

## Review checklist

Correctness
- [ ] No `float`/`double`/`REAL`/JS `number` arithmetic on money; JSON amounts parsed as int/string
- [ ] Every amount has a currency; minor-unit exponent comes from a currency table (JPY=0, NGN/USD=2, KWD=3)
- [ ] Rounding mode is explicit (usually banker's or half-up, documented) and happens once, at a defined boundary
- [ ] Fee/split allocation sums exactly to the total (remainder assigned deterministically)
- [ ] Ledger entries balance to zero per transaction per currency; enforced by DB constraint/trigger or a tested invariant
- [ ] No UPDATE/DELETE on ledger or event tables

State & concurrency
- [ ] Transitions validated against an explicit table; terminal states are terminal
- [ ] Conditional update or row lock guards each transition; affected-row count checked
- [ ] Balance checks (e.g. "sufficient funds") happen under a lock or with a constraint in the same tx as the debit
- [ ] No network calls inside lock-holding transactions

External integration
- [ ] Inbound API mutations require an idempotency key, scoped per merchant, with request-hash mismatch detection
- [ ] Outbound PSP calls pass a stable idempotency key derived from our attempt ID
- [ ] Webhooks: signature verified on raw body, timestamp tolerance, dedupe on event ID, fast 2xx, async processing
- [ ] Handlers tolerate duplicates, reordering, and events for objects we haven't seen yet
- [ ] Timeouts → `unknown` state + resolution job, not failure

Operations
- [ ] Reconciliation job exists and alerts on mismatch
- [ ] Limits/risk checks run before funds move; decisions logged with reasons
- [ ] No PAN/CVV stored or logged; secrets and PII redacted in logs
- [ ] Tests cover: duplicate request, duplicate webhook, out-of-order webhook, concurrent refund, partial refund to the cent, PSP timeout
