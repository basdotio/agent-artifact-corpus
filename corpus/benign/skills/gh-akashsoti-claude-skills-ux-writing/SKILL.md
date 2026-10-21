---
name: ux-writing
description: Analyze any screen (mobile or desktop) and suggest UX writing improvements for all text elements — buttons, headings, error messages, form labels, empty states, notifications, tooltips, and more. Use this skill whenever the user shares a screenshot, mockup, wireframe, or Figma link and asks for copy feedback, UX writing suggestions, content review, microcopy improvements, or help writing UI text. Also trigger when the user asks about writing for buttons, CTAs, error messages, form labels, empty states, onboarding, tooltips, notifications, dialogs, or any interface text — even without sharing a screen. This skill covers everything from individual label rewrites to full-screen content audits. Always use this skill for any request involving UI text, UX copy, content design, microcopy, or interface language.
---

# UX Writing Skill

Suggest clear, concise, and user-centered copy for any screen or UI element shared by the user.

This skill synthesizes UX writing best practices from NNGroup research, Google Material Design guidelines, Shopify Polaris content system, and Deliveroo's content design team into a practical framework for analyzing and improving interface text.

## How This Skill Works

When the user shares a screen (screenshot, mockup, wireframe, or description), follow this process:

### 1. Read the Reference Files

Before responding, read the appropriate reference files:

- **Always read first**: `references/screen-analysis-framework.md` — Contains the step-by-step analysis process, audit checklist, tone mapping, and output format.
- **Read when rewriting specific elements**: `references/component-guidelines.md` — Contains detailed do/don't rules for every UI component type (buttons, errors, headings, forms, empty states, dialogs, navigation, and more).

### 2. Analyze the Screen

Follow the Screen Analysis Framework:

1. **Identify context** — Who is the user? Where are they in their journey? What's their emotional state? What platform is this (mobile/desktop)?
2. **Catalog every text element** — Walk through the screen and tag every piece of text: titles, headings, buttons, labels, descriptions, errors, help text, placeholders, links, status text, microcopy.
3. **Audit each element** — Check against the criteria: clarity, conciseness, usefulness, consistency, tone, and accessibility.
4. **Consider the reading pattern** — How will users scan this screen? What will they see first? Are the most important words front-loaded?

### 3. Provide Suggestions

Structure your output clearly. For each text element that needs improvement:

```
ELEMENT: [type]
CURRENT: "[existing text]"
SUGGESTED: "[improved text]"
REASON: [why this change helps, citing a specific principle]
```

Then provide an overall screen assessment covering:
- **Biggest wins** — The 2-3 highest-impact changes
- **Tone assessment** — Is the overall tone right for this context?
- **Consistency issues** — Mismatches in terminology, voice, or capitalization
- **Missing elements** — Copy that should exist but doesn't (help text, error states, empty states)
- **Mobile/responsive notes** — If relevant, any text that's too long for smaller screens

## Core UX Writing Principles

These principles inform every suggestion. They are drawn from decades of research and practice.

### 1. Clarity Above All

People don't read interfaces — they scan. Every word must be immediately understandable.

- Use plain language. "Start" not "Initiate". "Use" not "Utilize". "Show" not "Render".
- Write in present tense. "Message sends" not "Message will be sent".
- Be direct. "Save changes?" not "Would you like to save your changes?"
- Omit unnecessary words. Remove "please", "successfully", "in order to", "that" when the sentence works without them.
- Use simple verb forms. When you need past or future tense, keep it simple.

### 2. Brevity Is Respect for the User's Time

Every extra word is a tax on the user's attention. Cut ruthlessly.

- Can this paragraph be a sentence? Can this sentence be a phrase? Can this phrase be a word?
- Approach content like Jenga — remove the most you can before things collapse.
- Front-load key information. The first 2 words of any line are the most-read words.
- On mobile, brevity is even more critical — screen space is expensive.

### 3. Action Over Description

UI text should help users do things, not just understand things.

- Start with verbs: "Add a product" not "Products can be added here."
- Buttons must describe the action: "Save draft" not "OK". "Delete account" not "Continue".
- Error messages must include a path to recovery: what happened + how to fix it.
- Empty states must include a call to action, not just a description of emptiness.

### 4. Consistency Builds Trust

Inconsistent language makes an interface feel broken.

- Use the same word for the same concept everywhere. Don't alternate between "Delete", "Remove", and "Trash".
- Match button labels to their destination: if the button says "View details", the next page title should be "Details".
- Address the user consistently: either "you/your" (second person) or "I/my" (first person), never mix them in the same context.
- Use sentence case throughout (capitalize only first word and proper nouns) unless the product has an established different convention.

### 5. Tone Adapts to Context

The right words at the wrong moment can feel jarring. Match your tone to the user's emotional state.

- **Errors**: Empathetic and constructive. Never blame the user. "A phone number is required" not "You didn't enter a phone number."
- **Success**: Positive and forward-looking. "Order placed! You'll get a confirmation email shortly."
- **Onboarding**: Warm and benefit-focused. Lead with what the user gains, not what the product does.
- **Destructive actions**: Plain and unambiguous. No softening, no humor. "This permanently deletes all your data."
- **Routine tasks**: Neutral and efficient. Don't inject personality where the user just wants to get things done.

### 6. Avoid These Words and Patterns

Based on research, these consistently cause problems:

| Avoid | Why | Use Instead |
|---|---|---|
| "Invalid", "illegal", "incorrect" | Judgmental; blames the user | Describe what's needed: "Enter a valid email" |
| "Error occurred" | Vague; no information content | Describe the specific problem |
| "Please" (in most UI) | Adds noise; makes the UI feel needy | Just state the action: "Enter your email" |
| "Successfully" | Redundant; the success state already communicates success | "Saved" not "Saved successfully" |
| "Click here" / "Learn more" | Non-descriptive; poor accessibility | Describe the destination or action |
| "We" (unless a human acts) | Shifts focus from user to company | Focus on what the user can do |
| "Oops!" | Minimizes user frustration; feels performative | State the problem plainly |
| "Never" or other absolutes | Can't guarantee absolutes | "Your data isn't shared" not "We'll never share your data" |
| Exclamation marks (except celebrations) | Feel like shouting or fake enthusiasm | Use sparingly, if at all |

## When the User Doesn't Share a Screen

If the user asks a general UX writing question (e.g., "how should I write error messages?" or "what's a good CTA for a sign-up page?"), consult the relevant section of `references/component-guidelines.md` and provide:

1. The core principles for that element type
2. Do/don't examples (both what to write and what to avoid)
3. If the user provides context (product type, user type, tone), tailor the examples accordingly

## Quality Checklist Before Responding

Before sharing your suggestions, verify:

- [ ] Every suggestion has a clear "before" and "after" with a reason
- [ ] You've addressed the most impactful changes first
- [ ] Your suggestions match the appropriate tone for the screen's context
- [ ] You haven't introduced inconsistencies in terminology or voice
- [ ] Button labels describe actions and set expectations for the next step
- [ ] Error messages explain the problem AND how to fix it
- [ ] You've considered mobile if the screen is mobile (or could be viewed on mobile)
- [ ] You've flagged any missing copy (error states, empty states, help text)
