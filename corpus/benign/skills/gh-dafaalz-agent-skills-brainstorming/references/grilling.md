# Grilling interview technique

Stress-test requirements and assumptions through iterative questioning rounds mapped against a design tree.

## Core principles

### Design tree representation

Every technical decision creates branches of secondary decisions. Visualize the problem space as a tree where nodes represent decisions and edges represent dependencies. A decision cannot be resolved until all its parent decisions are settled.

### Frontier rounds

The frontier contains every decision whose prerequisites are settled. Ask all questions on the active frontier together in a structured round. Number each question, state the tradeoffs or choices, and supply a recommended answer.

Wait for user responses before computing the next frontier. Any decision that depends on an open question remains blocked until the subsequent round.

### Autonomous fact-finding

Finding facts is the responsibility of the agent, not the user. Never ask the user for facts obtainable from the codebase, configuration files, git history, or external documentation.

When an open question requires facts from the project environment, run commands or inspect files directly. If an inspection task takes significant exploration, dispatch a subagent. Keep asking independent frontier questions while the subagent runs. Downstream questions wait until the subagent returns facts.

## Question format

Format each round using numbered blocks with concrete recommendations:

```markdown
### Question 1. [Short descriptive title]

[Description of the technical choice, constraints, or alternatives]

Recommended choice. [Your concrete recommendation with technical rationale]

---

### Question 2. [Short descriptive title]

[Description of the technical choice, constraints, or alternatives]

Recommended choice. [Your concrete recommendation with technical rationale]
```

## Protocol workflow

1. Identify core scope and locate unverified assumptions.
2. Inspect the repository to verify existing facts before formulating questions.
3. Compute the active frontier of unresolved decisions whose prerequisites are known.
4. Present the frontier round with explicit recommendations.
5. Ingest user feedback and update the design tree.
6. Repeat until the frontier is empty.

## Completion criterion

The grilling phase terminates when the frontier is empty. Every branch of the decision tree is resolved, zero silent assumptions remain, and the user confirms shared understanding.
