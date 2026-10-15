# Settlement, Merchant Payouts & Refunds

## Settlement (PSP → platform)

- Captured ≠ settled. The PSP pays out to your bank on a schedule (T+1, T+2…)
  net of their fees, possibly batched, possibly netting refunds/chargebacks.
- Model funds in stages with separate ledger accounts:
  `psp:receivable` → (settlement arrives) → `bank:operating`.
  Merchant side: `merchant:pending` → (settled / hold period passed) →
  `merchant:available` → (payout) → `bank:payout_clearing` → gone.
- Import PSP settlement reports; match each settled line to a ledger
  transaction by PSP reference. Unmatched lines = recon breaks.
- Record PSP fees as their own entries (`expense:psp_fees`) from the settlement
  report, not your estimate, and reconcile your estimate against it.

## Merchant payouts (platform → merchant)

1. **Compute payable** from the ledger: `available` balance minus reserves/holds
   minus negative-balance recovery. Never from summing payment rows.
2. **Create payout + ledger tx atomically:** debit `merchant:available`, credit
   `bank:payout_clearing`. This "reserves" the money so it can't be paid twice or
   refunded away concurrently. Guard with `available >= amount` under lock.
3. **Send via outbox** to the bank/transfer API with the payout ID as reference/
   idempotency key.
4. **Resolve:** `paid` → debit `bank:payout_clearing`, credit `bank:operating`
   (or however your bank account is modelled). `failed` → reverse step 2,
   returning funds to `merchant:available`. `unknown` → **do not retry with a new
   reference**; query status by reference; escalate.
5. **Returned later** (bank bounces after `paid`): reverse into merchant
   balance, mark beneficiary account as needing verification.

Rules:
- Verify beneficiary account (name enquiry / account validation) before the
  first payout and when bank details change; hold payouts for a cooling-off
  period after a bank-detail change (account-takeover defence).
- Minimum payout amounts, payout schedules, and per-merchant rolling reserves
  are configuration, not code.
- One payout per merchant per currency per run; use `SKIP LOCKED` job claiming
  and a unique `(merchant_id, payout_run_id)` constraint.
- Payout runs must be re-runnable safely after a crash.

## Refunds

- A refund is its own object with its own lifecycle:
  `pending → processing → succeeded | failed | unknown` (and cancelled).
- **Invariant:** Σ(non-failed refunds) ≤ captured amount, per payment. Enforce
  under row lock or with a conditional update + CHECK constraint (see
  concurrency reference). Count `pending/processing/unknown` refunds as
  consuming the refundable amount.
- Refund in the **original currency and to the original method**; FX
  differences are a separate, explicit entry.
- Partial refunds: support many; compute remaining = captured − Σ refunds.
- Fee policy is a business decision: decide whether platform/PSP fees are
  returned and post it explicitly, don't let it fall out of arithmetic.
- Ledger at creation: debit `merchant:available` (or pending), credit
  `refund_clearing`. On PSP success: clear to `psp:receivable`/bank. On failure:
  reverse. If the merchant's balance is insufficient, either block, take from a
  reserve, or allow a negative balance, explicitly per policy.
- Refunding an **uncaptured** auth is a **void**, not a refund.
- Block or flag refunds on payments with an open dispute (risk of paying twice).
- Refunds to closed cards/accounts can fail days later → handle `failed` after
  `succeeded`-looking interim states; reconcile.

## Chargebacks / disputes

- Separate object with deadlines (`evidence_due_by`). Funds are usually debited
  immediately with a dispute fee: debit `merchant:available`, credit
  `psp:receivable` (or bank) + fee entries.
- Won → reverse the debit; lost → finalise.
- Merchant can go negative → recover from future settlements before paying out;
  alert on large negative balances.

## Negative balances

Late refunds/chargebacks after payout make balances negative. Decide policy
upfront: net against future earnings, debit merchant's bank (where permitted),
draw from rolling reserve, or write off (with an explicit loss entry).
