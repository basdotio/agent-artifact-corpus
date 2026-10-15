# Jev API reference (via OpenRouter; verified Sept 2026, jev-1.13)

This skill calls Jev through **OpenRouter** by default. The request and response bodies
are the same as TypeSafe's native API; only the URL, key, and model slug differ. Question
semantics come from TypeSafe's docs (`https://docs.typesafe.ai/llms.txt`).

## Contents
- Endpoint and auth (OpenRouter)
- Request body
- Question shapes
- Response body and answer shapes
- Validating a response (fail closed)
- Model, limits, pricing
- Errors and retries
- Python and JavaScript examples
- Using TypeSafe's own SDKs through OpenRouter
- Direct TypeSafe route (fallback)
- Other routes (Vercel, Cloudflare, Netlify)

## Endpoint and auth (OpenRouter)

```http
POST https://openrouter.ai/api/alpha/decisions
Authorization: Bearer <OPENROUTER_API_KEY>
Content-Type: application/json
HTTP-Referer: <your site URL>      (optional, for OpenRouter rankings)
X-Title: <your site name>          (optional, for OpenRouter rankings)
```

- Model slug: `typesafe/jev-1.13` — pin it. A floating alias also exists,
  `~typesafe/jev-latest` (**with the tilde** — `typesafe/jev-latest` without it does not
  resolve on OpenRouter).
- Key: `https://openrouter.ai/settings/keys`, env `OPENROUTER_API_KEY` (`sk-or-v1-...`).
  The OpenRouter account needs prepaid credit.
- The path is under `/alpha/`, so it can change. On unexpected 404s, check OpenRouter's
  Jev model page for the current endpoint first.

## Request body

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `state` | string, object, or array | yes | The content to judge. Prefer named JSON fields when it has parts. |
| `model` | string | yes | `typesafe/jev-1.13` on OpenRouter. |
| `questions` | map of id → question | yes | Your ids; answers return under the same ids. Ids are **not** sent to the model. |

## Question shapes

Give every question `type` and `instructions` (the API schema makes `instructions`
optional, but a question without one is ambiguous; `jev.py` requires it). `instructions` may be a string, object or
array. Use an object to carry data the question refers to:

```json
"instructions": {
  "candidate": {"name": "John Smith", "city": "Oakland"},
  "question": "Is the resume for the same person as `candidate`?"
}
```

### noul (yes/no)

```json
{"type": "noul",
 "instructions": "Does the message explicitly ask for a refund?",
 "criteria": {"true": "Asks for money back or credit",
              "false": "Mentions a charge without asking for money back"}}
```
`criteria` is optional; only keys `true` and `false`.

### choice (one of a set, max 255 options)

```json
{"type": "choice",
 "instructions": "Which team should handle this?",
 "criteria": {"billing": "Payments, invoicing, refunds",
              "technical": "Bugs, outages, integrations",
              "none": "No listed team fits"}}
```
`criteria` maps option → description (string/object/array) or `null`. Always give a
no-match option — see the skill's `SKILL.md` for what happens without one.

### score (ordered rubric, 2–10 levels, lowest first — the API accepts 1+; 2–10 is the convention jev.py and other clients enforce)

```json
{"type": "score",
 "instructions": "How frustrated is the customer?",
 "criteria": ["Calm, just stating facts", "Frustrated but civil", "Very angry, strong language"]}
```
`criteria` must be an **ordered list**, not a dict keyed by level — both the Python and
JS SDKs made this a hard requirement in v0.6.0 (2026-09-15). A dict-of-levels example
copied from before that date will fail.

## Response body

