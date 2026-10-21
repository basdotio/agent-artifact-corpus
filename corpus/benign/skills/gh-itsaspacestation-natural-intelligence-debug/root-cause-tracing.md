# Root cause tracing

Reference file of the [`debug`](SKILL.md) skill. Read it when the error appears deep in a
call chain and the origin of the bad value is unclear.

## Principle

A bug surfaces where it is detected, not where it is caused. `git init` in the wrong
directory, a file written to the wrong path, a database opened with an empty name: the
failing call received a bad value from somewhere above. Fix where the value is born.

## Process

1. **Observe the symptom.** Quote the error exactly.
2. **Find the immediate cause.** The line that fails, with `file:line`.
3. **Ask what called it.** Walk the stack one frame up. Note the value passed in.
4. **Keep going.** Repeat until the value is created, not passed.
5. **Name the origin.** That line is the root cause. Cite it.

Example chain, from a test suite that created `.git` inside the source tree:

```
execFile('git', ['init'], { cwd: projectDir })   projectDir = ''
  <- WorktreeManager.createSessionWorktree(projectDir)
  <- Session.initializeWorkspace()
  <- Session.create()
  <- test calls Project.create('name', context.tempDir)
  <- setupCoreTest() returns { tempDir: '' } until beforeEach runs
```

Root cause: a top-level variable read before `beforeEach` filled it. Fix: a getter that
throws when read too early. Not: a guard around `git init`.

## Instrumentation

When the chain cannot be read from the stack trace, log before the dangerous call, not
after it fails:

```ts
console.error('[DEBUG-7f3a] git init', { directory, cwd: process.cwd(), stack: new Error().stack });
```

Use `console.error` in tests: loggers are often silenced. Include directory, cwd,
environment variables, and a timestamp. Run once, grep the marker, read the stack.

Tag every temporary log line with one prefix chosen for this investigation, such as
`[DEBUG-7f3a]`. Cleanup is then one search for the prefix. An untagged probe gets
forgotten and ships.

## Test pollution

When a side effect appears during the suite and no test owns it, bisect: run the tests
one by one, stop at the first that leaves the artefact behind. A shell loop over the test
files with an existence check after each run is enough.

## Defence in depth

After the fix at the source, add a check at each layer the bad value crossed: validate
at the entry point, validate before the side effect, refuse the side effect outside the
expected directory in test environments. The bug becomes impossible, not only fixed.
