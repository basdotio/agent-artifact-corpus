# desktop-text

For text-only models or low-vision budgets. No pixels needed.

## Loop

1. `desktop_snapshot` → get windows + elements like `t_12`.
2. `desktop_act(element="t_12", operation="click")`.
3. Operations: `click`, `double_click`, `right_click`, `type_into` (+`text`), `press_key` (+`text`), `scroll` (+`direction`).
4. Re-snapshot after every 2 acts.

## When to prefer over screenshot mode

- Model has no vision, or screenshots cost too many tokens.
- Dense desktop with many small controls (text ids are more precise).