```json
{
  "model": "typesafe/jev-1.13-20260917",
  "answers": {
    "is_refund":  {"type": "noul", "noul": 0.95},
    "department": {"type": "choice", "choice": "billing", "confidence": 0.81,
                   "probabilities": {"billing": 0.88, "technical": 0.12, "none": 0.0}},
    "frustration":{"type": "score", "score": 1.05, "confidence": 0.92,
                   "legend": {"0": "Calm...", "1": "Frustrated...", "2": "Very angry..."},
                   "probabilities": {"0": 0.0, "1": 0.95, "2": 0.05}}
  },
  "usage": {"input_tokens": 318, "output_tokens": 34, "cost": 0.0000134}
}
```

- `noul`: P(yes). No `confidence` field. 0.5 means unsure.
- `choice`: top option, full distribution (sums to 1), `confidence` from its shape.
- `score`: probability-weighted level index (may be fractional), per-level distribution,
  `legend` mapping index → description, `confidence`.
- `model`: the **dated snapshot** that answered, not the alias you sent — a request for
  `typesafe/jev-1.13` comes back as `typesafe/jev-1.13-20260917` (thousands of logged
  responses in [jev-certify](https://github.com/nikkoxgonzales/jev-certify) and
  [jev-fanout-bench](https://github.com/blowxian/jev-fanout-bench); the official OpenAPI
  says it "may differ from the alias supplied"). Log it; compare with a prefix match.
- `usage.cost`: USD cost of that call, in **every** OpenRouter Jev response. Use it
  directly instead of estimating from the per-token list price.
- Log `model` from every response so results can be traced to a model version.

## Validating a response (fail closed)

Typed output guarantees a shape, not that the shape matches what you asked. Before acting
on an answer, check it against the question you sent, and treat any mismatch as "no
decision" (fall back), never as a low-confidence yes. `jev.py` does this for every answer
(a failure becomes an error row, never a band); in your own code:

```python
import math

def is_p(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and 0 <= x <= 1

def same_model(pinned, returned):  # "typesafe/jev-1.13" matches "typesafe/jev-1.13-20260917"
    return returned == pinned or (returned or "").startswith(pinned + "-")

def answer_ok(question, answer, pinned_model, response_model):
    if not same_model(pinned_model, response_model) or answer.get("type") != question["type"]:
        return False
    if question["type"] == "noul":
        return is_p(answer.get("noul"))
    options = (list(question["criteria"]) if question["type"] == "choice"
               else [str(i) for i in range(len(question["criteria"]))])
    probs = answer.get("probabilities") or {}
    if not is_p(answer.get("confidence")) or not set(probs) <= set(options):
        return False
    if probs and (not all(is_p(p) for p in probs.values()) or abs(sum(probs.values()) - 1) > 0.02):
        return False
    if question["type"] == "choice":
        return answer.get("choice") in options and (
            not probs or probs.get(answer["choice"], 0) >= max(probs.values()) - 1e-6)
    score = answer.get("score")
    return isinstance(score, (int, float)) and 0 <= score <= len(options) - 1
```

The checks that matter most: the `choice` is one of the options you offered (an invented
id must never reach a dispatcher), the distribution sums to 1, the chosen option is the
most probable one, and the response `model` is the slug you pinned or a dated snapshot of
it (an exact-match check rejects every live response). Also cap the response
size you'll read and disable HTTP redirects on the client, so a misrouted call can't
hand you someone else's body. Keel's Rust client is a complete example of these checks
([`jev-core`](https://github.com/codejunkie99/keel/blob/main/crates/jev-core/src/lib.rs)).

## Model, limits, pricing (jev-1.13)

Limits differ by route — use the one for the transport you're actually calling:

| | OpenRouter (default) | TypeSafe direct |
| --- | --- | --- |
| Slug | `typesafe/jev-1.13` (dated; `~typesafe/jev-latest` also resolves) | `jev-1.13.0` (or the floating `jev-latest`) |
| Context | **32,000 tokens, state + all questions combined** (OpenRouter's documented limit; bisection probes through its `/api/v1/systemone` passthrough accepted the direct-route limits, 64k total / 32k state + longest question, with 1,000 questions in one call — [jev-fanout-bench](https://github.com/blowxian/jev-fanout-bench) round 2 E2 — but `/alpha/decisions` wasn't probed, so `jev.py` keeps 32k) | 64,000 tokens total; 32,000 for state + the single longest question |
| Rate limits | Set by OpenRouter for your key/credit | 250,000 tokens/sec, 1,200 requests/minute — TypeSafe's own docs say these "can change without notice" while demand is high |
| Price | TypeSafe list ~$0.042 per million **input** tokens, output free; OpenRouter's exact charge is in `usage.cost` on every response | Same list price; no per-call cost field, no balance/usage endpoint — track spend yourself |

Other constants, both routes:

| | |
| --- | --- |
| Input | Text only (string, JSON object, array of text). Convert images/binaries first — sending one returns HTTP 200 with maximal uncertainty (0.5), not an error. |
| Language | English best. The state's language is what matters: Korean state cost 6.5 accuracy points, Russian 77.3% vs 88.3% on paired XNLI ([jev-cyrillic-audit](https://github.com/AHTOOOXA/jev-cyrillic-audit)); keep questions in English (see question-design.md, "Known weak spots") |
| Billing | Measured per request: ~261 tokens fixed overhead (not counted toward the context limits), ~8 per question, ~8 per choice option (~21 with a description), ~8 per score level; `usage.cost` = tokens × $0.042/M exactly. Characters per token: English ~4.9, Korean ~1.4, Chinese/Japanese ~1.0 ([jev-fanout-bench](https://github.com/blowxian/jev-fanout-bench) round 2). `jev.py` estimates CJK/Hangul at one token per character |
| Latency | One 13-question request took 0.27 s in TypeSafe's [parallel_questions](https://docs.typesafe.ai/cookbooks/parallel_questions) cookbook; a packed 40-item batch request took ~2.3 s p50 in this project's [live benchmark](https://github.com/Shakibuzzaman3104/claude-jev-funnel/tree/main/benchmarks). `doctor` and `batch` print measured latency. |
| Data | TypeSafe doesn't train on requests; OpenRouter's own data policy also applies. |

Keep the slug in config and re-check thresholds before moving to a new version.

## Errors and retries

| Status | Meaning | Do |
| --- | --- | --- |
| 400 / 404 | Bad body; `400 Unknown model: …` for an unknown or retired pin on TypeSafe direct (e.g. `jev-1.12`); 404 for a moved endpoint or unknown slug on OpenRouter | Fix; don't retry |
| 401 | Missing/invalid key | Fix config; don't retry |
| 402 | OpenRouter account out of credit | Add credit; don't retry |
| 403 | Key limit reached, moderation, or network policy | Fix the key or its limits; don't retry |
| 422 | Body failed validation: `{"detail": [{"loc": [...], "msg": ..., "type": ...}]}` — join `loc` to find the field (e.g. `questions.q.score.criteria.0`) | Fix the request; don't retry |
| 408 | Request timeout | Retry with backoff |
| 429 | Rate limited | Exponential backoff; honour `retry-after-ms`, then `retry-after` (seconds or an HTTP date) |
| 529 | Overloaded | Exponential backoff |
| 5xx | Server error | Backoff, limited attempts |
| 3xx | A redirect | Don't follow it: the redirected request would carry your `Authorization` header to another host. Treat as a configuration error |

Official Python SDK shapes, for reading or porting examples (`typesafe_sdk`,
`_core/question_types.py`, `response_types.py`): `Score(criteria=[...])` takes an ordered,
non-empty list and **rejects `legend=`** (models forbid extra fields — blog examples passing
`legend` won't run); `legend` exists only on the answer, keyed by int, as are its
`probabilities`. `NoulAnswer` has only `type` and `noul` — **no `.confidence` or `.p`**.
A response has `.model`, `.usage` and `.answers`, plus `r.nouls`, `r.choices` and
`r.scores`, each keyed by question id. Choice criteria values may be `None` (an undescribed
label). Large question maps are accepted: 1,000 questions in one request
([jev-fanout-bench](https://github.com/blowxian/jev-fanout-bench)), 1,024 in
[jevinci](https://github.com/achimala/jevinci).

What the official SDKs do (`typesafe-sdk` 0.7.1, `@typesafe-ai/sdk` 0.6.0): retry 408,
429 and 5xx twice, backoff from 0.5 s doubling to a 5 s cap with 25% jitter, 10 s timeout
per attempt; Python caps the whole call at 30 s of retrying, and JS ignores a
server-requested wait above 60 s and uses normal backoff. Both default to the floating
`jev-latest`, so pass `model` explicitly. Every response carries an
`x-typesafe-request-id` (`req_…`) header — put it in error logs and support tickets
(`jev.py` appends it to error messages). `GET /v1/models` on the direct route lists
`{name, description, release_date}` and is a cheap way to check a key or a pin.

On a live path, add a circuit breaker on top of retries: one production gate retries once
and only when `retry-after` ≤ 2 s, stops calling for 120 s after 3 consecutive 429/529s,
spaces calls 0.25 s apart and caches identical calls for 300 s, bounding a call's worst
case at about 2 × timeout + 2 s ([hermes-jev](https://github.com/DoGMaTiiC/hermes-jev),
`plugins/jev-judge/README.md`).

## Python and JavaScript examples

Plain HTTP against the OpenRouter endpoint — no extra dependency, and what this skill's
own `jev.py` script uses. TypeSafe's own SDKs work too, pointed at OpenRouter's
`/api/v1/systemone` passthrough instead of `api.typesafe.ai` — see the next section.

Python (`requests`):

```python
import os, requests

response = requests.post(
    "https://openrouter.ai/api/alpha/decisions",
    headers={
        "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
        "Content-Type": "application/json",
        "X-Title": "My App",  # optional
    },
    json={
        "model": "typesafe/jev-1.13",
        "state": {"ticket": message},
        "questions": {
            "is_urgent": {"type": "noul",
                          "instructions": "Does `ticket` convey urgency?",
                          "criteria": {"true": "Explicitly time-sensitive",
                                       "false": "No urgency expressed"}},
            "department": {"type": "choice",
                           "instructions": "Which team should handle `ticket`?",
                           "criteria": {"billing": "Payments, invoicing, refunds",
                                        "technical": "Bugs, outages, integrations",
                                        "none": "No listed team fits"}},
        },
    },
    timeout=30,
)
response.raise_for_status()
body = response.json()
answers, cost = body["answers"], body["usage"]["cost"]
answers["is_urgent"]["noul"]
answers["department"]["choice"], answers["department"]["confidence"]
```

JavaScript (Node 18+ `fetch`):

```js
const response = await fetch("https://openrouter.ai/api/alpha/decisions", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${process.env.OPENROUTER_API_KEY}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ model: "typesafe/jev-1.13", state, questions }),
});
if (!response.ok) throw new Error(`Jev ${response.status}: ${await response.text()}`);
const { answers, usage } = await response.json();
```

Add retry with exponential backoff on 429/529/5xx in production code.

## Using TypeSafe's own SDKs through OpenRouter

OpenRouter also proxies TypeSafe's native endpoint at `/api/v1/systemone` specifically so
an existing TypeSafe SDK client keeps working after a base-URL and key change — no code
change beyond that (confirmed on OpenRouter's Jev guide). Prefer plain HTTP above for new
code in this skill; use this only if you're migrating an app that already has SDK-based
Jev calls.

Python (`typesafe_sdk`):

```python
import os
from typesafe_sdk import TypeSafeClient

client = TypeSafeClient(api_key=os.environ["OPENROUTER_API_KEY"],
                         base_url="https://openrouter.ai/api")
result = client.system_one(
    model="jev-1.13",
    state="I was charged twice for my subscription.",
    questions={"refund": {"type": "noul",
                           "instructions": "Is the customer asking for money back?"}},
)
```

JavaScript (`@typesafe-ai/sdk`):

```js
import { TypeSafeClient } from "@typesafe-ai/sdk";

const client = new TypeSafeClient({
  apiKey: process.env.OPENROUTER_API_KEY,
  baseURL: "https://openrouter.ai/api",
});
const result = await client.systemOne({
  model: "jev-1.13",
  state: "I was charged twice for my subscription.",
  questions: { refund: { type: "noul", instructions: "Is the customer asking for money back?" } },
});
```

SDK notes, both languages:
- `Score.criteria` must be an ordered list, not a dict keyed by level, since v0.6.0
  (2026-09-15) — the JSON examples in this file already use lists.
- Python SDK v0.7.0 (2026-09-18) switched its serializer from msgspec to pydantic and
  added a `response_model` parameter for stronger typing; v0.7.1 (2026-09-21) stopped
  logging the key value on exceptions.

## Direct TypeSafe route (fallback)

Same body, different URL/key/model: `POST https://api.typesafe.ai/v1/systemone`,
`Authorization: Bearer $TYPESAFE_API_KEY`, model `jev-latest` or the pinned `jev-1.13.0`.
The script supports it with `--provider typesafe`; use it when you have a TypeSafe key
rather than an OpenRouter one.

Rate limits are 250,000 tokens/sec and 1,200 requests/minute, and TypeSafe's own docs say
these can change without notice while demand is high. This route has no balance or usage
endpoint, so the script's local ledger (see `SKILL.md`) is the only spend record; on
OpenRouter, `GET /api/v1/key` also reports key-level usage and remaining limit.

Never put any key (OpenRouter or TypeSafe) in client code: Android APK/AAB, iOS app,
or a browser bundle. An OpenRouter key is especially costly to leak because it can call
every model on the account, not just Jev. Set a credit limit on the key in OpenRouter.

## Other routes (Vercel, Cloudflare, Netlify)

Jev reached several more platforms within days of its Sept 2026 launch. Each has its own
request shape — don't assume `type: "noul"` and `answer.noul` carry over. Not used by
this skill's script; listed here for integrations built on one of them.

| Route | Call | Model id | Key | Request shape |
| --- | --- | --- | --- | --- |
| Vercel AI Gateway — Evaluation API | `POST https://ai-gateway.vercel.sh/v1/evaluate`, or `experimental_evaluate()` from `ai` | `typesafe-ai/jev` | `AI_GATEWAY_API_KEY` | Own shape: question `type` is `"boolean"`, not `"noul"`; answer is `{type, probability}`. |
| Vercel AI Gateway — TypeSafe-compatible | `POST https://ai-gateway.vercel.sh/typesafe/v1/systemone` (base-URL swap for an existing `TypeSafeClient`) | `typesafe-ai/jev` | `AI_GATEWAY_API_KEY` | TypeSafe's own shape (`type: "noul"`, `answer.noul`) — the Gateway analogue of the OpenRouter passthrough above. |
| Vercel AI SDK, `@ai-sdk/typesafe-ai` | `experimental_evaluate({model: typeSafeAi.evaluationModel('jev-latest'), ...})` | `jev-latest` | `TYPESAFE_AI_API_KEY` | Calls TypeSafe directly (default base URL `https://api.typesafe.ai/v1`), bypassing AI Gateway; also uses `"boolean"`, and confidence lives at `result.providerMetadata.typesafe.confidence[id]`. |
| Cloudflare Workers AI | `env.AI.run('typesafe/jev', { state, questions })` | `typesafe/jev` | none — billed to the Workers AI binding | Same shape as TypeSafe direct (`noul`/`choice`/`score`); 32k context. |
| Netlify AI Gateway | `@typesafe-ai/sdk`'s `TypeSafeClient`/`systemOne()`, called from a Netlify Function | (SDK default) | none — Netlify wires credentials and billing automatically | Same shape as TypeSafe direct; no base URL or key to configure. |
