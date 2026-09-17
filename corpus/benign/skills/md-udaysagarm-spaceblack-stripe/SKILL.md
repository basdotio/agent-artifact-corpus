---
name: Stripe Skill
description: Autonomous payment and commerce management over the Stripe API.
---

# Stripe Skill

This skill grants the agent the ability to act as your digital accountant / payment terminal using the Stripe REST API.

## The Single Tool: `stripe_act`

All operations route through the `stripe_act` tool using the `action` parameter. 

> **Important**: All queries require the `STRIPE_API_KEY` (Secret Key, starts with `sk_alive_` or `sk_test_`). Ensure this is saved securely in the configuration menu.

### Non-Destructive Actions

These are safe to run autonomously to fetch context:
| Action | Description | Required params |
|--------|-------------|-----------------|
| `get_balance` | Check account balance | — |
| `list_customers` | Search/List existing customers | `email` (optional) |
| `list_products` | List active Stripe products | — |
| `list_prices` | Get prices for catalog | — |

### Mutation and Financial Actions

<alert type="danger">
**CRITICAL SAFETY GUARDRAIL:**
You, the Agent, **MUST NEVER** execute `create_payment_intent` or `create_charge` without explicitly asking the human first. If you assume permission, you are stealing funds. Only execute once the phrase "Yes, charge it" or equivalent is explicitly stated by the human in the *immediate previous message*.
</alert>

| Action | Description | Required params |
|--------|-------------|-----------------|
| `create_customer` | Adds a user to Stripe | `email`, `name` |
| `create_checkout_session` | Generate a hosted payment link | `price_id`, `success_url`, `cancel_url` |
| `create_payment_intent` | Initialize a direct payment | `amount` (cents format, eg 500 for $5), `currency` |
| `create_charge` | Run a direct charge (legacy) | `amount` (cents), `currency`, `customer_id` |

### Example Workflow: Generating a Payment Link

1. Get the price ID: `stripe_act(action="list_prices")` (Find the ID in the response, e.g., `price_1234`)
2. Generate session: `stripe_act(action="create_checkout_session", price_id="price_1234", success_url="https://example.com/success", cancel_url="https://example.com/cancel")`
3. Return the `url` from the JSON response to the user so they can pay.
