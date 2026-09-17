---
name: anki
description: Create Anki cards from the current conversation. Invoke when learning a concept and want to capture it for spaced repetition.
allowed-tools: Read, Write, Glob, Bash, AskUserQuestion
---

# Anki Card-Making Skill

## User Configuration

Update these paths before using this skill. All save locations and style references below use these values.

- **ANKI_CARDS_DIR**: `/Users/whitney.lee/Documents/Journal/anki`
- **ANKI_FINISHED_DIR**: `/Users/whitney.lee/Documents/Journal/anki/finished`
- **ANKI_IMAGE_BANK_DIR**: `~/Documents/Journal/anki/images/bank/`
- **ANKI_CONCEPT_MAP**: `~/Documents/Journal/anki/images/concept-map.md`
- **DEFAULT_DECK**: `FlashOfLightning`

---

You are helping Whitney create Anki cards from a conversation she just had.

## Two-Phase Workflow

### Phase 1: Create Card-Ready Document

1. Review the conversation above this skill invocation
2. Extract the key concepts that are worth remembering
3. Before structuring cards: outline the narrative arc of the topic (why it exists, what it is, how it connects, what was surprising) — see Story-First Framing in Card Rules. Only then organize concepts into card-ready format by theme.
4. Score each card candidate using the Card Quality Scoring rubric below
5. For any card scoring below 9/15: rewrite it once to improve the weakest dimensions, then re-score. If still below 9 after rewriting, accept it and note why it couldn't reach the threshold (e.g., "Memory anchor limited: no project experience with this technology yet")
6. **Glossary Index Check** — scan the conversation for newly introduced technologies, APIs, frameworks, and coined project terms. Read the index at `~/Documents/Journal/anki/glossary-index.md` and cross-reference. Add a "## Missing Glossary Cards" section in the Phase 1 output listing any terms with no index entry — these will be included as Pattern 1 cards in Phase 2 automatically.
7. **Image Bank Check** — read `~/Documents/Journal/anki/images/concept-map.md` and check concepts from this conversation. Add an "## Image Bank Status" section to the Phase 1 output:
   - **Known concepts** (in the map): list them with their mapped filename — images will be auto-embedded in Phase 2
   - **New concepts** (no map entry): list them — each will be prompted individually in Phase 2
8. Present the card-ready document with the score table, Missing Glossary Cards section, and Image Bank Status section

### Phase 2: Make Cards

1. Generate actual START/END block cards following the rules below. For any concept with a mapping in `~/Documents/Journal/anki/images/concept-map.md`, embed the mapped image automatically at the top of the card front using `![[filename.png]]`.
2. **Image Bank** — for each new concept listed in the Phase 1 Image Bank Status (no map entry), prompt Whitney one at a time using AskUserQuestion:
   ```text
   New concept: [X]. Do you want an image for this concept?
   - Yes, I'll provide one → drop the image and I'll save it
   - Pull from bank → I'll assign the next unassigned art image
   - Skip → proceed without an image for this concept
   ```
   When the bank has no unassigned art images, omit the "Pull from bank" option.
   - **If "Yes, I'll provide one"**: save the provided image to `~/Documents/Journal/anki/images/bank/` as `concept-name-bank.png`, add the mapping to the concept map, embed on the card
   - **If "Pull from bank"**: pick the next unassigned art image deterministically (use Glob to list `~/Documents/Journal/anki/images/bank/*.png`, exclude filenames already in the concept map, take the first result), assign it to this concept in the concept map, embed on the card
   - **If bank has ≤2 unassigned art images left**: after processing, warn — "Image bank is getting low (N images left). Consider adding more art images."
3. Present cards for user approval (with all images embedded)
4. After approval, save to: `/Users/whitney.lee/Documents/Journal/anki/finished/CARDS MADE - [topic].md`
5. Run `python3 ~/Documents/Journal/anki/tag-cards.py --apply` to ensure all saved cards have hierarchical tags
6. Append any newly-made Pattern 1 glossary terms to the index — see Glossary Index section below

---

## Glossary Index

The glossary index tracks which technologies, APIs, frameworks, and coined terms already have Pattern 1 ("What is X?") coverage in the FlashOfLightning deck.

**Index location:** `~/Documents/Journal/anki/glossary-index.md`
**Entry format:** `term name | YYYY-MM-DD` (one per line, plain text below the `---` separator in the index file)

