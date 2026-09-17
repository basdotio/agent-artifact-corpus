---
name: openclaw-fraud-detect
description: Build or update a Stripe fraud-signal webhook service that verifies Stripe signatures, normalizes fraud events, and forwards summaries to OpenClaw (memory_store and alerting). Use when working on Stripe fraud webhook handlers, event allowlists, OpenClaw gateway calls, or Slack alert routing for fraud signals.
---

# Openclaw Fraud Detect

## Overview

Create a small FastAPI webhook service that accepts Stripe fraud-related events, verifies signatures, summarizes risk signals, and forwards the summary to OpenClaw for memory storage and alerting.

## Workflow

### 1. Confirm the baseline implementation

Start from the existing reference implementation and keep changes minimal:
- `/home/coder/fraud-detects/fraud_webhook/app.py`

### 2. Verify Stripe webhook signatures

Use `stripe.Webhook.construct_event` with the `Stripe-Signature` header and `STRIPE_WEBHOOK_SECRET`. Reject invalid signatures with a 400 error.

### 3. Filter to fraud-signal events

Use an allowlist to keep noise low. Default allowlist:
- `radar.early_fraud_warning.created`
- `charge.dispute.created`
- `review.closed`

Only process events on the allowlist and return a structured "ignored" response otherwise.

### 4. Summarize the event

Produce a compact JSON summary that includes:
- event id, type, created, livemode
- charge / payment_intent / customer identifiers
- amount and currency
- risk fields (`risk_level`, `risk_score`, `seller_message`, `network_status`, `reason`) if present

Load detailed field guidance from `references/stripe-fraud-summary.md` if needed.

### 5. Forward to OpenClaw

If the gateway token is present, send:
- `memory_store` via `/tools/invoke` for storage
- a `/v1/responses` request instructing Slack alerting via Civic Nexus tools

Use the environment variables and request shapes in `references/openclaw-gateway.md`.

### 6. Add a test webhook

Keep a `/webhook/test` handler for local testing that accepts a synthesized event payload and reuses the same summary/forwarding pipeline.

## Resources

### references/
- `references/stripe-fraud-summary.md` for event fields, allowlist, and summary shape
- `references/openclaw-gateway.md` for OpenClaw gateway calls and environment variables
