# Reference 02: Calling Jev through TypeSafe or OpenRouter

TypeSafe's direct API and official SDKs are currently available. OpenRouter is an
alternative access path and is the target of this kit's dependency-free clients.
Choose based on the user's existing account and infrastructure.

## TypeSafe direct API (current first-party path)

- Create a key: https://console.typesafe.ai/keys
- Env var: `TYPESAFE_API_KEY`
- Endpoint: `POST https://api.typesafe.ai/v1/systemone`
- Current model alias: `jev-latest`
- HTTP API: https://docs.typesafe.ai/api
- Python SDK: https://docs.typesafe.ai/sdk/python
- JavaScript SDK: https://docs.typesafe.ai/sdk/javascript
- Official agent skill: https://github.com/typesafe-ai/skills (MIT licensed)

The official agent skill is vendor-maintained and reads the live documentation.
This independent starter kit links to it but is not affiliated with, endorsed by,
or a replacement for TypeSafe's official materials.

## OpenRouter auth and model

- Env var: `OPENROUTER_API_KEY` (get one at https://openrouter.ai/keys).
- Header: `Authorization: Bearer $OPENROUTER_API_KEY`.
- Model slug: `typesafe/jev-1.13` on the raw API; `jev-1.13` when using the SDK
  with the OpenRouter base URL. The live model page is
  https://openrouter.ai/typesafe/jev-1.13 (check it for the current version and
  price).

## OpenRouter through the TypeSafe SDK

Packages: `@typesafe-ai/sdk` (TS/JS), `typesafe_sdk` (Python). Point them at
OpenRouter with your OpenRouter key:

```python
from typesafe_sdk import TypeSafeClient
import os

client = TypeSafeClient(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api",
)
result = client.system_one(
    model="jev-1.13",
    state="I was charged twice for my subscription.",
    questions={
        "refund": {"type": "noul", "instructions": "Is the customer asking for money back?"},
        "department": {
            "type": "choice",
            "instructions": "Which team should handle this?",
            "criteria": {"billing": "Charges and refunds", "technical": "Bugs and outages"},
        },
    },
)
```

Use the SDK when you can: it avoids hand-maintaining response types and endpoint
details. For new direct integrations, follow the current first-party SDK docs
linked above rather than adapting this OpenRouter example from memory.

## Raw HTTP path (dependency-free fallback)

Request body (verified field names):

```json
{
  "model": "typesafe/jev-1.13",
  "state": "Help! My payments have failed for 3 days and nobody answers support.",
  "questions": {
    "is_urgent": { "type": "noul", "instructions": "Does this convey urgency?" },
    "department": {
      "type": "choice",
      "instructions": "Which team should handle this?",
      "criteria": {
        "billing": "Payments, invoicing, refunds",
        "technical": "Bugs, outages, integrations",
        "sales": "Pricing, upgrades, new accounts"
      }
    },
    "frustration": {
      "type": "score",
      "instructions": "How frustrated is the customer?",
      "criteria": ["Calm", "Frustrated", "Very angry"]
    }
  }
}
```

Field rules (verified against OpenRouter and TypeSafe/AIML docs):
- Every question: `type` (noul | choice | score) and `instructions` (the question
  in plain language).
- `choice`: `criteria` is an object mapping each option key to a short description.
  Max 255 options.
- `score`: `criteria` is an ordered array of level labels, lowest first, minimum 2
  and maximum 10.
- `noul`: `criteria` optional (descriptions for the "true"/"false" cases).

RESOLVED DISCREPANCY: one community example used `prompt` / `options` / `rubric`.
The canonical, OpenRouter-and-TypeSafe-documented names are `instructions` /
`criteria`. Use `instructions` + `criteria`.

ENDPOINT - LIVE-VERIFIED 2026-09-22: `POST https://openrouter.ai/api/alpha/decisions`
WORKS on OpenRouter (tested against a real key; request and response shapes below
confirmed live). An alternate path `https://openrouter.ai/api/v1/systemone` also
appears in some docs; `alpha/decisions` is the confirmed one. The scaffolding
client defaults to it and exposes it as a single constant if it ever changes.

## Response shape (verified)

```json
{
  "model": "typesafe/jev-1.13-20260917",
  "answers": {
    "is_urgent": { "type": "noul", "noul": 0.96 },
    "department": {
      "type": "choice",
      "choice": "billing",
      "confidence": 0.97,
      "probabilities": { "billing": 0.98, "technical": 0.02, "sales": 0 }
    },
    "frustration": {
      "type": "score",
      "score": 1.3,
      "confidence": 0.55,
      "legend": { "0": "Calm", "1": "Frustrated", "2": "Very angry" },
      "probabilities": { "0": 0, "1": 0.7, "2": 0.3 }
    }
  },
  "usage": { "input_tokens": 403, "output_tokens": 73, "cost": 0.00003 }
}
```

Read from the response:
- `noul` -> P(yes) float.
- `choice` -> `choice` (winning key), `confidence`, `probabilities`.
- `score` -> `score` (fractional level), `confidence`, `legend`, `probabilities`.
- On OpenRouter, `usage.cost` -> the real dollar cost of that call. The direct
  TypeSafe API documents token usage; do not assume every gateway returns cost.

## Other gateways (mention only if the user asks)

Cloudflare AI, AI/ML API, Vercel AI Gateway, and Requesty may also expose Jev.
Check their current docs if the user already uses one; otherwise prefer the
official TypeSafe direct path or the included OpenRouter scaffolding.

## Two patterns that matter in practice

### The escape option (for `choice`)

A `choice` question forces Jev to pick one of the options you gave it. If a real
input does not fit any of them, Jev still picks the closest one, often at high
confidence. So when the option list might not cover every input, add an explicit
escape option and route on it:

```json
"topic": {
  "type": "choice",
  "instructions": "Which FAQ topic answers this, or none?",
  "criteria": {
    "pricing": "Cost, plans, billing",
    "shipping": "Delivery times and regions",
    "not_faq": "None of these; needs a human"
  }
}
```

Then treat `not_faq` (or your equivalent) as "escalate", instead of relying on a
confidence threshold to notice the mismatch. This is more robust than threshold
tuning alone, because Jev can be confidently wrong on an out-of-scope input.

### Per-input variable criteria (keep instructions generic, vary the state)

If the requirement changes per call (each job posting needs a different number of
years, each tenant has different rules), do NOT bake the specific value into the
question `instructions` - that hardcodes one case and breaks on reuse. Put the
variable requirement in the `state` and keep the question generic:

```json
{
  "state": "JOB REQUIREMENT: 5+ years Python.\n\nRESUME:\n...",
  "questions": {
    "meets_experience": {
      "type": "noul",
      "instructions": "Does the resume meet the years-of-experience requirement stated above?"
    }
  }
}
```

Now the same question works for every posting; only the state changes.
