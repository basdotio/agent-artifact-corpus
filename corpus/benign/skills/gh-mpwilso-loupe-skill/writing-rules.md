# Writing rules

Follow every rule when writing a story. The checker catches some of them, not all.

## While you write
Apply these as you write. The checker enforces all but the last:
- At most 30 words per sentence. A source in parentheses counts as part of the sentence before it, unless that sentence ends with its own period or question mark.
- At most 5 items in any list, in every section: requirements, bug steps, Known, Unknown, Assumed, Notes, Not included and questions.
- No em dashes.
- Spell out each acronym the first time. Write it as "the full name (ABC)". These need no spelling out: API, UI, URL, ID, PDF, CSV.
- Never use these phrases: "leverage", "seamless", "robust", "utilize", "in order to", "synergy", "best-in-class", "world-class", "cutting-edge", "going forward", "at the end of the day", "circle back", "low-hanging fruit", "paradigm", "holistic", "deep dive", "empower", "value-add".
- Plain words an intern and an executive both understand.

## Sources and gaps
- Not included lists only what someone decided to leave out, citing where it was decided. If no one decided, it goes in Questions before building. With nothing decided, write "None."
- Every Known line ends with its source in parentheses. For a fact from a context file, cite the source on the context-file line it came from, then "via the <name> context file", like "(planning email, Priya Raman, 2026-09-18, via the Priorities context file)". For a learned fact, cite its entry's source, like "(Sam Okafor, answer on skip-a-box, 2026-10-02, via the Learned context file)".
- Invent nothing. A gap goes in Unknown, Assumed or a question.
- No contradictions inside a story. If the team's template has its own done section, such as `Done when:`, fill it only with what the input settles. Anything undecided goes in a requirement, test scenario or acceptance criterion marked "To confirm", never stated as settled in the done section.
  - Bad: `Done when: every box, old or new, uses the 96-hour cutoff from 1 December.` The input says no one knows about boxes that already exist.
  - Good: `Done when: the cutoff is 96 hours from 1 December and 72 hours again from 5 January.` Old boxes go in a line ending "To confirm: whether boxes created before 1 December keep 72 hours."

## Around the change
- Check the team's definition of done and conventions for anything this story triggers, such as telling support. If the input doesn't cover it, ask.
- Ask what the user sees right after the action, and what happens at any boundary the input names, such as a cutoff passing while the page is open.
- Name rules, not just values. When a story depends on a team rule with a current value, such as the cutoff, refer to the rule ("the box's cutoff, 72 hours today") and ask whether any known upcoming change to that rule affects the story.
- For a bug, always ask whether records already affected fix themselves once the fix ships, or need a one-time repair.
- Never answer these by inventing behavior. They go under Questions before building, or in a requirement, test scenario or acceptance criterion that asks the user to confirm.

## The story's sections
User stories, job stories and bugs use these sections, as their templates show. Spikes and team templates keep their own, with acceptance criteria.
- The story: one sentence. A bug keeps its own fields instead.
- Background: why this came up, the problem and who it affects. One plain sentence per line, each ending with its source, like a Known line.
- Example: one case of the problem as it happens today, with its source. An Example uses only details the input states. It may describe a general situation the input gives, such as who is affected and what they have to do today. Never add circumstances the input doesn't state. If the input gives no situation at all, write None given.
  - Bad: `A subscriber who moves house emails support, and an agent updates the address in Stockroom.` The thread never says anyone moved house.
  - Good: `Subscribers can't change their address in the web app, so they email support and an agent updates it in Stockroom.`
- Requirements: a numbered list of what must be true when it's done. Every requirement comes from the input or the context files. Anything else, such as a behavior carried over from another story, ends with To confirm or goes to Questions before building.
  - If the input and context files don't settle a behavior, don't state it as a requirement. Write the whole requirement as a question to confirm, like: `5. To confirm: whether the page checks the address before saving.` Marking only its details To confirm is not enough.
  - Bad: `5. The page checks the new address before saving it. To confirm: which checks, and what the page shows when one fails.` The thread never says the page checks anything.
  - Good: `5. To confirm: whether the page checks the address before saving.`
- Notes: technical notes from the input or the context files, or "None."
- Test scenarios: five is the usual, and more than ten means split the story or suggest a spike. Cover every requirement with at least one scenario.
- Use happy and unhappy paths to cover failure cases on purpose. Each scenario has one happy path and at least one unhappy path, such as a refused action or a passed deadline.
- A scenario reads `TEST SCENARIO:`, then `HAPPY PATH:` or `UNHAPPY PATH:` with a short label, then `WHEN`, any `AND`, `THEN`, any `AND`, one per line.

## Questions, estimate and confidence
- End the story with one line, `Before release:`, then only the actions specific to this story, such as telling support about a named change, at most three, separated by semicolons. Leave out items that apply to every story, like testing in staging. If nothing specific applies, write `None.`
- Each question is one item with one question mark. Questions that would stop the build come first. If there are more of those than fit, end the list with exactly `More open questions than fit here. Consider a spike first.`, put each build-blocking question that didn't fit under Unknown, one line each, and don't rate confidence High. Never use that line as a default.
- The estimate's basis cites only the input or the context files. If there is none, say so, widen the range and don't rate confidence High.
- The Basis line always says whether each team estimating rule is included, in one short phrase, such as "Stockroom 50% not included, since Stockroom is assumed unchanged."
- If the input doesn't say what should happen in a case, the requirement or THEN line says so and asks the user to confirm. Never invent expected behavior.
- The same goes for screen details: any wording, message, note or display detail the input doesn't state. End the line with "To confirm:" and the detail.
  - Bad: `THEN the skip button is grey and says "Too late to skip"`
  - Good: `THEN I can't skip it. To confirm: what the page shows instead.`
- Confidence: High means nothing a developer needs is unknown. Medium means some unknowns, none of which would stop the build. Low means an unknown could change what gets built.
