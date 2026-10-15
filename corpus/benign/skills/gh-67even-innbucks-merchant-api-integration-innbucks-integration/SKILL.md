---
name: innbucks-integration
description: "InnBucks Merchant API integration expert (Zimbabwe's InnBucks mobile wallet): bearer-token login, generating payment and withdrawal codes, showing the code with its QR code and app deep link, checking code status, and agent deposits, deposit inquiry, reversals, bank change, utility payments and statements, through UAT sign-off and go-live. Amounts are integer cents, auth needs both an API key and a 15-minute token, and InnBucks' documents contradict themselves, so consult this skill for any InnBucks code, review, error, testing or go-live question, even a quick one, in any language. Recognise it by: InnBucks; /auth/third-party; /api/code/generate or /api/code/inquiry; X-Api-Key with a Bearer token; paymentToken, zw.co.innbucksnova.test or com.innbucks.customer deep links; stan, authNumber, destinationMsisdn, destinationAccount, originalParticipantReference; statuses New, Claimed, Timed Out; responseCode 00/000/025/096; USSD *569#. Not for EcoCash, OneMoney or Paynow."
---

# InnBucks Merchant API

InnBucks is a Zimbabwean mobile wallet. The Merchant API is **code-based**: the merchant's server
**generates a code**, shows it (digits + QR + deep link), the **customer pays against it** in the
InnBucks app or on USSD `*569#`, and the server **asks** whether the code is paid. No callbacks
are documented. Agents also move cash in and out (withdrawal codes, deposits, bank change). Money moves,
so correctness beats speed: most rules below exist because breaking them charges 100x too much, pays
out cash that was never claimed, or credits a deposit twice.

This skill knows exactly what the InnBucks guide at https://67even.github.io/innbucks-merchant-api-integration/
knows (InnBucks Merchant API document v1.2.1, reviewed 22 Sep 2026). The `references/` files are
generated from that guide. InnBucks' own documents are under NDA and are not included: when the user
has them, they are the contract.

## 1. Setup and authentication

1. **Credentials come from InnBucks** at merchant onboarding: an **API key**, a **username** and a
   **password**, plus a private **base URL** per environment (test, production). There is no public
   sandbox or portal. Walk a newcomer through `references/onboarding.md` (test app, test funds,
   business administrator, merchant vs agent capabilities).
2. **Two credentials on every call:** `X-Api-Key: <key>` on **every** request, login included, and
   `Authorization: Bearer <accessToken>` on every request **except** login.
3. **Login:** `POST {baseUrl}/auth/third-party` with `{"username","password"}` → `accessToken`,
   `responseCode "00"`, `responseDescription`. Success needs `00` **and** a token.
4. **The token lasts 15 minutes.** Cache it (shared across workers), log in again after **14
   minutes**, and on a `401` log in again and retry that request **once**. A second `401` is a
   credentials problem: stop. Never log in per request.
5. **Everything lives in config**, server-side only: `INNBUCKS_BASE_URL`, `INNBUCKS_API_KEY`,
   `INNBUCKS_USERNAME`, `INNBUCKS_PASSWORD`, `INNBUCKS_ENV` (test|production), `INNBUCKS_TOKEN_TTL`
   (840). Start from `config/innbucks.env.example`. A mobile app talks to the merchant's server, never
   to InnBucks.

With credentials, `python3 scripts/innbucks_cli.py --env-file .env login` is the fastest proof that
the base URL, key, username and password belong together (`references/authentication.md`).

## 2. Endpoints

Base URL + path. JSON bodies. `responseCode "00"` = success unless noted.

| Purpose | Method + path | Notes |
|---|---|---|
| Login | `POST /auth/third-party` | no bearer; returns `accessToken` |
| Generate code | `POST /api/code/generate` | `type` `PAYMENT` or `WITHDRAWAL`; returns `code`, `qrCode` (base64) |
| Code inquiry | `POST /api/code/inquiry` | body `{"code"}` (+ optional `reference`); read `status` |
| Linked account inquiry | `GET /api/v1/account/msisdn/{263...}/details?currency=USD` | success is **`"000"`** |
| Deposit | `POST /api/transaction/deposit` | agents; `destinationAccount` from linked account |
| Deposit inquiry | `POST /bank/api/transaction/inquiry` | note the **`/bank`** prefix; result in `details.responseCode` |
| Reversal (deposits only) | `POST /api/transaction/reversal/v2` | `type: "CREDIT"`; codes `00` / `025` / `096` |
| Bank change | `POST /api/transaction/bankChange` | USD ≤ 500 cents (US$5; no ZWG limit documented); `destinationMsisdn` |
| Utility payment | `POST /api/utility/provider/payment` | `provider`, `providerProduct`, `additionalData` |
| Account statement | `POST /api/account/fullStatement` | one calendar month max; `yyyy-MM-dd HH:mm:ss` |
| Response-code list | `GET /api/file/response-codes` | download at integration time |

