---
name: review-c
description: Review animation.c for C issues — memory safety, terminal handling, signal safety, and game logic
allowed-tools: Read, Grep, Glob, Bash, Write
---

Review `animation.c` for the following categories of issues. Be direct and specific — cite line numbers.

## Source context
Current source: !`cat -n animation.c`

---

## What to check

### 1. Memory safety
- Buffer overflows in `write_to_buffer()` — are x/y bounds checked before indexing into `screen_buffer`?
- `malloc`/`free` symmetry — any allocations that might leak?
- Use of uninitialized memory

### 2. Terminal handling
- `enable_raw_mode()` / `disable_raw_mode()` — are they always paired? Can an early exit skip `disable_raw_mode()`?
- `atexit` registration — is it safe to call `disable_raw_mode()` more than once?
- `read_key()` — is it truly non-blocking? What happens on `read()` returning -1 or 0?

### 3. Signal safety
- Are there signal handlers? If not, does `Ctrl+C` leave the terminal in raw mode?
- Any `printf`/`malloc` calls inside signal handlers (unsafe)?

### 4. Game logic
- Snake boundary conditions — what happens when the snake hits an edge?
- Frame timing — is `sleep(1)` the right granularity? Any drift?
- Input handling — can direction reverse instantly (e.g. going right then pressing left)?

### 5. General C hygiene
- Magic numbers without named constants
- Missing `return` values checked (e.g. `write()`, `tcsetattr()`)
- Any UB (undefined behavior): signed overflow, pointer aliasing, etc.

---

Summarize findings by severity: **Critical**, **Warning**, **Suggestion**. Skip categories with nothing to report.

After completing the review, write the full output to `review.md` in the project root using the Write tool.