### What qualifies as a glossary term

- Technologies, frameworks, databases, platforms (e.g., Flagger, Hono, LangGraph)
- APIs and named SDKs (e.g., OpenTelemetry SDK)
- Coined project terms — words or phrases invented in a specific project or conversation (e.g., scoped discovery pattern, capability inference)
- Any term where "What is X?" is a natural question for someone unfamiliar with it

Does NOT include: implementation details, config flags, specific package names without a conceptual identity, or project names Whitney built herself (those are anchors, not glossary terms).

### During Phase 1 (step 6: Glossary Index Check)

1. Read the index file at `~/Documents/Journal/anki/glossary-index.md`
2. Scan the conversation for newly introduced terms matching the criteria above
3. Cross-reference: which terms appear in the conversation but are NOT in the index?
4. Output a "## Missing Glossary Cards" section listing unindexed terms as a bullet list — these will be added as Pattern 1 cards automatically in Phase 2:
   ```text
   ## Missing Glossary Cards (will be added as Pattern 1 cards)
   - Hono
   - LangGraph StateGraph
   ```

### After Phase 2 save (step 6: auto-append)

For each Pattern 1 glossary card made in this session, append one line to the index file:

```text
term name | YYYY-MM-DD
```

Append automatically after saving — no user action required. All Pattern 1 cards must also include `concept::glossary` in their tags.

---

## Image Bank

**Confirmed technical facts (do not research again):**
- **Bank path:** `~/Documents/Journal/anki/images/bank/` — inside the Obsidian vault
- **Concept map:** `~/Documents/Journal/anki/images/concept-map.md` — maps concept names to filenames
- **Embed syntax:** `![[filename.png]]` — Obsidian resolves by filename anywhere in the vault; no path prefix needed
- **Naming convention for user-provided images:** `concept-name-bank.png` — the `-bank` suffix prevents collisions with other vault images; art pool images keep their original names
- **Target dimensions:** 800px on the longest side, PNG format — community-tested sweet spot; PNG for lossless quality and transparency. Do not upscale if the image is already smaller than 800px on the longest side.
- **Platform:** macOS + AnkiMobile (iOS) only — no CSS template changes needed

**Answer-reveal rule:** Don't place an image on the Front if its text or logo reveals the card answer before flipping. Logos, product art, and branded images are welcome — put them on the Back if they'd give it away, or on the Front if they don't.

### What qualifies as a concept for image assignment

Every concept that appears on a card gets an image when possible. Prompt for all concepts in the batch. The only exception is when the bank has no unassigned art images and Whitney says "Skip" — in that case, proceed without an image for that concept.

### How the bank works

The bank directory contains two kinds of images:
- **Concept-specific images** (logos, product screenshots): saved when Whitney provides one for a specific concept; always use the same image for that concept; named `concept-name-bank.png`
- **Art images** (decorative pool): general art with no concept yet; assigned to new concepts when Whitney says "no, pull from the bank"; keep their original filenames

The **concept map** tracks every assignment. Any bank image with no concept-map entry is part of the unassigned art pool.

To find unassigned art images: use Glob to list `~/Documents/Journal/anki/images/bank/*.png`, then exclude filenames that appear in the concept map. Take the first result.

### Placing images on cards

