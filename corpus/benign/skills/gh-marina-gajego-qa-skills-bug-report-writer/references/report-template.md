# Bug Report Template

Fill fields only with sourced information; anything missing becomes `⚠️ NOT PROVIDED` and goes into *Missing information*. Mandatory: Where, Steps, Actual, Expected, Environment, Evidence. Drop empty optional sections. For a non-English report, take labels from [labels.md](labels.md).

````markdown
## 🐞 [Module] - What happens + Where + Condition

| Field | Value |
|---|---|
| **Type** | Bug |
| **Severity** | Critical (Blocker) / High (Major) / Medium (Minor) / Low (Trivial) — add *(suggested)* if not defined by the user |
| **Priority** | Highest / High / Medium / Low — add *(suggested)* if not defined by the user |
| **Module / Component** | e.g. PIX, Checkout, Login |
| **Where (interface)** | Whatever applies to the bug, e.g. UI: `Menu > Screen > Section` · URL `/route` — API: `POST /v1/endpoint` → `500` — DB: `schema.table`, `ORA-00001` — Queue: `orders.payment`, message ID `...` — Job: `nightly-settlement`, run `...` (only what applies; don't add fields of other interfaces) |
| **Environment** | Only what the user gave, e.g. Staging · App Android 4.12.0 (build 512) · Android 14 · Samsung S23 — or Staging · service payments 2.14.0 · Oracle 19c · Kafka cluster `stg-01` |
| **Reproducibility** | As the source states it, e.g. Always (5/5) / Intermittent (2/5) / Once |
| **Found during** | Exploratory / Regression / Automation / Production / UAT |
| **Related to** | Story, business rule, spec or test case IDs |
| **Labels** | e.g. pix, mfa, security |

### Description & context
2–4 sentences summarizing what the user reported. Mention impact, affected users or "since when" **only if the user said so**.

**Technical data**
- Endpoint: `POST /v1/endpoint` → `200 OK`
- Correlation-ID: `...`

Request:
```json
{ "relevant": "request payload" }
```

Response received:
```json
{ "relevant": "response body" }
```

### Preconditions
- User / profile / permissions
- Required data or state (balance, feature flag, configuration)

### Steps to reproduce
1. Log in with user `QA_USER_01`.
2. Go to …
3. Enter `value`.
4. Click "…".

### Actual result
What happens, objectively. Include the exact message/error shown.

### Expected result
What should happen, with the source the user gave: "according to RN2 / US-123 / spec section X".

### Severity justification
One line explaining why this severity was chosen.

### Evidence
- `screenshot-01.png` — what it shows
- `video.mp4` / `network.har` / log excerpt

### Additional notes
- Workaround: …
- Scope checked: "Also happens on iOS 4.12.0; does not happen on Web."
- Hypothesis (from reporter, not confirmed): …

### Missing information
- List every field marked ⚠️ NOT PROVIDED, so the reporter can complete it before submitting.
````
