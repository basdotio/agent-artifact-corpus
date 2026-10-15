# Card Authorisations & Declines

## Auth vs capture

- **Authorisation** reserves funds on the cardholder's account; no money moves yet.
- **Capture** instructs the funds to move. Can be immediate (auth+capture /
  "sale") or later (separate capture, e.g. ship-then-charge, hotels, ride-hailing).
- **Void/reversal** releases an uncaptured auth. Always void auths you won't
  capture: dangling holds anger customers.
- **Auth expiry:** uncaptured auths expire (often ~7 days, varies by scheme,
  MCC and PSP). Track `auth_expires_at`; capture before it or re-authorise.
- **Partial capture** (capture less than authorised) is usually allowed; the
  rest is released. **Over-capture** generally isn't (except specific MCCs
  with tolerances). Enforce `captured_minor <= authorized_minor` in the DB.
- **Incremental auth** (hotels, car rental): track each increment.
- Ledger: an auth posts nothing to merchant balances (optionally a memo/hold
  entry). Capture posts the receivable/merchant-pending entries.

## 3-D Secure / SCA

- Flow: `created → requires_action` (challenge URL/redirect) → callback →
  `authorizing`. The customer may abandon; expire `requires_action` attempts.
- Never trust the client redirect alone to mark success. confirm via webhook
  or a server-side PSP fetch.
- Store the authentication result (frictionless/challenged, ECI, liability
  shift): it matters for disputes.

## Declines

Classify decline codes from the PSP into a small internal taxonomy:

| Category | Examples | Retry? | Customer message |
|---|---|---|---|
| `soft` / retryable | issuer unavailable, processing error, timeout, try again | Yes, limited, backoff | "Something went wrong, please try again" |
| `insufficient_funds` | insufficient funds, exceeds withdrawal limit | Maybe later (subscriptions: dunning schedule) | "Insufficient funds" (ok to show) |
| `authentication_required` | SCA required, 3DS failed | Retry **with** 3DS | Prompt authentication |
| `hard` / do-not-retry | stolen/lost card, pickup card, invalid account, closed account, do not honor (often) | **No** | Generic "card declined" |
| `fraud` | suspected fraud, security violation | **No**; feed risk | Generic message |
| `invalid_data` | incorrect CVV, expired card, invalid number | Only after customer fixes data | Field-specific prompt |

Rules:
- Store **both** the raw PSP/network code and your normalised category on the
  attempt. Keep the raw code for analysis; drive logic off the category.
- **Never retry hard declines.** Card schemes monitor excessive retries on the
  same card and can levy fines; issuers may block the merchant.
- Cap retries per card per time window; dunning for subscriptions spread over days.
- **Don't reveal fraud-related reasons** (stolen, pickup, fraud) to the
  customer. show a generic decline. This avoids helping card testers.
- A decline is a **final, cacheable** outcome for its idempotency key.
- A declined attempt is terminal; a retry is a **new attempt** with a new key.

## Card-testing defence

Card testing (many small auths with stolen card numbers) shows up as bursts of
low-value attempts and high decline rates. Mitigate with: per-IP/device/email/
BIN velocity limits, CAPTCHA after N failures, minimum amounts, blocking
repeated declines on one card, monitoring decline-rate spikes per merchant.

## PCI scope

- Never let raw PAN/CVV touch your servers: use PSP hosted fields / SDK
  tokenisation. Then you only handle tokens and last4/brand/expiry.
- Never log, store or put CVV in any field, even temporarily.
- Keep card tokens scoped to the merchant/customer that created them.
