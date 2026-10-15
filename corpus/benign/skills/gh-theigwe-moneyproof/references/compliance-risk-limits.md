# Compliance, Risk & Limits

> This is engineering guidance, not legal advice. Exact thresholds, KYC tiers,
> reporting duties and retention periods depend on jurisdiction and licence
> (e.g. CBN rules in Nigeria, PSD2 in the EU, FinCEN in the US) and change over
> time. Keep them in configuration and confirm with compliance.

## Where checks sit

Run risk and limit checks **before** funds move and **inside** the decision
path, not as an async afterthought:
```
request → authN/authZ → validation → KYC tier & limits → risk scoring
        → decision (allow | review | block | step-up) → execute → post-event monitoring
```
Log every decision with inputs, rule/model version, score and reason codes in
an append-only `risk_decisions` table. You'll need it for audits and disputes.

## Limits

- Types: per-transaction max/min, daily/monthly cumulative volume, count
  velocity (N per minute/hour), balance caps (wallet tiers), per-beneficiary,
  per-device/IP/BIN, per-merchant payout limits.
- Make them **data-driven**: `limits(subject_type, subject_id|tier, metric,
  window, currency, max_value)`, overridable per customer with audit trail.
- Enforce **atomically**: cumulative-limit checks race just like balance
  checks. Use a counter row updated under lock in the same tx as the money
  movement, or a conditional update:
  ```sql
  UPDATE limit_counters SET used_minor = used_minor + $amt
   WHERE subject_id=$1 AND window_start=$2 AND used_minor + $amt <= $max;
  ```
  Redis counters are fine for velocity *signals*; the authoritative monetary
  limit should be transactional with the debit (or reconciled).
- Count reserved/pending amounts against limits; release on failure.
- Windows: be explicit about rolling vs calendar and about timezone (e.g.
  Africa/Lagos midnight vs UTC).

## KYC / KYB

- Tiered accounts: what a user can do (limits, features like payouts) depends
  on verification level. Encode tier → capability mapping in config.
- Store verification status, provider, reference and timestamps; store
  documents encrypted with restricted access; don't store more PII than needed.
- Re-verify on risk triggers (bank detail change, large volume jump).
- Merchant onboarding (KYB): business registration, directors/UBOs,
  settlement account ownership match.

## AML & sanctions

- Screen customers/merchants/beneficiaries against sanctions/PEP lists at
  onboarding and on list updates; screen payout beneficiaries.
- Transaction monitoring rules: structuring (many just-below-threshold
  transactions), rapid in/out (pass-through), unusual geography, sudden volume spikes.
- Cases: create `review_cases` with SLA; funds can be held pending review.
  Holding funds = ledger move to a `held` account, not a flag.
- Suspicious-activity reporting is a compliance process; engineering provides
  data export and an audit trail. Don't tip off the subject in user-facing messages.

## Risk scoring (fraud)

- Signals: device fingerprint, IP/geolocation vs card BIN country, email/phone
  age, velocity, decline history, account age, behavioural anomalies.
- Outcomes: allow, step-up (3DS/OTP), manual review, block. Rules first,
  models later; keep rules versioned and testable.
- Feedback loop: label outcomes (chargebacks, confirmed fraud) back to decisions.

## Security & data protection

- PCI DSS: stay out of scope via PSP tokenisation; never store CVV; mask PAN
  (first6/last4 at most).
- Encrypt sensitive data at rest; secrets in a secrets manager; rotate webhook
  and API keys.
- Logs: structured, with correlation IDs; redact PAN, CVV, BVN/NIN/SSN,
  account numbers, tokens, full names where not needed.
- Least privilege; dual control (maker-checker) for manual balance adjustments,
  limit overrides, refund overrides and payout releases: every manual action
  is a ledger transaction with `actor` and `reason`.
- Data retention: keep financial records for the legally required period;
  delete/anonymise other PII per policy. Ledger is never deleted.

## Operational controls
- Kill switches per merchant, per payment method, per PSP.
- Alerts: decline-rate spikes, refund-rate spikes, payout failures, recon
  breaks, negative balances, webhook backlog, `unknown`-state backlog.
- Runbooks for: PSP outage (failover/queue), duplicate payout suspicion,
  ledger imbalance detected.
