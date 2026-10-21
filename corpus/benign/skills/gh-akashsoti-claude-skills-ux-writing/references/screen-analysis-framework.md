# Screen Analysis Framework

Use this framework to systematically analyze any screen (mobile or desktop) for UX writing improvements.

## Step 1: Identify the Screen Context

Before writing a single word, answer these questions:

1. **Who is the user?** First-time visitor? Power user? Someone in distress? Someone in a hurry?
2. **Where are they in their journey?** Browsing → deciding → acting → confirming → recovering?
3. **What's their emotional state?** Excited (onboarding), stressed (checkout), frustrated (error), neutral (settings)?
4. **What's the one thing they need to do or know?** Every screen has one primary job. Find it.
5. **What platform is this?** Mobile screens need shorter copy, larger tap targets, and more progressive disclosure. Desktop can afford slightly more detail.

## Step 2: Catalog Every Text Element

Walk through the screen and tag every piece of text:

| Element Type | Examples |
|---|---|
| Screen/page title | "Settings", "Your Cart", "Create Account" |
| Section headings | "Payment method", "Shipping address" |
| Body/description text | Paragraphs, feature descriptions, instructions |
| Button labels (primary) | "Continue", "Save", "Buy now" |
| Button labels (secondary) | "Cancel", "Skip", "Back" |
| Link text | "View details", "Forgot password?" |
| Form labels | "Email", "Password", "Phone number" |
| Placeholder text | "e.g., name@company.com" |
| Help text | "We'll send a verification code to this number" |
| Error messages | "Enter a valid email address" |
| Empty states | "No items in your cart" |
| Status/feedback text | "Saved", "Uploading…", "3 items selected" |
| Tooltips | "This controls who can see your profile" |
| Navigation labels | Tab names, menu items, breadcrumbs |
| Microcopy | Legal text, disclaimers, badges, tags |

## Step 3: Apply the UX Writing Audit Checklist

For each text element, evaluate against these criteria:

### Clarity
- [ ] Would a first-time user understand this without context?
- [ ] Is it free of jargon, technical terms, and internal language?
- [ ] Does it use simple, common words? ("Use" not "utilize", "Start" not "Initiate")
- [ ] Is it in the present tense? ("Message sends" not "Message will be sent")
- [ ] Does it use active voice where appropriate? (Passive is OK for headings and errors)

### Conciseness
- [ ] Can any words be removed without losing meaning?
- [ ] Is it scannable — could a user get the gist in under 2 seconds?
- [ ] Are sentences short (under 20 words)?
- [ ] Does it front-load the key information?
- [ ] Are common introductory phrases omitted? ("Save changes?" not "Would you like to save your changes?")

### Usefulness
- [ ] Does this text help the user take action or make a decision?
- [ ] Does it answer the question the user is likely asking at this moment?
- [ ] If it's an error, does it explain how to fix the problem?
- [ ] If it's a button, does it set clear expectations for what happens next?
- [ ] If it's a form label, does it make the expected input obvious?

