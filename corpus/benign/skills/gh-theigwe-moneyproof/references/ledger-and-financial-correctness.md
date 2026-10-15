# Financial Correctness, Invariants & the Append-Only Ledger

## Representing money

**Preferred:** integer minor units + currency.
```
amount_minor BIGINT NOT NULL CHECK (amount_minor >= 0)   -- 150050 = ₦1,500.50
currency     CHAR(3) NOT NULL REFERENCES currencies(code)
```
- Minor-unit exponent comes from a `currencies` table (ISO-4217): JPY/KRW=0,
  NGN/USD/EUR/GHS/KES=2, KWD/BHD=3. Never hard-code `/100`.
- `BIGINT` holds ~9.2×10¹⁸ minor units, enough for any fiat amount. It is **not**
  enough for 18-decimal crypto tokens (use `NUMERIC(78,0)` of base units, or a
  decimal string) and `currencies.minor_units` must allow up to 18.
- On the wire, carry amounts as integer minor units or a **decimal string**,
  never a JSON number. In OpenAPI use `type: string` with a `pattern` and no
  `format: decimal` (some generators map it back to a float).
- Prefer an absent amount over `0` when a value is unknown or unpriced; zero
  sums and reports a real holding as worthless.

**Alternative:** `NUMERIC(20, 4)` (or similar fixed scale) when you need sub-minor
precision (FX rates, per-unit pricing, interest accrual). Keep FX rates as
`NUMERIC` with more scale (e.g. `NUMERIC(24,10)`), and round to the currency's
minor unit only when posting to the ledger.

**Never:** `FLOAT`, `DOUBLE`, `REAL`, JS `Number` arithmetic, `money` type in
Postgres (locale-dependent), or parsing JSON amounts into floats.

Language notes:
- Python: `int` or `decimal.Decimal` built from **strings** (`Decimal("10.10")`,
  never `Decimal(10.1)`); set context rounding explicitly.
- Java/Kotlin: `long` minor units or `BigDecimal` with explicit `RoundingMode`;
  compare with `compareTo`, not `equals` (scale-sensitive).
- JS/TS: `bigint` minor units, or `dinero.js` / `big.js`. Serialize as string.
- Go: `int64` minor units or `shopspring/decimal`.
- Wrap in a `Money` value object that refuses cross-currency arithmetic.

## Rounding & allocation

- Choose one rounding mode per use (half-even for aggregates/interest, half-up
  is common for customer-facing fees) and document it.
- Round **once**, at the boundary where an amount becomes a posted ledger amount.
  Never round intermediate steps.
- **Allocation must be exact.** Splitting ₦100.00 three ways is 33.34/33.33/33.33,
  not 33.33×3. Use largest-remainder allocation and assign the remainder
  deterministically (e.g. to the platform or the first party):
  ```python
  def allocate(total_minor: int, ratios: list[int]) -> list[int]:
      s = sum(ratios)
      parts = [total_minor * r // s for r in ratios]
      remainder = total_minor - sum(parts)
      order = sorted(range(len(ratios)),
                     key=lambda i: (total_minor * ratios[i]) % s, reverse=True)
      for i in order[:remainder]:
          parts[i] += 1
      assert sum(parts) == total_minor
      return parts
  ```
- Fees: compute fee, then `net = gross - fee`. Never compute net and fee
  independently (they won't sum to gross).

## Double-entry, append-only ledger

Core tables (see `assets/ledger_schema.sql`):
- `ledger_accounts`: one per (owner, purpose, currency): e.g.
  `merchant:123:available:NGN`, `merchant:123:pending:NGN`,
  `platform:fees:NGN`, `psp:paystack:receivable:NGN`, `bank:payout_clearing:NGN`.
  Each has a **normal balance** (debit or credit).
- `ledger_transactions`: one row per business event (capture, refund, payout,
  fee, reversal), with `idempotency_key UNIQUE`, `event_type`, `reference_type`,
  `reference_id`, `effective_at`, `created_at`, `actor`, `correlation_id`.
- `ledger_entries`: ≥2 rows per transaction: `account_id`, `direction`
  (debit/credit) or a signed amount, `amount_minor`, `currency`.

**Invariants (enforce, don't hope):**
1. Per transaction, per currency: Σ debits = Σ credits.
2. Entries are insert-only (revoke UPDATE/DELETE; trigger that raises).
3. Every entry's currency = its account's currency.
4. Every transaction references the business object that caused it.
5. Accounts that must not go negative (customer wallets, merchant available)
   are checked under lock or via constraint at posting time.
6. Ledger-derived balance == cached balance (if any): checked continuously.
7. Globally, per currency: Σ all debit entries == Σ all credit entries (the books balance).
   Note that per-account balances are signed by normal balance, so they do not
   sum to zero; test this invariant on raw entries, not on `account_balances`.

Enforcing (1) in Postgres: insert entries in the same tx and use a
`CONSTRAINT TRIGGER … DEFERRABLE INITIALLY DEFERRED` that checks the sum at
commit, or post via a single stored procedure that validates before insert.

**Example: card capture of ₦10,000 with 1.5% fee:**
| Account | Debit | Credit |
|---|---|---|
| psp:receivable | 10,000.00 | |
| merchant:123:pending | | 9,850.00 |
| platform:fee_revenue | | 150.00 |

At settlement, PSP pays us: Dr `bank:operating` / Cr `psp:receivable`, and
merchant funds move `pending → available`.

**Corrections:** post a reversing transaction (`reverses_transaction_id`) and,
if needed, a new correct one. Never edit.

## Balances

- Compute as `SUM(entries)` per account. For speed, maintain
  `account_balances(account_id, balance_minor, version, last_entry_id)` updated
  **in the same tx** as entries, with `SELECT … FOR UPDATE` on the balance row.
- Distinguish `pending`, `available`, `reserved/held` as separate accounts,
  not as flags on one balance.
- For hot accounts (platform fee account) avoid lock contention: shard into
  sub-accounts, or skip the cached balance for accounts that never need a
  sufficient-funds check.

## Auditability

- `created_at` (system time) and `effective_at` (business time) on every
  financial record; never back-date `created_at`.
- `actor` (user/service/webhook), `reason`, `correlation_id`, external
  references (PSP charge ID, bank reference, NIP session ID, etc.).
- Keep raw inbound webhook payloads and outbound request/response summaries
  (redacted) for the regulatory retention period.
- Make it possible to answer: *"Why is this merchant's balance X?"* by listing
  entries; *"What happened to payment P?"* by listing transitions + PSP events.
- Consider hash-chaining ledger rows (`prev_hash`) or periodic signed snapshots
  if tamper-evidence is required.

## Reconciliation

Daily (and ideally intraday) jobs compare:
- PSP settlement/transaction reports ↔ `psp:receivable` entries
- Bank statement ↔ `bank:*` accounts and payouts
- Internal state ↔ ledger (every `captured` payment has exactly one capture tx)

Mismatches go to a `recon_breaks` table with owner and status; alert on any
unresolved break older than N hours. Reconciliation is how you find the bugs
that tests missed.
