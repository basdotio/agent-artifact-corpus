---
name: done
description: After the human merges, sync, mark merged tickets done on the board and name the next ticket. No commits. Part of the dev-flow lifecycle (take, implement, address, done).
license: MIT
disable-model-invocation: true
---

# /done

Project facts live in `AGENTS.md`. Read it first.

1. **Sync.** Graphite: `gt sync -f`. Plain git: `git switch <base> && git pull --ff-only`.
2. **Close out.** A merged PR closes its issue through `Closes #<n>`, so closed issues still labelled `status:in-review` are the merged ones: `gh issue list --state closed --label status:in-review --json number`. Run `just task <n> done` for each.
3. **Next.** Name the next ticket using the same rule as `/take` step 2. Do not claim it.

No commits. Shortest complete answer. End with one line: `Next: /take on <model for take in AGENTS.md>.`