### Consistency
- [ ] Is the same concept called the same thing everywhere? (Don't switch between "Remove", "Delete", and "Trash")
- [ ] Is the person addressed consistently? (All "you/your" or all "I/my", never mixed)
- [ ] Do forward/backward button pairs feel like matching terms?
- [ ] Does the button label match the title of the destination screen?
- [ ] Is capitalization consistent? (Sentence case everywhere, or Title Case if that's the established pattern)

### Tone
- [ ] Does the tone match the emotional context? (Empathetic for errors, celebratory for completion, neutral for routine tasks)
- [ ] Is it free from blame language? (No "you failed", "incorrect", "invalid", "illegal")
- [ ] Is it respectful and not condescending? (No "simply", "just", "obviously")
- [ ] Is it appropriately warm without being cloying? (Avoid forced friendliness in serious contexts)
- [ ] Does it avoid exclamation marks (except for genuine celebrations)?

### Accessibility
- [ ] Would a screen reader make sense reading this aloud?
- [ ] Is link text descriptive (not "click here" or "learn more")?
- [ ] Are error messages associated with their fields (not just color-coded)?
- [ ] Do images have meaningful alt text?
- [ ] Are abbreviations and acronyms explained on first use?

## Step 4: Consider the Reading Pattern

People don't read screens linearly. They scan. The layout determines what gets read first.

### F-Pattern (common for text-heavy pages)
- Users read the first line more completely.
- They scan down the left side, occasionally reading into the middle.
- **Implication**: Front-load important words in every heading and paragraph. The first 2 words are the most-read words.

### Layer-Cake Pattern (pages with clear headings)
- Users read headings and skip body text until they find the relevant section.
- **Implication**: Headings must be self-explanatory. Don't depend on body text to convey meaning.

### Spotted Pattern (scanning for keywords)
- Users scan for specific words — numbers, their name, a status.
- **Implication**: Use visual weight (bold, color, icons) to highlight the information users are scanning for.

### Mobile-Specific Considerations
- Screens are smaller; every word costs more real estate.
- Users scan even faster on mobile.
- Tap targets need enough space — long button text can create awkward wrapping.
- Progressive disclosure is more important: show less, reveal on demand.

## Step 5: Output Format

When suggesting UX writing improvements, structure your output like this:

### For Each Text Element
```
ELEMENT: [type — e.g., Primary Button, Error Message, Page Title]
CURRENT: "[the existing text]"
SUGGESTED: "[your improved text]"
REASON: [one sentence explaining the change, referencing a specific principle]
```

### For Overall Screen Feedback
Provide a brief summary covering:
1. **Biggest wins** — The 2-3 changes that would have the most impact.
2. **Tone assessment** — Is the overall tone right for this context?
3. **Consistency issues** — Any mismatches in terminology, voice, or capitalization.
4. **Missing elements** — Text that should exist but doesn't (help text, empty states, error states).
5. **Mobile/responsive notes** — If the screen is mobile, any text that may be too long or need rewriting for the smaller viewport.

## Tone Mapping by Screen Type

| Screen Type | Tone | Priority |
|---|---|---|
| Onboarding / Welcome | Warm, inviting, benefit-focused | Show value, don't overwhelm |
| Sign-up / Login | Neutral, efficient, reassuring | Speed, clarity, trust |
| Dashboard / Home | Informative, concise, actionable | Orientation, key metrics |
| Settings / Preferences | Neutral, descriptive, precise | Explain consequences |
| Checkout / Payment | Reassuring, trustworthy, minimal | Reduce anxiety, build confidence |
| Error / Failure | Empathetic, constructive, calm | Explain + guide recovery |
| Success / Confirmation | Positive, celebratory (mildly), next-step-focused | Acknowledge + guide forward |
| Empty State | Helpful, encouraging, action-oriented | Explain + invite action |
| Search Results | Informative, assistive | Show relevance, offer alternatives |
| Form-heavy screens | Clear, directive, supportive | Minimize friction, prevent errors |
| Legal / Policy | Plain, honest, structured | Comprehension over compliance |
| Marketing / Landing | Persuasive, benefit-led, concise | Convert with clarity |

## Common Copy Smells (Red Flags to Look For)

These patterns almost always signal a writing problem:

1. **"Please"** — In UI, it often adds noise. "Enter your email" is more direct than "Please enter your email". Reserve "please" for moments of genuine inconvenience to the user.
2. **"Successfully"** — "Profile updated" says the same thing as "Profile updated successfully" in fewer words.
3. **"In order to"** — Just say "to".
4. **"Are you sure?"** — Add context instead: "Delete this draft? This can't be undone."
5. **Exclamation marks everywhere** — Reserve for actual celebrations. Multiple exclamations feel desperate.
6. **ALL CAPS for emphasis** — Use bold or placement instead. Caps feel like shouting.
7. **"Oops!" in error messages** — Minimizes the user's frustration and feels performative.
8. **Walls of text** — If a paragraph is more than 3 sentences, it needs restructuring.
9. **"Click here"** — Always describe the destination, not the mechanical action.
10. **Mixing metaphors** — Don't "save to your cart" on one screen and "add to basket" on another.
