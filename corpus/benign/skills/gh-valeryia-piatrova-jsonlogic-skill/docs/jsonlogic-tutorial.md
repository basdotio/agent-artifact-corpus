# JsonLogic Tutorial: Write Your First Rule in 5 Minutes

JsonLogic is a way to write business rules as JSON. Instead of code like `if (age >= 18)`, you write a JSON object that any JsonLogic library (JavaScript, Python, Ruby, PHP, Java and more) can evaluate. Rules become data: storable in a database, sendable over an API, editable without deploying code.

## The basic shape

Every JsonLogic rule is a JSON object where the **key is the operator** and the **value holds the arguments**:

```json
{ "operator": [argument1, argument2] }
```

A real example. "The user is an adult":

```json
{ ">=": [{ "var": "age" }, 18] }
```

Evaluate it against data `{"age": 21}` and you get `true`. Against `{"age": 16}`, `false`. The `var` operator reads a value from the data by path.

## Your first three rules

**1. Comparison.** Give a discount to orders over $200:

```json
{ ">": [{ "var": "total" }, 200] }
```

**2. Branching with `if`.** `if` takes condition/result pairs, plus a final else:

```json
{
  "if": [
    { ">=": [{ "var": "age" }, 18] }, "adult",
    "minor"
  ]
}
```

**3. Combining conditions with `and`.** Premium users over 25 get 20% off:

```json
{
  "if": [
    {
      "and": [
        { "==": [{ "var": "tier" }, "premium"] },
        { ">": [{ "var": "age" }, 25] }
      ]
    },
    0.20,
    0.10
  ]
}
```

## The operators you will use most

- **Data:** `var`, `missing` (check that fields exist)
- **Logic:** `if`, `==`, `!=`, `!`, `and`, `or`
- **Numbers:** `>`, `>=`, `<`, `<=`, `+`, `-`, `*`, `/`, `%`, `max`, `min`
- **Arrays:** `map`, `filter`, `reduce`, `all`, `some`, `none`, `in`
- **Strings:** `cat`, `substr`

The full list with exact behavior is at [jsonlogic.com/operations.html](https://jsonlogic.com/operations.html).

## Test your rule before you trust it

A rule is only done when it runs correctly on real data, including edge cases: what if the field is missing? What if it is a string instead of a number? The [jsonlogic-skill](https://github.com/valeryia-piatrova/jsonlogic-skill) turns this tutorial into a workflow inside your AI coding assistant: describe the requirement in plain language, and the assistant writes the rule, validates it against the real specification, and runs it against your data before showing it to you.

Install it for Claude Code, Cursor, GitHub Copilot, Codex or Gemini CLI (see [install instructions](../README.md#install)), then try:

> Write a JsonLogic rule: orders over $200 get 20% off, over $100 get 10% off, otherwise no discount. Validate it against {"total": 150}.

## Keep learning

- [JsonLogic examples: real-world rules](jsonlogic-examples.md)
- [How to validate a JsonLogic rule](jsonlogic-validator.md)
