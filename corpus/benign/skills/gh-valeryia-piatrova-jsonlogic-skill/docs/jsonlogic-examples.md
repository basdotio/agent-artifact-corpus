# JsonLogic Examples: Real-World Rules

Copy-paste JsonLogic rules for common business logic. Each example shows the requirement in plain language, the rule, and sample data. All rules follow the official JsonLogic specification at [jsonlogic.com](https://jsonlogic.com).

## Discount tiers

Requirement: orders over $200 get 20% off, over $100 get 10% off, otherwise no discount.

```json
{
  "if": [
    { ">": [{ "var": "total" }, 200] }, 0.20,
    { ">": [{ "var": "total" }, 100] }, 0.10,
    0
  ]
}
```

Data: `{"total": 150}` returns `0.10`.

## Age gating

Requirement: allow access only to users 18 or older.

```json
{ ">=": [{ "var": "age" }, 18] }
```

Data: `{"age": 21}` returns `true`.

## Role-based access control

Requirement: admins always pass; editors pass during business hours.

```json
{
  "or": [
    { "==": [{ "var": "role" }, "admin"] },
    {
      "and": [
        { "==": [{ "var": "role" }, "editor"] },
        { ">=": [{ "var": "hour" }, 9] },
        { "<": [{ "var": "hour" }, 18] }
      ]
    }
  ]
}
```

## Required form fields

Requirement: the signup form is submittable only when name and email are present.

```json
{
  "and": [
    { "!": [{ "missing": ["name"] }] },
    { "!": [{ "missing": ["email"] }] }
  ]
}
```

The `missing` operator returns the names of absent fields, so wrapping it in `!` means "nothing is missing".

## Shipping cost

Requirement: free shipping over $50, otherwise $4.99.

```json
{
  "if": [
    { ">=": [{ "var": "total" }, 50] }, 0,
    4.99
  ]
}
```

## Feature flag by percentage

Requirement: enable the new checkout for 10% of users, keyed by user id hash.

```json
{ "<": [{ "%": [{ "var": "user_id" }, 100] }, 10] }
```

## Filter a list

Requirement: from a list of orders, keep only the paid ones.

```json
{
  "filter": [
    { "var": "orders" },
    { "==": [{ "var": "status" }, "paid"] }
  ]
}
```

Data: `{"orders": [{"status": "paid"}, {"status": "draft"}]}` returns the paid order only.

## Grade classification

Requirement: turn a numeric score into a letter grade.

```json
{
  "if": [
    { ">=": [{ "var": "score" }, 90] }, "A",
    { ">=": [{ "var": "score" }, 80] }, "B",
    { ">=": [{ "var": "score" }, 70] }, "C",
    "F"
  ]
}
```

## Null-safe greeting

Requirement: greet by name, or fall back to "Guest".

```json
{ "cat": ["Hello, ", { "var": ["user.name", "Guest"] }, "!"] }
```

The second element of the `var` array is the default when the path is missing.

## Date comparison

Requirement: the subscription is active when today is before the expiry date. (Dates compare as strings in `YYYY-MM-DD` format.)

```json
{ "<": [{ "var": "today" }, { "var": "expires_at" }] }
```

## Generate rules from plain language

Writing these by hand works until the rules get nested three levels deep. The [jsonlogic-skill](https://github.com/valeryia-piatrova/jsonlogic-skill) generates, validates and debugs JsonLogic rules inside your AI coding assistant (Claude Code, Cursor, GitHub Copilot, Codex, Gemini CLI). Describe the requirement in words; get back a rule that has already been run against your data.

## Related

- [JsonLogic tutorial: write your first rule in 5 minutes](jsonlogic-tutorial.md)
- [How to validate a JsonLogic rule](jsonlogic-validator.md)
