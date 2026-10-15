---
name: prompt-check-upstream
description: Manual prompt.
disable-model-invocation: true
metadata:
  opencode/autoinvoke: false
---

Run only when explicitly invoked by the user. Perform the task below now, using the text accompanying this invocation as its input, scope, and additional instructions. Follow explicit user changes to the saved defaults. If no input is supplied, use the current project and conversation where sufficient; ask only for essential missing information. Apply this prompt to this task, not as standing instructions for unrelated future requests.

Compare the relevant upstream releases and source changes with our current implementation and workarounds. Determine which problems are fully fixed, partly fixed, or still present. Check whether existing patches still apply and whether newer capabilities simplify our approach. Separate release-note claims from source evidence and behavior we have tested. Recommend what to retain, update, or retire.
