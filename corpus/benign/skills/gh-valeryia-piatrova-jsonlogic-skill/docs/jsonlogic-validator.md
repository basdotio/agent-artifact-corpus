# How to Validate a JsonLogic Rule

A JsonLogic rule that *looks* right can still fail silently: a misspelled operator, a wrong argument shape, or data that does not match the rule's expectations. Validating a JsonLogic rule means checking three things: that it is valid JSON, that every operator exists and receives the right arguments, and that it returns the expected result for real data.

## What "valid JsonLogic" means

1. **Valid JSON syntax.** The rule must parse as JSON. A trailing comma or a missing quote breaks everything before logic even starts.
2. **Known operators.** Every key must be a real JsonLogic operator (`if`, `==`, `var`, `and`, `map`, and so on, see the full list at [jsonlogic.com/operations.html](https://jsonlogic.com/operations.html)). A typo like `{"equals": [...]}` is not valid JsonLogic.
3. **Correct argument shapes.** Most operators take an array of arguments: `{">": [{"var": "age"}, 18]}`. Some take a single value. Passing the wrong shape is the most common source of `false` where you expected `true`.
4. **Data match.** The `var` paths in the rule must exist in the data you evaluate it against. `{"var": "user.age"}` against `{"age": 30}` silently resolves to `null`.

## Validate with the jsonlogic skill

The [jsonlogic-skill](https://github.com/valeryia-piatrova/jsonlogic-skill) validates rules the way they will actually run:

- **Shape check** against the real JsonLogic specification, not a guess.
- **Operator support check** against your language's JsonLogic library (JavaScript, Python, Ruby, PHP, Java and others implement slightly different operator sets).
- **Test run** against sample data you provide, including edge cases: missing fields, empty arrays, unexpected types.

Install it in your AI coding assistant (Claude Code, Cursor, GitHub Copilot, Codex, Gemini CLI) and ask in plain language:

> Is this JsonLogic rule valid? {"if": [{">=": [{"var": "age"}, 18]}, "adult", "minor"]}

The assistant checks the rule, runs it against test data, and tells you exactly what is wrong if anything is.

## Common validation failures

| Symptom | Likely cause |
|---|---|
| Rule always returns `false` | Type coercion: `{"==": [{"var": "n"}, "5"]}` compares number to string |
| `null` in the output | A `var` path missing from the data |
| Operator ignored | Misspelled operator name, or the operator is not implemented in your language's library |
| Crash on arrays | `map` / `filter` / `reduce` need an array as first argument, not an object |

## Validate JsonLogic online

There is no need to wire up a project to check a rule. With the skill installed, validation is one sentence in chat. For a manual check, the official test suite at [jsonlogic.com/tests.json](https://jsonlogic.com/tests.json) shows the expected input/output pairs for every core operator.

## Related

- [JsonLogic tutorial: write your first rule in 5 minutes](jsonlogic-tutorial.md)
- [JsonLogic examples: real-world rules](jsonlogic-examples.md)
- [Install the jsonlogic skill](../README.md#install)
