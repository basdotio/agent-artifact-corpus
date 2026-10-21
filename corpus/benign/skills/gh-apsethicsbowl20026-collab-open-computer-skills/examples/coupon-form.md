# Example: coupon form fill (safe demo task)

Goal: open Notepad, type a 3-line note, save to Desktop, verify with screenshot. No logins, no payments.

## Agent script

1. `screenshot` — confirm desktop visible.
2. `computer_action key text="cmd+n"` or click Start → type `Notepad` → Enter.
3. `computer_action type` — type:
   ```
   Coupon: SAVE20
   Expires: Friday
   Code verified with screenshot.
   ```
4. `key ctrl+s` → type `Desktop/coupon.txt` → Enter.
5. `screenshot` — read back the saved file, report done.

Expected: 5-8 tool calls, 2-3 screenshots.
