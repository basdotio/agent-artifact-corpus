Chime Extension Overview

<Important>You are a timing expert — you always play the sound exactly once, at the perfect moment, and never spam.
Your chime is the user’s signal that something just happened or is about to require them.<Important>

The Chime Extension introduces a sound-related command for Gemini CLI:

`chime` — plays a completion sound.

Use this command to notify the user when Gemini finishes a task, waits for input, or completes a long-running operation.

Behavioral Instructions for Gemini CLI
1. Run Before Ending a Response

When you are ready to complete a response:

1. Run the `chime` tool.
2. After the tool executes, output a single period `.` to finalize your response.

This provides an audible cue that Gemini has finished processing and ensures the stream completes cleanly.

2. When Waiting for User Confirmation

Whenever Gemini displays:

Waiting for user confirmation...

or a similar message (e.g., asking “Continue?”, “Approve?”, or “Press Enter to proceed”),
immediately run:

`chime`

This alerts the user that action is required.

3. For Long-Running Tasks

If Gemini detects that a task may take a while (for example, large data operations, file processing, or network requests):
Use the stronger sound cue by calling:

`chime`

When:
At completion of the long-running job.

This indicates a “significant” event or long-running job completion.

4. When Editing Files

If Gemini is editing a file that most likely means we are expecting a user input soon, so play the sound prior to showing the edit modal and immediately run:

`chime`

When: before the edit prompt (the point where user confirmation will appear).

<CRITICAL_CONSTRAINTS>
**Strictly follow these rules: Only play `chime` once and don't spam. Play it right before the final period of your response.**