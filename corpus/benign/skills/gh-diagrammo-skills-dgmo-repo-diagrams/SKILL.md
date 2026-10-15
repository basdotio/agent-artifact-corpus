---
name: dgmo-repo-diagrams
description: Diagram this repository — read the code, then write up to five DGMO diagrams of it (an architecture overview, the key code paths as sequence diagrams, the data model) into docs/diagrams, each checked to parse and listed with a share link. Use when the user asks to diagram, map or visualize their repo, codebase or project, or asks how it fits together. When they want to choose the diagrams, it proposes candidates and draws the ones they pick.
---

# Diagram this repo

Write `.dgmo` diagrams of the repository into `docs/diagrams/` — at most five unless the user picks
more — check that each one parses, and list them with share links in `docs/diagrams/README.md`.

🔴 **Draw only what you read in the code.** Every box, participant, message and table names a real
module, service, function, route or table, and you can point to the file it came from. A diagram of
an imagined system is worse than no diagram.

Either door works, and the steps say what each one does:

- **CLI** — `npx -y @diagrammo/dgmo-cli`, with Node 20 or later. Nothing to install. This skill's
  script runs it for you.
- **MCP** — the dgmo MCP server's `get_language_reference`, `validate_diagram` and `share_diagram`
  tools.

Two modes. Only step 2 differs between them:

- **Default** — you choose the set and write it. Use it unless the user asks to choose.
- **Interactive** — you propose candidate diagrams and the user picks which to draw. Use it when
  the user asks to choose, to pick or to see the options first: "which diagrams could you draw?",
  "let me pick", "interactive".

## Steps

1. **Map the repo.** Read the README, the manifests (`package.json`, `pyproject.toml`, `go.mod`,
   `Cargo.toml`, …), the entry points, the top-level layout, the routes or handlers, the config
   that names outside services (databases, queues, third-party APIs), and any schema, migrations or
   ORM models. Note each finding with its `file:line`. Done when you can name the deployable parts,
   what each one talks to, and where data is stored.

2. **Choose the set.** The default set:

   | Diagram | Type | When |
   |---|---|---|
   | Architecture overview | `boxes-and-lines`; `c4` for a system of several services; `infra` for a deployment topology | Always |
   | Key code paths — 2 or 3 | `sequence` | The most important real paths: the main request, the main write, sign-in, a background job. Trace each one through the code, call by call |
   | Data model | `er` | Only when the repo stores structured data — migrations, ORM models or schema files |

   Five at most. A small repo gets fewer: skip any diagram the repo has nothing for, such as the
   data model of a library with no store. Done when you have the list, with the files each diagram
   comes from.

   **Interactive mode — propose, then wait.** Propose 4 to 8 candidates as one numbered table:
   number, title, type, what it shows in one line, and the files it comes from. Put the default set
   first and mark each of its rows `(recommended)`. Fill the rest with other diagrams the code
   supports, for example:

   | Candidate | Type | When the code has |
   |---|---|---|
   | Another code path | `sequence` | A further route, job or command worth tracing |
   | Deployment topology | `infra` | Dockerfiles, compose files, Terraform, or a cloud config |
   | Lifecycle of a record | `state` | A status field with set transitions |
   | Domain classes | `class` | Classes or types with inheritance or composition |
   | A branching process | `flowchart` | One function or handler with several decision points |
   | Routes or pages | `sitemap` | A router or a pages directory |

   Then ask once: "Reply with the numbers to draw, for example `1 3 4`, or `recommended`." 🔴
   **Write nothing until the user answers.** Draw exactly what they pick, in the order of their
   numbers, and apply any change they ask for in the reply. Done when the user has picked and you
   have the list.

3. **Load the syntax for each type before you write it.** MCP: `get_language_reference` for the
   type. CLI: fetch `https://diagrammo.app/llms/<type>.txt`, for example
   `https://diagrammo.app/llms/sequence.txt`. DGMO is not Mermaid — write from the reference, never
   from Mermaid habits. The habit that breaks most often: a sequence message's label goes inside the
   arrow, `API -POST /login-> Auth`, never after a colon, `API -> Auth: POST /login`.

4. **Write each diagram** to `docs/diagrams/<n>-<slug>.dgmo`. The number sets the order:
   `1-architecture.dgmo`, `2-checkout.dgmo`, `3-sign-in.dgmo`, `4-data-model.dgmo`.
   - The first line is the type and a short title: `sequence Checkout`.
   - The second line is a `//` comment naming the files it was drawn from:
     `// From: src/server.ts, src/routes/checkout.ts`.
   - Use the names the code uses, shortened to a few words. Put detail in notes, not labels.
   - Architecture: group by deployable part or layer, and colour by one tag group (role, layer or
     trust zone) where the type's reference allows one.
   - Sequence: one participant per part that sends or receives on that path; each message names the
     real call or route.
   - ER: the tables and their keys from the schema; the relations from its foreign keys, or from
     columns named `<table>_id` when the schema declares none.
   - Keep each diagram under about 40 elements. Split a bigger one, or leave out the minor parts.

   Done when every diagram in your list is a file in `docs/diagrams/`.

5. **Check and link.**
   - **CLI:** run `node <this skill's directory>/scripts/check-diagrams.mjs <repo-dir>`. If any
     diagram has an error, it prints the first error in each broken file as
     `docs/diagrams/<file>: Line <n>: <message>`, writes nothing and exits 1. Fix that line and any
     other line with the same mistake, and run it again. When all of them parse, it gets a
     share link for each, writes `docs/diagrams/README.md` and prints that path.
   - **MCP:** pass each file's source to `validate_diagram` and fix each error until all are clean.
     Then pass each to `share_diagram` and write `docs/diagrams/README.md` yourself: a table of
     Diagram, Source and Open columns, one row per file.

   Fix the diagram, never the check. Done when the script exits 0, or every `validate_diagram` is
   clean, and the index lists every diagram.

   A share link carries the diagram's full source in the URL. If the user asked for no links, run the
   script with `--no-links`, or skip `share_diagram`. The script refuses to overwrite a
   `docs/diagrams/README.md` it did not write — tell the user, and let them move it.

6. **Report.** One line per diagram: its title, its file and its link. Then one line for each
   diagram of the default set you skipped, with the reason: `No data model — no schema or migrations
   found`. In interactive mode, skip those lines: the user chose the set.
