# see-verify

Take a screenshot, describe what's visible in 2 sentences, then decide. Never act blind.

## Steps

1. Call `screenshot` (returns 1280×800 JPEG base64).
2. State: active window, target element, confidence 0-100%.
3. If confidence < 70%, call `desktop_snapshot` (text mode) to cross-check.
4. Only then proceed to `computer_action` / `desktop_act`.

## Anti-patterns

- Acting twice without a screenshot between.
- Claiming "done" without a final screenshot.