Every field, response and example: `references/api-reference.md`. Alphabetical index with the client
function names: `references/method-index.md`.

## 3. Payload rules

- **Amounts are integer cents** in every request: `450` = US$4.50. Never `4.50`, `"4.50"` or `4.5`.
  InnBucks' own generate example sends `"amount": 1` (1 cent) - don't copy it. The most common bug is
  dollars sent as cents (customer sees US$0.04) or cents multiplied again. Store money as cents.
- **Currencies:** `USD`, `ZWG`.
- **Exact field names:** `destinationMsisdn` (not `msisdn`/`destinationMSISDN`), `destinationAccount`,
  `accountNumber` (statement, deposit inquiry), `participantReference`, `originalParticipantReference`,
  `providerProduct`, `startDateTime`/`endDateTime`, `narration`.
- **`reference`**: optional in the API but always send one, unique per request, **saved before the
  call**. It comes back as `stan`. For deposits it is the **only** key for deposit inquiry and
  reversal (`originalParticipantReference`); duplicate checking, where enabled, rejects a repeated one.
- **Reversal and deposit inquiry each need a NEW `participantReference`**; the deposit's reference
  goes in `originalParticipantReference`. Reversal `amount`, `currency` and `destinationAccount` must
  match the deposit exactly.
- **`narration` appears on the merchant statement**: put the merchant's own order reference in it.
- **MSISDN format** `263XXXXXXXXX`.

`python3 scripts/innbucks_cli.py lint generate body.json` (or `deposit`, `reversal`, `bank-change`,
`utility`, `statement`, ...) checks a payload against all of these.

## 4. The code payment flow

```
save order + reference → generate (cents, narration = ref) → save code/authNumber/time
→ show logo, amount, code, QR, "*569#", 10:00 countdown (+ deep link on mobile)
→ background job: inquiry every 30 s → Claimed | Paid → fulfil once
                                     → Expired | Timed Out → offer a new code
                                     → still New after ~11 min → mark UNKNOWN, review
```

- **A code is valid for 10 minutes.** `timeToLive` (e.g. `"576sec"`) is the time left.
- **Statuses:** `New`, `Claimed`, `Paid`, `Expired`, `Timed Out`. **Both `Claimed` and `Paid` mean
  paid** (InnBucks' guidelines say a paid code shows `Claimed`). Normalise case/spaces before
  comparing (`Timed Out` = `TIMED_OUT`). Read `status` only when `responseCode` is `00`.
- **Poll at most once every 30 seconds per code**, from 30 s after generating - InnBucks asks for this
  explicitly. Do it in a queue/job, not in the customer's web request; the browser polls the
  merchant's own server.
- **Never call a timeout "failed".** Mark it unknown and re-check later.
- **A replacement code does not cancel the old one**: keep checking every code issued for an order.
- **Deep link** (mobile only), scheme from `INNBUCKS_ENV`: test
  `zw.co.innbucksnova.test://purchase?paymentToken={code}`, production
  `com.innbucks.customer://purchase?paymentToken={code}`. Keep the code and QR visible too.
- **QR:** `qrCode` is base64; prefix `data:image/png;base64,` unless it already starts with `data:`.
- **Branding** is reviewed at UAT: official logo (navy on light, white on dark), InnBucks navy
  `#0E2240`; see `references/payments.md` §5.6.

## 5. Agent flows

- **Withdrawal (cash-out):** generate `type: "WITHDRAWAL"`, show it, poll every 30 s, **hand over cash
  only on `Claimed`/`Paid`**.
- **Deposit (cash-in):** linked account inquiry (`"000"` = success; pick the account in the deposit's
  currency) → **agent checks the name against the customer's national ID** (compliance, mandatory) →
  deposit with the merchant's own `reference`.
- **Lost deposit response (timeout, 5xx):** **never re-send.** Deposit inquiry with the same
  reference as `originalParticipantReference` and a new `participantReference`. `details.responseCode`
  is the deposit's result; InnBucks settles every deposit within 30 minutes.
- **Reversal** exists **only for deposits**. `025` = original not found or already reversed (check with
  deposit inquiry); `096` = try later (whether to reuse the `participantReference` is undocumented -
  ask InnBucks, and deposit-inquire first if unsure). Real-time reversals are not available for any
  code-based transaction; InnBucks has a separate reversal process (document + go-live training) -
  never promise an API refund for a code payment.
- **Bank change:** a cash customer's change credited to their wallet, **≤ 500 cents in USD** (no ZWG
  limit documented); validate before calling.

Details and examples: `references/agent-services.md`.

## 6. Errors and retries

- Two layers: HTTP status, then JSON `responseCode`. `00` (or `000` on linked account) is success;
  anything else failed, with the reason in **`responseMsg` or `responseDescription`** (the name varies
  by endpoint - read both).
