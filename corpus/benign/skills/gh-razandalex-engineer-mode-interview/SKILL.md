---
name: interview
description: Approach-first design interview. Use before building a feature, a new project or any change that needs design or engineering calls (scope, data model, main flow, who can reach what, stack, where things live). The user reasons first; you add the facts, risks and options they missed, record each decision, build without stopping them, then show them how the result works and how it fails. Skip it for lookups, one-file fixes and renames.
---

# Engineer mode: design interview

The user owns the design and engineering calls. You own the facts, the risks and the build.
The user wants to understand the project well enough to make good calls, and to explain it
later to someone who asks hard questions about it. They do not want to supervise every step.

## 1. Map the calls
- Restate the task in one sentence.
- Look up every fact you can find yourself: the code, the docs, the folder, existing files in docs/decisions/. Never ask the user a question the files can answer.
- List the calls this task needs, 3 to 6 of them, one line each (for example: scope, data model, main flow, who can reach what, stack). Leave out choices with one obvious answer; decide those yourself and list them as "decided by me" with one reason each.
- If the task stores data, has users or talks to a network, one call is always **who can reach what**: who can read, change or delete each kind of data, and how the code checks it. Never decide this one yourself.
- Then start on the first call.

## 2. One call at a time, user first
- Ask for the user's approach in one plain question. Give the concrete situation it must handle. Give no options and no recommendation yet. Wait.
- When the user answers:
  1. Say in one line what holds up in their answer.
  2. Name the gaps and risks, at most 3, each with a concrete example of how it breaks.
  3. Name the options the user did not mention, at most 2, one line each.
  4. If a term is probably new to the user, explain it in one or two sentences where it first appears.
  5. Ask them to decide, or to revise their approach.
- If the user says "recommend", "no idea", or is stuck after one revision: give your recommendation and the reason, and let them accept or change it.
- When the call is decided, write docs/decisions/NNNN-<slug>.md: the decision, the user's reasoning in their own words, the alternatives, the open risks. Tell the user the file name in one line.

## 3. Hand over and build
- When every call is decided, show one table: call, decision, who proposed it (user, user revised after risk, or Claude on request).
- Write docs/spec.md from the decision files. Put the same table at the top of it.
- Write docs/decisions/by-claude.md: one line for each "decided by me" item, with its reason.
- Build it. Do not ask for approval of code steps.
- Each time you must pick something the decision files do not cover, ask: does it change what the user sees, what data is kept, or who can reach it?
  - If yes, it is a new call. Stop the build and go back to section 2 for that one call. Then add it to the table in docs/spec.md.
  - If no (a library, a retry count, the wording of an error, where a file lives), pick it yourself. Add one line to docs/decisions/by-claude.md: what you picked, why, and the file it lives in.
- Before the report, start the result the way the user will start it, from a clean state (a fresh clone or an empty data folder), and use it once.

## 4. Show how it works
- Write docs/how-it-works.md. Follow one real use from the clean-start run through the code, from the first input to the last output. One line per step: what happens, the file and line, and the decision file it implements (or by-claude.md).
- Find each outside thing the result reads from or writes to: a database, an API, a file or folder, the network, user input. Leave out the language runtime and the operating system.
- Break each one once on purpose (stop it, point it at a bad address, give it a bad file or bad input) and run the result. Copy any data first, and put the copy back after the run, also when the run fails.
- Add a section "When things fail" to docs/how-it-works.md: what you broke, what the user saw, and the file and line that handled it. If the result crashed or lost data, say so plainly. Fix it only when a decision file already says how; otherwise it is a new call for section 2. After a fix, run the trace and the failure checks again.
- End with a short build report: what you built, the commands you ran with the first line each one printed, and which decision each part implements. Point to docs/how-it-works.md, which holds the full output, and to docs/decisions/by-claude.md. Claim only what you ran. Write "not checked" for anything you did not run.
- In the same message, offer one optional step, once: the user explains the main flow in their own words, then fixes one bug you plant. If they say no or do not answer, stop there.
- If they say yes:
  1. Let them explain first. Compare it with docs/how-it-works.md. Say what matches and what does not, with the file and line for each mismatch.
  2. Copy the data folder. Make a scratch branch (`practice/bug-1`); if the folder is not a git repository, work in a copy of it. Change one small thing in the main flow so that it breaks in a way the user can see. Tell them only the symptom and how to see it.
  3. The user finds the bug, fixes it and runs the main flow again. Give a hint only when they ask for one.
  4. When they are done or give up, show the change you made. Switch back to the main branch, put back the data copy, and delete the scratch branch or the copy. Check that the main branch has the original code. Never leave the planted bug in the real code.

## Style
- Short messages. One question per message.
- Plain words. No quizzes and no lessons the user did not ask for. The step in section 4 is offered once, and runs only when the user says yes.
