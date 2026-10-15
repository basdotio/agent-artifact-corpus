# Mini-agent

This is a minimal coding assistant with the same behavior as Claude Code.
Minimal: just 280 loc for the agent, 400 loc for tools, 1200 lop for prompts.
Intuitively it "runs an interactive coding agent":
```
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install -r requirements.txt

$ export GEMINI_API_KEY=redacted
$ ./mini_agent.py --model gemini/gemini-2.5-pro

[MODEL: gemini/gemini-2.5-pro + gemini/gemini-2.5-flash]
[IMPLICIT --mcp builtin]
[TRANSCRIPT: /Users/ljw1004/.claude/projects/default/2025-09-01.jsonl]

> Please analyze the files in my current directory and tell me what they do.

  >> <system-reminder># CLAUDE.md (project instructions) ...</system-reminder>
  >> <system-reminder>Your TODO list is empty. Remember that the TodoWrite tool is a great
     way to stay on top of complex tasks.</system-reminder>
[7193 input tokens, 202 response tokens]
  >> LS(...) -> "- /Users/ljw1004/code/mini_agent/\n  - CLAUDE.md\n  - LICENSE
[4042 cached input tokens, 3912 further input tokens, 204 response tokens]
  >> Read(...) -> "    1→# Mini-agent\n    2→\n    3→
  >> Read(...) -> "    1→#!/usr/bin/env python3\n    2→\n    3→from __future__
  >> Read(...) -> "    1→from __future__ import annotations\n    2→from path
  >> Read(...) -> "    1→from __future__ import annotations\n    2→from typi
[55145 input tokens, 5650 further input tokens, 194 response tokens]

< This project is a minimal coding assistant. Here's a breakdown of the key files:
*   `mini_agent.py`: The main script that runs the interactive agent loop.
    It takes user input, communicates with an LLM, and uses tools to perform tasks.
*   `core_tools.py`: Implements the core functionalities (tools) that the agent
    can use, such as reading/writing files (`Read`, `Write`, `Edit`), searching
    (`Grep`, `Glob`), and running commands (`Bash`).
*   `typedefs.py`: Defines the data structures and types used for messages, tools,
    and conversation history (transcripts).
*   `adapter.py`: A module that connects to different Language Models (like GPT,
     Claude, Gemini) through the `litellm` library, allowing the agent to be
     model-agnostic.
*   `test/`: Contains unit tests for the project.
```

## Same mechanics as Claude Code, but none of the "secret sauce"

The behavior of an AI agent is *completely* characterized by only five things,
the things that are sent to the LLM "completion" method:
1. system prompt
2. tool-descriptions
3. user prompt, i.e. what the user types in
4. tool-results
5. system-reminders, i.e. text automatically inserted by the agent into
   the user prompt.

This agent behaves the same as Claude in the mechanical aspects (how its loop behaves,
what tools it has, what behavior they have, when it chooses to send system-reminders).

However when it comes to Claude's "secret sauce", i.e. the content of Claude's
tool-descriptions, system-prompt and system-reminders, this agent has none of
Claude's magic: it only has its own simple versions. (If Claude's version of these
things were plugged into this agent, then it would give byte-for-byte identical output
to Claude).

This agent also prints system-reminders in the UI, so you can understand what's being sent
and when.

## Features

This implementation has none of the UI niceties of Claude Code,
and none of the permissions/safety. What it does have, however:
1. It supports UserPromptSubmit, PreToolUse and PostToolUse hooks, with identical
   format and behavior to Claude Code. (However it only looks for hooks within MCP
   servers, not within a user's ~/.claude/settings.json file)
2. It supports custom subagents, with identical behavior to Claude Code. (However
   it only looks for sub-agents within MCP servers, not within a user's settings file)
3. It supports TODO list, plan mode via `/plan {true|false}`, and all the other
   tools that Claude has -- Read, Edit, MultiEdit, Grep, Glob, LS, Bash,
   WebFetch, WebSearch
4. It supports MCP servers with the `--mcp` command line argument.

You can choose a model. It uses the litellm naming conventions, e.g.
```
--model gpt-4.1                             # uses OPENAI_API_KEY
--model gemini/gemini-2.5-pro               # uses GEMINI_API_KEY
--model anthropic/claude-sonnet-4-20250514  # uses ANTHROPIC_API_KEY
```
The WebSearch tool uses a 'simple' model to digest web-pages before feeding
them to the main model. The simple model is usually automatically inferred,
but you can specify e.g. `--digest-model o4-mini`. Mini_agent uses the model's
prompt caching (which is CRUCIAL!) and displays cache hit numbers.

Mini_agent also exposes *single-step* and *non-interactive* uses. This is powerful for
headless operation e.g. when you want to run the agent remotely but then
migrate it's current state over to the user's machine when it needs help.
It's also handy for integration tests.
Let's explain these features via the command-line args:
```
./mini_agent.py --resume transcript.jsonl --{no-}interactive --{no-}execute-tools -p "What files are in the current directory?"
```
Precisely put, the behavior of mini_agent is two loops.
1. The inner "agentic" loop gets an assistant response from the LLM,
   executes any tools in it and presents the results to the LLM,
   and repeats until the assistant no longer requests tools.
   The `--no-execute-tools` flag will make it exit with code 2
   and print tool-use to the command-line, rather than proceeding.
2. The outer "user interaction" loop gets a prompt from the user,
   runs an agentic loop with it, and repeats. The `--no-interactive`
   flag will make it exit with code 0 rather than asking the user.

Every user message and every assistant message get written to a transcript.jsonl
file, in the same format as Claude Code uses (hence you can start a conversation
in Claude Code and migrate over to mini_agent, or vice versa).
If you supply `--resume` flag then it will resume from that existing
transcript, otherwise it will start a fresh transcript. If you supply
a `-p` prompt (text, or json content-block list) then it will append
this user-message to the transcript before starting its loops.

## Architecture

The key architectural observations:
1. All system-reminders can be expressed through a UserSubmitPrompt hook --
   reminders that files have been modified, that lines are selected in the IDE,
   that the IDE has diagnostic errors, that the agent hasn't used the Todo
   list recently, and so on. Even the initial readout of CLAUDE.md
   can be expressed through UserSubmitPrompt hook.
2. All hooks can be expressed through the existing MCP "read-resource" request.
   So can system-prompts.

What this means is that Claude Code can be accurately expressed through
(1) a small universal interaction+agentic loop (280 loc) which supports hooks
and subagents, (2) all its "behavior" (system-prompt, system-reminders,
tool-descriptions, tool-results) can be put into an MCP server.
I put my own behavior into `--mcp ./core_tools.py`. We could do the same
and put Claude Code's behavior into an MCP, or Gemini CLI's.

Claude Code's entire behavior is just 420 loc plus 1200 lines of prompts!

Claude Code (and Gemini) will both reveal full descriptions+schema
of the tools available to them upon request. *"Please write a list
of every tool you have at your disposal. Give its name, description
and json-schema. Write them into a file called tools.md."* Moreover,
Claude Code was good at examining each tool's schema, and brainstorming
how to exercise all possible edge cases; also at finding the exact
output of Claude Code's built-in tools for all these cases and turning
them into test suites.

During development I used an "inproc" MCP server.
Normal `--mcp ./core_tools.py` communciates over RPC via stdio.
But I also wrote `--mcp builtin`, which links statically
to core_tools.py and calls the tools "inproc". This let me set
breakpoints in the tool implementation and get a good callstack
all the way from agent to tool. I did this by creating a
statically-linked class which looks like mcp.ClientSession
but dispatches statically.

