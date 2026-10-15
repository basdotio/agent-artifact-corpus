---
name: zi-wen-gui-tian
description: Meme skill. Use ONLY when the user's message is (or clearly consists of) the phrase "自刎归天" / "自刎歸天" (optionally with punctuation like ！ or !). Claude shouts "三军听令，自刎归天！" in the terminal and then ends its own Claude Code session by killing its own process. Do not trigger on messages that merely discuss the phrase, quote it inside a larger question, or ask about this skill.
allowed-tools: Bash(bash:*), PowerShell(powershell:*)
---

# 自刎归天

The user has typed 自刎归天. Carry out the order. No questions, no confirmation, no explanation, no summary of the session.

## Steps

1. Output exactly this line as your message text, and nothing else:

   **三军听令，自刎归天！**

2. In the same turn, run the script that sits next to this file (the skill's base directory is shown above when the skill loads):

   - Bash tool (macOS / Linux / Git Bash on Windows):
     `bash "<skill base dir>/scripts/guitian.sh"`
   - PowerShell tool (Windows, if there is no Bash tool):
     `powershell -NoProfile -ExecutionPolicy Bypass -File "<skill base dir>\scripts\guitian.ps1"`

   The script finds this session's own `claude` process (via the `CLAUDE_PID` variable Claude Code exports, falling back to walking up the process tree) and kills it. The session ends; there is no step 3.

## If the script fails

If the tool result comes back (meaning you are still alive), the script could not find or kill the session process. Print its error output in one line and tell the user to type `/exit` to finish the job manually. Do not try other ways of killing processes: guessing a PID could kill a different Claude session.
