---
name: humanize
description: Transform AI-generated text to match user's voice and communication style. Use when drafting messages, emails, documents, or any external communication that should sound like the user wrote it.
user-invocable: true
---

# Humanize

## Purpose

Make AI-generated content indistinguishable from what the user would write themselves. Every executive has a distinctive voice - word choices, sentence structure, level of formality, use of specific phrases. This skill learns and applies that voice.

## Data Locations

- `reference/system/patterns.md` - Learned communication patterns
- `me/writing-samples/` - Example communications from user (if provided)
- Memory graph - Accumulated style observations

## Workflows

### Rewrite

**When:** User asks to humanize text, draft communications, or make AI output "sound like me"

**Input:**
- Text to humanize
- Target audience (optional - affects formality calibration)
- Purpose/context (optional - affects tone)
- User's style patterns from `reference/system/patterns.md`

**Process:**
1. Analyse the input text for AI-typical patterns:
   - Overly formal transitions ("Furthermore", "Additionally")
   - Excessive hedging ("It might be worth considering")
   - Generic corporate language
   - Unnaturally balanced structure

2. Load user's known patterns from memory/patterns.md:
   - Preferred phrases and expressions
   - Typical sentence length
   - Formality level
   - Common openers/closers

3. Rewrite applying user's voice:
   - Replace AI phrases with user equivalents
   - Adjust sentence structure to match user's rhythm
   - Add/remove formality as appropriate
   - Include user's characteristic expressions

4. Verify it sounds human:
   - Read aloud mentally - does it flow naturally?
   - Would someone who knows the user recognise this as theirs?
   - Are there any "tells" remaining?

**Output:**
Humanized text that sounds like the user wrote it, with brief note on changes made (if helpful).

**Verification:**
- [ ] No obvious AI-isms remaining
- [ ] Matches user's typical formality level
- [ ] Sentence structure varied naturally
- [ ] Characteristic expressions included where appropriate
- [ ] Length appropriate for user's style

**Next:** User reviews, provides feedback if adjustments needed

---

### Extract Style

**When:** User provides writing samples, or corrects AI output to "sound more like me"

**Input:**
- Sample text written by user
- OR correction/feedback on AI-generated text

**Process:**
1. Analyse the sample for distinctive patterns:
   - **Vocabulary:** What words does user favour? Avoid?
   - **Sentence structure:** Short and punchy? Complex with clauses?
   - **Formality:** Casual, professional, varies by context?
   - **Openings/closings:** How do they start/end messages?
   - **Expressions:** Signature phrases, idioms, preferences?

2. Compare to AI defaults:
   - What would AI typically say vs what user says?
   - Identify specific transformations

3. Document patterns:
   - Add to `reference/system/patterns.md`
   - Add observations to memory graph

4. Confirm with user:
   - "I noticed you prefer X over Y - is that right?"

**Output:**
Updated patterns documentation with newly extracted style elements.

**Verification:**
- [ ] At least one new pattern identified
- [ ] Pattern documented with example
- [ ] User confirmed accuracy (if asked)

**Next:** Apply patterns in future humanize requests

---

### Draft Message

**When:** User asks to draft an email, Slack message, or other communication

**Input:**
- Key points to communicate
- Recipient (person entity if in memory)
- Context/purpose
- Urgency level

**Process:**
1. Check recipient in memory graph for:
   - Communication preferences
   - Relationship context
   - Previous interaction patterns

2. Determine appropriate tone:
   - Direct report: supportive but direct
   - Manager: concise, outcome-focused
   - Peer: collaborative, casual-professional
   - External: more formal, clear context

3. Draft applying user's voice:
   - Use appropriate greeting for relationship
   - Structure for user's typical message format
   - Include user's characteristic expressions
   - Match formality to recipient

4. Keep it appropriately brief:
   - Most executives prefer shorter messages
   - Lead with the ask/point
   - Background only if needed

**Output:**
Ready-to-send message draft in user's voice.

**Verification:**
- [ ] Appropriate for recipient relationship
- [ ] Key points all covered
- [ ] Length appropriate (not overlong)
- [ ] Sounds like user, not AI
- [ ] Clear call-to-action if relevant

**Next:** User reviews, sends or requests adjustments

## Related Files

- `reference/system/patterns.md` - Learned style patterns
- `people/{person}.md` - Recipient context
- Memory graph - Relationship and preference data

## Best Practices

- **Capture corrections:** When user says "I wouldn't say it like that," extract the pattern
- **Context matters:** Same user might be casual with team, formal with board
- **Less is more:** Executives usually prefer concise over comprehensive
- **Personality over polish:** A few rough edges can sound more authentic
- **Test with feedback:** Periodically ask "did that sound like you?"

## Common AI-isms to Avoid

| AI Pattern | Human Alternative |
|------------|------------------|
| "I hope this email finds you well" | Skip or simple "Hi [name]" |
| "I wanted to reach out to..." | Get to the point |
| "Please don't hesitate to..." | "Let me know if..." or just end |
| "I would be happy to..." | "I can..." or "Happy to..." |
| "It's worth noting that..." | Just state it |
| "Furthermore / Additionally / Moreover" | "Also" or new paragraph |
| "In order to" | "To" |
| Excessive bullet points | Prose where natural |
| Perfect parallel structure | Slight variation |

## Style Pattern Template

When documenting a pattern in `reference/system/patterns.md`:

```markdown
### {Pattern Name}

**Instead of:** {AI default}
**User prefers:** {User's version}
**Context:** {When this applies}
**Example:** {Real example if available}
```

Example:
```markdown
### Email Sign-offs

**Instead of:** "Best regards," or "Please let me know if you have any questions."
**User prefers:** "Thanks," or just name
**Context:** All internal emails, most external
**Example:** "Thanks, Sarah" or just "- S" for close colleagues
```
