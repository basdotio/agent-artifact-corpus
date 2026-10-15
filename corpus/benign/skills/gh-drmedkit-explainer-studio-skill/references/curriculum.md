# Curriculum data (optional)

The studio works from a concept card alone. If you have curriculum data, the card gets better misconceptions and the
film knows what it may assume. The format the kit was built against (one repo per subject, e.g.
`<subject>-curriculum-essentials`), read-only for explainer work:

| file | content |
|---|---|
| `topics.csv` | `id,title,strand,grade,scope,subgoals,requires,status` |
| `spec/<id>.json` | `id, title, strand, grade, scope, goals, standards, subgoals, links, conventions, owns_shared_skills, notes, open_issues, review_log`: the sub-goals in order and the misconception ids each uses |
| `topics/<id>.json` | per-topic detail |
| `misconceptions.json` | `{ count, misconceptions: [{ id: "mc.<subject>.<strand>.<slug>", name, description, ... }] }` |
| `dependencies.csv/json`, `map.json` | prerequisite and dependent topics |

How to use it:
- The concept card copies `id`, `title`, `grade`, `strand` exactly, and picks 3-6 misconceptions: the topic's own first
  (from its `spec` sub-goals), then fitting ones from neighbouring topics. Validate that every id exists.
- Each explainer step's wrong options are those misconceptions in plain words, with the catalog id in `catalog`; the
  reveal answers the misconception's `description` (why it is tempting, and what the figure shows instead).
- Put the topic id(s) in `topic.config.json` -> `curriculum.ids` and in STATUS (main id first, then the bundle).
- Prerequisites tell you what the film may assume; dependents what the end card can point to.

Without curriculum data: write the misconceptions yourself (from physics-education research and what learners
typically get wrong), give them stable ids (`mc.<subject>.<topic>.<slug>`) and keep them in the card.
