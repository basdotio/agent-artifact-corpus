# click-ground

Mouse/keyboard on a 1280×800 grid via `computer_action`.

## Actions

`left_click`, `right_click`, `middle_click`, `double_click`, `mouse_move`, `left_click_drag`, `type`, `key`, `scroll`, `wait`.

## Rules

- Click the center of the element, not edges.
- `type`: click the field first (focus), then type, then screenshot to verify text appeared.
- `key`: combos like `ctrl+s`, `cmd+t`, `alt+tab` go in `text`.
- `left_click_drag`: needs `start_x,start_y` + `x,y` end.
- `scroll`: needs `direction` (up/down) — scroll the hovered pane only.
- After every 3 actions, `screenshot`.

## Example

```json
{"action": "left_click", "x": 640, "y": 400}
{"action": "type", "x": 640, "y": 400, "text": "hello"}
{"action": "key", "text": "ctrl+s"}
```