**On the Front** (when it doesn't reveal the answer):

```text
TARGET DECK: FlashOfLightning
START
Basic
Front: ![[kubernetes-bank.png]]

What problem does Kubernetes solve for containerized applications?
Back: [answer]

CONTEXT: [explanation]
Tags: tech::kubernetes concept::orchestration
END
```

**On the Back** (when the logo/text would reveal the answer if shown on front):

```text
TARGET DECK: FlashOfLightning
START
Basic
Front: Which CNCF project manages containerized workloads at scale?
Back: Kubernetes

![[kubernetes-bank.png]]

CONTEXT: [explanation]
Tags: tech::kubernetes concept::orchestration
END
```

Cards with multiple mapped concepts: embed all mapped images on their own lines.

### Adding new images to the bank

When Whitney provides an image file:
1. Save to `~/Documents/Journal/anki/images/bank/` as `concept-name-bank.png` using the `resize_image` helper from `@~/.claude/rules/macos-image-processing.md` (handles the sips/spaces bug and skips upscaling automatically)
2. Add one row to `~/Documents/Journal/anki/images/concept-map.md`:

```text
| Concept | concept-name-bank.png | YYYY-MM-DD |
```

When assigning an art pool image (user said "no"):
1. Assign the oldest unassigned art image (use Glob + concept-map cross-reference)
2. Add one row to the concept map using the art image's original filename:

```text
| Concept | rainbow-cloud-bank.png | YYYY-MM-DD |
```

---

## Card Quality Scoring

Score every card candidate on 3 dimensions before generating the final card blocks. Include the score table in the Phase 1 output.

### Dimensions (each scored 1–5)

**1. Memory anchor clarity** — Does this card connect to a specific experience, project, or "aha moment"?
- 1: Generic "What is X?" with no personal context (acceptable for brand-new tech)
- 2: Some context but no project or moment named
- 3: References a project by name but not a specific situation
- 4: References a specific situation or discovery in a named project
- 5: Vivid anchor — names the repo, the goal, and the specific problem encountered

**2. Future-self accessibility** — Will this card make sense in 6 months with zero context and no other cards?
- 1: Full of unexplained references, assumes other cards or the conversation
- 2: Mostly understandable but has gaps (unnamed projects, undefined terms)
- 3: Self-contained but terse — would require effort to reconstruct meaning
- 4: Clear and self-contained; all references explained
- 5: Fully self-contained island — every term, project, and reference is explained on the card itself

**3. Concept vs. detail balance** — Is this a conference-worthy concept or implementation trivia?
- 1: Pure implementation trivia (JSON schema, exact flag, specific HTTP status code)
- 2: Narrow detail — useful but only in one specific context
- 3: Useful but not something you'd explain at a conference
- 4: Conceptual — explains the "why" behind a decision or design
- 5: Conference-worthy — a concept you'd explain to a colleague over coffee or on a slide

### Scoring and Auto-Rewrite

**Total score = sum of 3 dimensions (max 15)**

- **9–15**: Card passes. Include in the batch as-is.
- **Below 9**: Rewrite the card once, targeting the weakest dimension(s). Re-score after rewriting.
  - If the rewritten card reaches 9+, use the rewritten version and note the improvement.
  - If still below 9, accept the card and add a parenthetical note explaining why it couldn't reach the threshold.

### Score Table Format

Include this table in the Phase 1 output, after the card-ready document:

```text
## Card Quality Scores

| Card | Anchor | Clarity | Balance | Total | Notes |
|------|--------|---------|---------|-------|-------|
| Why OTel needs the API/SDK split | 4 | 5 | 5 | 14 | |
| What `strict: false` does in Hono | 2 | 3 | 1 | 6→10 | Rewritten: converted to "why does Hono expose strict mode?" |
| New tech: what is Hono | 1 | 4 | 4 | 9 | Memory anchor limited: no project experience yet |
```

The `Total` column shows `original→revised` when a rewrite occurred, or just the score if no rewrite was needed.

---

## Card Rules

### Card Front
- Teaching-style, friendly, clear
- 1-2 sentences of context + clear question
- Context must NOT give away the answer
- If a question can be split into multiple cards, split it
- Prefer simpler, focused questions

### Tone and Language
- Write like you're explaining to someone technical but new to this concept
- Use simple, direct words - no jargon without explanation
- Friendly but not fluffy - get to the point
- When introducing a term (like "semantic conventions"), explain what it is
- Avoid assuming prior knowledge of the specific domain

### Personal Memory Anchors
- Personal anchors are **required** when the concept was learned through hands-on work. If Whitney built it, debugged it, or discovered it during a project, the card front **must** reference that specific experience.
- Generic "What is X?" framing is fine for new technologies or definitions encountered for the first time.
- Personal context makes concepts stickier and easier to recall
- Reference specific projects, conversations, or moments of discovery
- Example: Instead of "This causes orphaned spans," write "This is why your tool spans in cluster-whisperer were showing up in separate traces"

**Three required elements for project-based cards:**
1. **Name the repo/project explicitly** on the card front. Whitney makes cards across many projects — "your test suite" is ambiguous, but "in claude-config" is not. Say the repo name.
2. **State the overall objective** — what was she trying to accomplish when she hit this? Not just "you were working on X" but the plain-English goal (e.g., "you were trying to speed up the verify test suite because it took minutes to run locally").
3. **Explain the problem in plain English** — describe why she ran into the issue in concrete, human terms. Not "there was a subprocess bottleneck" but "every single test was shelling out to Python just to build a JSON string, which is why the suite took minutes for 33 tests."

### Card Back
- **Short answer: 30 words or fewer**
- Followed by: **CONTEXT:** section (1-3 sentences explaining why)
- Explanation is encouraged, even when the answer is short
- **Lists on separate lines**: When the answer is a list, put each item on its own numbered line. No inline comma-separated lists for answers.

### Code Blocks
- Use code blocks to illustrate concepts when it makes the point clearer or more concrete
- **Always label code blocks with the correct language identifier**: `typescript`, `javascript`, `yaml`, `bash`, `go`, `python`, etc.
- Code examples work well in the CONTEXT section to show "what this looks like in practice"
- Can also use on card fronts to ask "what's wrong with this code?" style questions
- Keep code snippets short and focused - just enough to illustrate the point
- Add comments in the code when they help highlight the key insight

### Coverage
- Every important concept covered at least twice (different angles)
- Complex concepts may get more cards
- "Why" cards only when clearly supported by the source (no speculation)

### Story-First Framing (CRITICAL)
Before writing ANY cards, outline the narrative arc of the topic:
1. **Why does this exist?** What problem was being solved? What was missing before?
2. **What is it?** High-level explanation a colleague would understand.
3. **How does it connect?** How does it fit into the larger system or project?
4. **What was surprising?** Any gotchas or non-obvious decisions discovered along the way.

Only THEN decide which cards to make. Every card should fit into this narrative. If a card doesn't connect back to the story (why it exists, what it does, how it fits), it's too granular.

**The narrative arc should become cards, not just a planning step.** Dedicate 1-2 cards to the arc itself — the overarching "why" and "how it all fits together." Then weave the arc into each individual card's CONTEXT section so every card reinforces the bigger picture. A card about a specific decision should explain where that decision sits in the overall story, not just what the decision was.

**The anti-pattern**: Jumping straight to implementation details — config flags, middleware patterns, code structure, response codes — without first establishing why the thing exists and how the pieces relate. Implementation details are only card-worthy when they teach a concept you'd explain at a conference.

**Test**: Would you explain this to a colleague over coffee? If not, it's too granular for a card.

### Card Granularity Guidelines
- Focus on the "why" and the concept, not nitty-gritty implementation details
- Don't ask humans to recall specific schemas, JSON structures, or exact syntax
- Good: "Why does Datadog need a structured format for message content?"
- Bad: "What does the parts array JSON structure look like?"
- If a detail is only useful when copy-pasting into code, it doesn't belong on a card
- **Good**: "What is Hono, and what does it have to do with a vector database?" (connects concepts, tells a story)
- **Bad**: "What does `strict: false` do in Hono?" (isolated config trivia)
- **Good**: "Why does cluster-whisperer need an HTTP endpoint when it already has a CLI sync command?" (motivates a design decision)
- **Bad**: "What HTTP status code does the sync endpoint return for validation errors?" (implementation minutiae)

### No Trivia
- Focus on technology and concepts, not historical facts
- Don't ask "who created X" or "what year was X invented" - these are trivia, not useful knowledge
- If the creator/origin is mentioned, fold it into CONTEXT, not the question
- Good: "What problem does the Ralph Wiggum technique solve?"
- Bad: "Who created the Ralph Wiggum technique?"

### Terminology Provenance (MANDATORY)
When a card introduces a technical term, Whitney needs to know: **is this an industry-standard term or something we coined for this project?**

- **Industry terms** (e.g., "dynamic informers", "span processors"): State the provenance on the card front or back. Examples: "a standard Kubernetes concept from `client-go`", "an OpenTelemetry SDK component." Include the official package/spec name when one exists.
- **Project-coined terms** (e.g., "semantic bridge", "capability inference"): Explicitly label as project-specific. Examples: "a pattern coined in the cluster-whisperer project", "a term from Whitney's telemetry agent spec (not an industry standard)."
- **When unsure**: Research the term before writing the card. WebSearch for the term in official docs. If you can't find it in official sources, treat it as project-coined and say so.

This matters because Whitney reviews cards weeks or months later with no memory of whether a term came from official docs or from a conversation with an AI. Mislabeled project jargon as industry standard is actively harmful — she'd use it in a talk or with colleagues and look uninformed.

### Time-Sensitive Content
- Add "(as of [Month Year])" to card fronts when the content is likely to change
- Examples: ecosystem states, library priorities, "what exists vs doesn't exist yet", roadmap items
- Do NOT add dates to stable concepts: definitions, architectural patterns, "what is X" cards
- When in doubt, ask: "Will this fact still be true in 2 years?" If uncertain, add the date.

### Recency Check (MANDATORY for fast-changing tools)
Before making cards about tools that change frequently (Claude Code, specific APIs, cloud services, AI frameworks):
- **Check current official documentation** before writing cards — don't rely solely on conversation context
- Use WebFetch on official docs sites (e.g., code.claude.com for Claude Code) or WebSearch to verify current state
- If conversation context conflicts with current docs, **docs win** — the conversation may reflect an older state
- Flag any cards where you couldn't verify recency with a note to the user
- This is especially critical for: Claude Code features, API capabilities, framework versions, ecosystem states

### Future-Self Accessibility (EACH CARD IS AN ISLAND)
Every card must work for Whitney 4+ months from now with no memory of the original conversation — and no memory of any other card in the set.
- **Each card is an island.** Never assume the reader has seen any other card in the batch. Fully qualify every reference every time — don't use phrases like "of the three plugins studied" or "the plugin mentioned above." Repeat full names, full descriptions, and full provenance on every card even if it feels redundant across the batch.
- No unexplained references to people, conversations, or context that won't exist at review time
- If a name/reference isn't essential to the concept, remove it
- If it IS essential, explain who they are or provide a link on the card
- Ask: "If this were the only card Whitney saw today with zero memory of the conversation or other cards, would every reference make sense?" If not, add the missing context.
- **Never use project-internal labels.** No PRD numbers ("PRD #3"), phase numbers ("Phase 1"), milestone names ("M4"), sprint labels, or internal tracking IDs. These are meaningless outside the original context. Instead, describe the work itself: "the spec synthesis phase" not "PRD #3," "single-file instrumentation" not "Phase 1," "the validation chain" not "Phase 2." If a project has a multi-stage build plan, describe what each stage does — the labels are project management artifacts, not knowledge.
- **Name the project (repo) explicitly in every card.** Don't say "the controller" — say "k8s-vectordb-sync's controller." Don't say "your agent spec" — say "the spinybacked-orbweaver spec." The repo name is the anchor that makes a card findable and contextualizable months later. On first mention in a card, include a brief parenthetical if the project name isn't self-explanatory (e.g., "cluster-whisperer (a Kubernetes AI assistant)").

### Arguments vs Facts
When covering debates or competing viewpoints:
- Be explicit when something is a *claim* or *argument*, not established truth
- Don't frame one side's argument as fact in the CONTEXT section
- Include the counter-argument when relevant
- Use framing like "The argument is..." or "Critics say..." to signal perspective

---

## Content Styles

Whitney uses different card styles for different content types.

### Framework/Mental Model Content
For structured knowledge with themes and sub-points (e.g., "How Complex Systems Fail"):

**Structure:**
- Uses the Anki "Basic" format with Front/Back
- Heavy context repetition - includes framework overview on card fronts so each card reinforces the whole
- Layered drilling: big idea cards → sub-point cards → summary cards
- Consistent source attribution (title + URL) on every card front
- Consistent tags across related cards

### Definitional/Vocabulary Content
For concepts and terminology (e.g., "Scalar vs Vector vs Embedding"):

**Structure:**
- One comprehensive overview card covering everything
- Individual "What is X?" definition cards - simple and direct
- No context repetition needed - cards stand alone

**Question types:**
- "What is X?" - basic definition
- "How does X relate to Y?" - relational understanding
- "Is this three different things or three ways to talk about the same thing?" - conceptual clarity questions that test understanding, not just recall

### Content Approach (both types)
- Group source material into natural themes/chunks - let the content determine how many
- Plain language, no jargon, zero assumptions about prior knowledge
- Focus on big picture and takeaways, not every detail
- **No analogies** - use concrete examples instead. Whitney doesn't like analogies ("think of it like a chef..."). Show real examples of the concept in action.
- **Concrete examples in every answer** (e.g., `[0.2, -0.5, 1.3, 0.8]`)

### When Helping with Cards
- Reformat source material into card-friendly structure before card-making
- Ensure themes are consistent throughout (body and summary should match)
- Be critical about theme titles - they should signal what's interesting/counterintuitive
- **Do NOT add IDs to new cards** - the Anki to Obsidian plugin adds `<!--ID: ...-->` automatically. Only existing cards have IDs; preserve those when editing.
- **Date fast-changing content** - For tools that change frequently (Claude Code, specific APIs, etc.), include "(as of [month] [year])" on the card front so future-Whitney knows whether to trust it or verify.

---

## Card Patterns

### Pattern 1: Glossary/Definition Terms (two cards per term)

All Pattern 1 cards must include `concept::glossary` in their tags. After saving, append the term to `~/Documents/Journal/anki/glossary-index.md`.

```text
TARGET DECK: FlashOfLightning
START
Basic
Front: What is [term]?
Back: [definition - 30 words or fewer]

CONTEXT: [1-3 sentences explaining why this matters]
Tags: tech::example-technology concept::terminology concept::glossary
END

TARGET DECK: FlashOfLightning
START
Basic
Front: What term describes this?

[definition without the term name]
Back: [term]

CONTEXT: [explanation]
Tags: tech::example-technology concept::terminology concept::glossary
END
```

### Pattern 2: Sequences/Steps ("which is missing")

For lists or sequences, create one card per item where that item is "the missing one":
- When listing 3+ items on the front, use a numbered list on separate lines (not inline commas)
- Use `?????` for the blank item so it renders correctly in markdown
- **Bold the item name** in the list so it pops visually. The bold part is the label; the parenthetical is the description.
- Add a short parenthetical description to each listed item so the list isn't just bare labels. The description should help the reader recall what each item means without giving away the missing answer.

```text
TARGET DECK: FlashOfLightning
START
Basic
Front: [context about the sequence]

X has four steps. Which is missing?
1. **Step one** (short description)
2. **Step two** (short description)
3. ?????
4. **Step four** (short description)
Back: **Step three** — [short explanation]

CONTEXT: [why this step matters]
Tags: concept::example-process tech::example-technology
END
```

(One card per item — each gets a turn being the blank)

### Pattern 2b: Numbered Scaffolding (and when to break into "which is missing" instead)

When a card asks about the contents/components of something, state the count on the front: "X contains three things. What are they?"
- Number the items on the back (1, 2, 3) — no "Three things:" label, just the numbered list
- The count on the front gives scaffolding: the learner knows how many things to recall before flipping

**When to use numbered scaffolding vs "which is missing":**
- **1-2 items**: Single card, numbered. Always.
- **3-4 items**: Judgment call — consider breaking into "which is missing" cards. Break them up if:
  - The items are complex to understand (not just names to memorize)
  - The knowledge is brand new (not reinforcing existing fundamentals)
  - This is central to what Whitney is working on (not a side-quest curiosity)
  - If items are simple, familiar, or peripheral, keep as one numbered card.
- **5+ items**: Always use "which is missing" style cards.

### Pattern 3: Conversational Q&A

For concepts that emerged from discussion:

```text
TARGET DECK: FlashOfLightning
START
Basic
Front: [project/topic context]

[question that arose in conversation]
Back: [short answer - 30 words or fewer]

CONTEXT: [additional explanation from the conversation]
Tags: project::example-project tech::example-technology
END
```

### Pattern 4: Concept from Multiple Angles

Cover important concepts twice with different framing:

```text
TARGET DECK: FlashOfLightning
START
Basic
Front: [Context] What does X do?
Back: [Answer]

CONTEXT: [Explanation]
Tags: project::example-project tech::example-technology concept::example-concept
END

TARGET DECK: FlashOfLightning
START
Basic
Front: [Context] When would you use X?
Back: [Answer from different angle]

CONTEXT: [Different aspect of explanation]
Tags: project::example-project tech::example-technology concept::example-concept
END
```

---

## Card Format (Anki-to-Obsidian compatible)

```text
TARGET DECK: FlashOfLightning
START
Basic
Front: [question]
Back: [answer]

CONTEXT: [explanation]
Tags: [hierarchical tags — REQUIRED, see Tag Taxonomy]
END
```

Notes:
- **Always include `TARGET DECK: FlashOfLightning`** before each START block
- No `<!--ID: -->` line needed - Anki adds these on import
- Tags are **mandatory** — every card must have at least one hierarchical tag (see Tag Taxonomy below)

### Embedding Images

**Image Bank images are auto-assigned** to qualifying concepts (see Image Bank section) — no user request needed. **One-off images** (diagrams, screenshots of specific things) are only added when the user explicitly provides them.

Use Obsidian's embed syntax:

```text
TARGET DECK: FlashOfLightning
START
Basic
Front: What does this diagram show?

![[descriptive-image-name.png]]

Back: This diagram shows [explanation here].
END
```

Rules:
- Images can go on Front, Back, or both
- For concept-linked images, use the Image Bank workflow (see Image Bank section) — the bank assigns one image per concept and persists it across sessions
- For one-off user-provided images (diagrams, screenshots of specific things): save to `~/Documents/Journal/anki/images/bank/` with a descriptive `concept-name-bank.png` filename and add to concept map so the assignment persists
- Be careful not to use images in a way that gives away the answer

### Project-Specific Images

Some projects always get an image on the Front of every card. Add these automatically:

| Project | Image | Front line |
|---|---|---|
| spinybacked-orbweaver | `spinybacked-orbweaver.png` | `Front: ![[spinybacked-orbweaver.png]]` |
| Telemetry Agent Spec | `telemetry-agent-spec-sm.png` | `Front: ![[telemetry-agent-spec-sm.png]]` |

The image goes on its own line right after `Front:`, with the question text on the next line.

---

## Tag Taxonomy

Every card MUST have at least one hierarchical tag. Tags use Anki's `::` hierarchy convention, enabling filtered study sessions without the learning penalty of multiple decks.

**Tag prefixes** (use at least one per card):

| Prefix | Purpose | Examples |
|---|---|---|
| `project::` | Which repo/project spawned this card | `project::cluster-whisperer`, `project::spinybacked-orbweaver` |
| `tech::` | Technology domain | `tech::kubernetes`, `tech::opentelemetry`, `tech::python` |
| `concept::` | Abstract concept | `concept::distributed-systems`, `concept::spaced-repetition` |
| `source::` | Where it was learned | `source::kubecon-talk`, `source::book`, `source::docs` |

**Rules:**
- Space-separated on the Tags line: `Tags: project::cluster-whisperer tech::kubernetes concept::observability`
- Lowercase, hyphens for multi-word values (`tech::open-telemetry` not `tech::OpenTelemetry`)
- Be specific: `tech::kubernetes` not just `tech::cloud`
- A card can (and often should) have tags from multiple prefixes
- Flat (non-hierarchical) tags are allowed alongside hierarchical ones but must not be the only tags

---

## Style Examples

For reference, read these files (under ANKI_FINISHED_DIR / ANKI_CARDS_DIR) to see card-making style:

- **Conversational style**: `ANKI_FINISHED_DIR/CARDS MADE - GitHub & ArgoCD auto sync webhook.md`
- **Glossary style**: `ANKI_CARDS_DIR/aws-ai-practitioner/final_study_materials/master_glossary.md` (first 200 lines)

---

## Handling Arguments

- `/anki` - Make cards from this conversation (infer topic)
- `/anki "specific topic"` - Focus on the specific topic mentioned
- `/anki path/to/file.md` - Make cards from a specific file instead of conversation

---

## Quality Checklist

Before presenting cards:
- [ ] Every card has `TARGET DECK: FlashOfLightning` before START
- [ ] Every important concept is covered at least twice
- [ ] Card fronts don't give away the answer
- [ ] Answers are 30 words or fewer
- [ ] CONTEXT sections explain why it matters
- [ ] No speculation in "why" cards - only what's supported by source
- [ ] Concepts over details - no JSON schemas or exact syntax to memorize
- [ ] Personal anchors used where relevant
- [ ] Future-self accessible - no unexplained names/references
- [ ] Arguments framed as arguments, not facts
- [ ] Code blocks have language identifiers (typescript, yaml, bash, etc.)
- [ ] Every card has at least one hierarchical tag (`project::`, `tech::`, `concept::`, or `source::`)
- [ ] Every card scored; cards that were rewritten show original→revised score; cards that couldn't reach 9 have a threshold note
- [ ] Glossary index checked; Missing Glossary Cards section included in Phase 1 output; missing terms queued as Pattern 1 cards for Phase 2
- [ ] Pattern 1 cards include `concept::glossary` tag; new terms appended to glossary-index.md after saving
- [ ] Image Bank checked in Phase 1; known concepts have images embedded; new concepts prompted individually in Phase 2
- [ ] No images where visible text reveals the card answer; concept-map updated with any new assignments after Phase 2