- Retry only: `401` (once, after re-login), code inquiries (at the next 30 s tick), reversal `096`
  (later, after checking the deposit). **Never re-send a money-moving request** (deposit, bank change, utility,
  reversal) after a timeout or 5xx until you know it failed.
- Log endpoint, reference, `responseCode`, message, HTTP status and the **`X-Trace-Id`** response
  header; never the password, API key or token. InnBucks support asks for the trace id.

Tables: `references/errors-and-retries.md`.

## 7. Templates

Copy the matching template and adapt it; don't write a client from scratch. Each was run against a
mock InnBucks server that checks both headers, re-login after a `401`, exact field names and integer
cents (the Laravel service ran on real `illuminate/http` + `illuminate/cache`).

| Stack | Files |
|---|---|
| PHP / Laravel | `templates/php-laravel/InnBucks.php` (service: `token`, `generateCode`, `inquireCode`, `linkedAccount`, `deposit`, `depositInquiry`, `reverseDeposit`, `bankChange`, `utilityPayment`, `statement`, `ok`, `message`, `codeStatus`, `isPaid`, `isFinal`, `deepLink`, `qrDataUri`) + `InnBucksException.php` + `PollInnBucksCode.php` (queued 30 s check) + `config-services-innbucks.php` |
| Node.js 18+ | `templates/node/innbucks.js` (same functions, plus `waitForCode`) |
| Python 3.9+ | `templates/python/innbucks.py` (`requests`; snake_case names, plus `wait_for_code`) |

When adapting: keep the shared token cache and the single 401 retry, keep cents validation at the
boundary, keep `Claimed` + `Paid` as paid, keep polling in a job with a 30 s floor, and make "mark
paid" idempotent. If the stack is clear from the repo, pick its template without asking.

## 8. Scripts

`scripts/innbucks_cli.py` (Python 3, standard library only; reads the same `INNBUCKS_*` variables,
`--env-file .env` to load them):

- `self-test` - checks the linter. `lint KIND FILE|-` - checks a body (cents, currency, `type`, field
  spelling, MSISDN, new vs original references, bank-change limit, date format, month span).
- `deeplink CODE` - the deep link for `INNBUCKS_ENV`.
- `login`, `generate`, `inquiry`, `wait` (30 s floor), `linked-account`, `deposit`, `deposit-inquiry`,
  `reversal`, `bank-change`, `utility`, `statement`, `response-codes` - live calls; `--dry-run` prints
  the request with secrets masked. Money-moving commands refuse `INNBUCKS_ENV=production` without
  `--allow-live`. Nothing is re-sent after a timeout.

Use it to prove credentials, reproduce a user's failure outside their app, or lint a pasted payload.

## 9. Testing, UAT and go-live

- **Test:** InnBucks' Android test customer app, registered with a Zimbabwean number (InnBucks
  supplies the download link and a test OTP), funded by InnBucks on request. Deep links use the test
  scheme.
- **UAT sign-off form** test cases: authentication, generate payment code, generate withdrawal code,
  code inquiry, code mini statement (no endpoint is documented for this one - ask InnBucks or mark it
  N/A). Record Pass / Pass with exception / Fail / N/A with InnBucks references.
- **Submit** the signed form + a **1-2 minute customer-journey video** (success and failure, each
  enabled transaction type) to merchants@innbucks.co.zw. Changes to the approved journey need
  InnBucks' approval.
- **Go-live:** production credentials and base URL, pre-funding, reversal/help-desk/statement
  training, `INNBUCKS_ENV=production`, one small real payment. Checklists: `references/testing-and-uat.md`,
  `references/go-live.md`.

## 10. When answering or reviewing

- **Debug from the symptom**: `references/troubleshooting.md` (401 after ~15 min = no refresh; 401 on
  everything = missing `X-Api-Key`; 404 on deposit inquiry = missing `/bank`; tiny or huge amounts =
  cents confusion; paid orders not fulfilled = only `Paid` accepted; `000` treated as failure).
- **Cite the rule and its reason**, e.g. "this re-sends the deposit after a timeout, which can credit
  the customer twice; run a deposit inquiry with the same reference instead".
- **Keep documented facts separate from recommendations.** Not documented by InnBucks: base URLs,
  callbacks (there are none), a code-payment refund API, the code mini statement endpoint, field
  length limits, rate limits beyond the 30 s inquiry rule, the full provider/product list, the
  not-found shape of deposit inquiry, `qrCode` image type, merchant-vs-agent capability split,
  the meaning of utility `ledger`/`available`, the ZWG bank-change limit. Say so and point to InnBucks
  (merchants@innbucks.co.zw) rather than inventing. Full list: `references/known-issues.md`.
- **Reviewing an integration:** check it against §1, §3-§6 line by line, then the go-live checklist
  in `references/go-live.md` and best practices in `references/best-practices.md`.
