# moneyproof

A [Claude Code](https://claude.com/claude-code) skill that makes Claude write and review
backend code that moves money the way a payments engineer would.

Money bugs don't crash. They silently double-charge a customer, pay a merchant twice,
or create money out of nothing. This skill gives Claude a set of non-negotiable rules,
a default architecture, and focused reference guides so those outcomes are impossible
by construction or detectable within minutes.

## What it covers

| Area | Reference |
|---|---|
| Payment, refund and payout statuses, transitions, lifecycle design | [`lifecycle-and-state-machines.md`](references/lifecycle-and-state-machines.md) |
| Minor units, decimals, rounding, allocation, double-entry ledger, audit trail | [`ledger-and-financial-correctness.md`](references/ledger-and-financial-correctness.md) |
| DB transactions, locking, races, idempotency keys, transactional outbox | [`transactions-concurrency-idempotency.md`](references/transactions-concurrency-idempotency.md) |
| Webhook endpoints, duplicate, late and out-of-order events, reconciliation | [`webhooks-and-event-ordering.md`](references/webhooks-and-event-ordering.md) |
| Auth, capture, void, 3DS, decline codes, card-testing defence | [`card-authorisation-and-declines.md`](references/card-authorisation-and-declines.md) |
| Settlement, merchant payouts, refunds, chargebacks, negative balances | [`settlement-payouts-refunds.md`](references/settlement-payouts-refunds.md) |
| KYC/AML, limits, risk rules, PCI scope, retention | [`compliance-risk-limits.md`](references/compliance-risk-limits.md) |

It also ships a starter PostgreSQL schema, [`assets/ledger_schema.sql`](assets/ledger_schema.sql):
an append-only double-entry ledger with triggers enforcing balanced transactions,
currency matching, no updates or deletes, and a drift view that compares cached balances
to ledger-derived ones.

## The ten non-negotiables

1. Never use floats for money.
2. Amount and currency travel together.
3. Balances are derived from an append-only double-entry ledger.
4. Never update or delete financial history.
5. Every state change goes through an explicit, database-guarded state machine.
6. Every externally triggered mutation is idempotent.
7. The PSP is the source of truth for what happened; the ledger is the source of truth for what we owe. Reconcile daily.
8. Unknown is a real state. A timeout is not a failure.
9. No external calls inside lock-holding DB transactions.
10. Everything is auditable, with correlation IDs end to end.

The skill ends with a review checklist Claude runs against the code it wrote or reviewed,
and it states any item it deliberately did not meet.

## Install

Skills live in a `skills` directory. For all your projects:

```bash
git clone https://github.com/theigwe/moneyproof.git ~/.claude/skills/moneyproof
```

Or for a single project, clone into `<project>/.claude/skills/moneyproof`.

The folder name should match the `name` in [`SKILL.md`](SKILL.md). Start a new Claude Code
session and the skill is picked up automatically.

## Usage

Claude loads the skill on its own when a task touches payments, wallets, balances,
refunds, payouts, ledgers, PSP integrations (Stripe, Paystack, Flutterwave, Adyen and
similar), webhook handlers, or any code that stores or computes money. You don't need
to mention it. Examples:

- "Add a refund endpoint to our payments service."
- "Review this Paystack webhook handler for bugs."
- "Design the schema for merchant wallets and payouts."
- "Why can two concurrent refunds exceed the captured amount?"

Claude reads only the reference files the task needs, so context stays small.

## Layout

```
SKILL.md                  entry point: non-negotiables, architecture, review checklist
references/               one focused guide per topic
assets/ledger_schema.sql  starter PostgreSQL ledger
```

## Scope and disclaimer

This is engineering guidance, not legal or compliance advice. KYC tiers, reporting duties,
limits and retention periods depend on jurisdiction and licence. Keep them in
configuration and confirm with your compliance team. The SQL is a starting point to adapt
and test under your own load, not a drop-in production ledger.

## Contributing

Issues and pull requests are welcome, especially for new PSP-specific pitfalls, additional
failure modes, and corrections. Please keep guidance concrete and testable, and avoid em dashes.

## License

MIT, see [`LICENSE`](LICENSE).
