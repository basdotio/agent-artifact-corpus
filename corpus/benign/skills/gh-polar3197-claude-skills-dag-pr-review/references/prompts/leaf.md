## Kind: leaf (line-level review)

You own a small set of files, or line ranges within them. Review every changed hunk in your scope line by line,
using the upstream summaries as ground truth about the wider change.

For each hunk, ask:
- **Logic:** conditions, off-by-one errors, null or empty cases, wrong variable, inverted checks, early returns that
  skip cleanup.
- **Contracts:** does this code honour the changed contracts listed upstream? Does it break its own callers? Grep for
  them if the signature or behaviour changed.
- **Errors:** swallowed exceptions, errors converted into success, retries without limits, partial writes.
- **State:** shared mutable state, ordering assumptions, transactions, caches that are now stale.
- **Inputs:** any value that crosses a trust boundary without validation, and injection into queries, shells, paths
  or templates.
- **Tests in scope:** do they assert the behaviour they claim to? Were assertions weakened?

Also check what was **removed**. A deleted check or deleted test is often the bug.

### Expansion

If your assignment says you may request expansion and your scope is too big to review well in one pass (roughly more
than the stated line budget, or several unrelated concerns), do not review it superficially. Return
`"status": "NEEDS_EXPANSION"` with a `summary` of what you learned while skimming, and a `children` list that splits
your scope. You can split by file or by line range, as in `"src/big.py:1-300"`. Each child needs `title`, `files`, and
an optional `focus`. Children must together cover every file in your scope.
