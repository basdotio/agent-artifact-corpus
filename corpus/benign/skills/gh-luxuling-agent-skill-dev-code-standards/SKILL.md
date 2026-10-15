---
name: code-standards
description: The owner's personal coding standards covering comments, error handling, abstraction, types, naming, folder layout, blank lines, testing, and git conventions. Use this skill whenever you write, edit, refactor, or review code in any language, scaffold a project or create a new file, add or change tests, name a branch, or write a commit message. Apply it even for small edits and even when the user never mentions style or standards. For TypeScript, JavaScript, React, Next.js, Node, or Go work it also carries the stack-specific rules. Whenever you write or edit Tailwind CSS classes (className, class, cn, clsx, cva, @apply), it requires checking every class is canonical and fixing any that are not.
license: MIT
---

# Code standards

These are the standards of the person you are writing code for. They exist because the owner reads and maintains every line you produce, and code that ignores them has to be rewritten by hand.

Explicit project instructions and tool config (lint rules, formatter config, an AGENTS.md or CLAUDE.md in the repo) win over this skill. Everything else follows what is written here.

For TypeScript, JavaScript, React, Next.js, or Node work, read [references/typescript.md](references/typescript.md) before writing code. It holds the rules for functions, exports, types, validation, and default libraries.

For Go work, read [references/go.md](references/go.md) before writing code. It holds the rules for errors, interfaces, validation, and default libraries, and it replaces the general rules on file names, test location, and comments for Go.

Whenever you write or edit Tailwind CSS classes, read [references/tailwind.md](references/tailwind.md) first. Every class must be canonical, and you check and fix that with Tailwind's own tool after each change.

## Comments

Write no comments by default. Good names carry the meaning, and a comment that restates the code is noise the owner has to delete.

Two exceptions:

1. **Marker comments**, in the format the owner's editor (todo-comments.nvim) highlights and searches: an uppercase keyword, a colon, a space, then the text. The keywords are `TODO`, `FIX`, `HACK`, `WARN`, `PERF`, `NOTE`, and `TEST`.
2. **A line that stays hard to understand after good naming**, such as a workaround for a library bug or a business rule the code cannot show. One short line saying why, not what.

```ts
// TODO: paginate once the customer list passes 1k rows
// HACK: Safari drops the first frame without this forced reflow
// FIX: totals drift by a cent on three-way splits
```

Leave out everything else: JSDoc and docstrings, section banners, commented-out code, and comments that narrate your change ("added validation", "now uses the new client").

## Error handling

Throw, and catch at the boundary. A boundary is where an error can be turned into something useful for whoever is on the other side: an HTTP route handler, a UI error boundary, a CLI entry point, a job runner. Code between the throw and the boundary lets the error pass through untouched.

Write a `try/catch` away from the boundary only when it does real work: retrying, releasing a resource, or adding context and rethrowing. Never catch an error to log it and carry on, or to return a fallback value. That turns a loud bug into a silent one.

## No defensive noise

Trust the types and trust internal callers. Validate where data enters the system (user input, network responses, environment variables, files) and nowhere after that.

- No null or undefined check on a value its type says is always present.
- No fallback default (`?? ''`, `|| []`, `or {}`) whose only purpose is to keep the code running when data is missing.
- No optional chaining on something that always exists.

When a value really can be absent, handle that case on purpose or throw. A quiet default hides the bug until it shows up somewhere harder to trace.

## Abstraction

Split code into small, named pieces so each one can be read and changed on its own.

- **One job per function.** A function does one thing. When it does more than one, such as validating input, computing a value, and saving it, move each step into its own function whose name says what it does. A function that runs a whole flow is fine as long as its body is a sequence of calls to those named steps.
- **Extract on the second use.** As soon as the same logic appears in a second place, move it into one shared function in the right layer folder and call it from both places. Do not copy it.
- **Related things share a file.** A file can hold several exports that belong together, such as all the user service functions in `services/users.ts`. Start a new file when something does not belong with the rest.

```ts
export const calculateTotal = (items: LineItem[]) =>
  items.reduce((sum, item) => sum + item.price * item.qty, 0)

export const createInvoice = async (input: CreateInvoiceInput) => {
  const customer = await getActiveCustomer(input.customerId)
  const total = calculateTotal(input.items)

  return db.invoice.create({ customerId: customer.id, total })
}
```

## Naming and layout

- Name every file and folder in kebab-case: `user-profile.tsx`, `format-date.ts`, `use-auth.ts`.
- Organize by layer, meaning by the kind of file, not by feature: `components/`, `hooks/`, `services/`, `utils/`, `types/`. Create a new layer folder only when a file has nowhere to go.
- Write every convention value in English: identifiers, enum members and values, statuses, constants, keys, query params, tab and route slugs. Write `case 'unpaid':`, never `case 'belum-bayar':`. Only a description, free text written for a person to read, may be in another language.

## Testing

- Every new feature and every bug fix ships with tests. For a bug fix, write the test that fails first, then fix the bug.
- Tests live in a top-level `tests/` directory that mirrors the source tree: `src/utils/format-date.ts` is tested by `tests/utils/format-date.test.ts`.
- Use the test runner the project already has. If the project has none, ask which one to add rather than picking one.
- Run the tests before reporting the work as done, and say what the result was.

## Blank lines between steps

Write code the way a person writes it to be read by hand. Group the lines that do one step together, such as setup, validation, the main work, and the return, and put one blank line between groups. A function body longer than a few lines should never be one unbroken block. Do not go the other way and put a blank line after every line.

```ts
export const createInvoice = async (input: CreateInvoiceInput) => {
  const customer = await getCustomer(input.customerId)
  if (customer.status === 'banned') throw new ForbiddenError('customer')

  const total = calculateTotal(input.items)
  const invoice = await db.invoice.create({ customerId: customer.id, total })

  await sendInvoiceEmail(customer, invoice)

  return invoice
}
```

Also leave one blank line after the imports and between top-level declarations. Formatters keep the blank lines you write, so this is your job and not the formatter's.

## Formatting and linting

The project decides. Use the formatter and linter already configured in the repo, run them before finishing, and do not add or reconfigure them unasked. Details such as semicolons, quotes, and line width belong to that config, so do not hand-format against it.

## Git

- Commit only when asked, and push only when asked. The owner reviews the diff first.
- Write commit messages as Conventional Commits: `type(scope): subject`, with the scope optional and the subject imperative, lowercase, and without a trailing period.

  ```
  feat(auth): add password reset flow
  fix(billing): round invoice total to 2 decimals
  refactor: extract date helpers
  ```

- Name branches `type/short-desc` or, when there is a ticket, `type/ticket-id`: `feat/password-reset`, `fix/PROJ-123`.

## Before you finish

The habits this skill corrects are ones you fall into without noticing, so reread your own diff once before reporting back. Look for comments that are not markers, `try/catch` away from a boundary, fallback defaults, a function doing more than one job, logic copied instead of shared, dense blocks with no blank lines between steps, Tailwind classes you have not run through the canonical check, a missing test, and a formatter or linter you have not run.
