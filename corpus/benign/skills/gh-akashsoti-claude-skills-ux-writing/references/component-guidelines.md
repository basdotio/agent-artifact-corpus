# Component-Specific UX Writing Guidelines

This reference covers writing guidelines for every common UI component and pattern. Read this file when you need detailed guidance for a specific element type.

## Table of Contents
1. [Buttons & CTAs](#buttons--ctas)
2. [Headings & Titles](#headings--titles)
3. [Error Messages](#error-messages)
4. [Empty States](#empty-states)
5. [Form Fields & Labels](#form-fields--labels)
6. [Notifications & Toasts](#notifications--toasts)
7. [Dialogs & Modals](#dialogs--modals)
8. [Onboarding & Walkthroughs](#onboarding--walkthroughs)
9. [Navigation & Links](#navigation--links)
10. [Tooltips & Help Text](#tooltips--help-text)
11. [Loading & Progress States](#loading--progress-states)
12. [Confirmation Messages](#confirmation-messages)
13. [Permission Requests](#permission-requests)
14. [Settings & Preferences](#settings--preferences)
15. [Search](#search)

---

## Buttons & CTAs

Buttons are among the hardest pieces of copy to write well. Every word must earn its place.

### Core Principles (sourced from Deliveroo Design and Material Design)
- **Use action verbs**: CTAs inspire motion — always lead with a verb. "Save changes" not "Changes saved". "Add to cart" not "Cart".
- **Explain the next step**: The button label should set expectations for what happens after clicking. If clicking "Continue" leads to a payment screen, say "Continue to payment" instead.
- **Be consistent between button and destination**: If the button says "Go to checkout", the next screen title should be "Checkout" — not "Your bag" or "Review order".
- **Match forward/backward labels**: Use complementary verb pairs. "Go back" / "Go forward" is better than "Previous" / "Next". Both should feel like active choices.
- **Keep it short**: 1-4 words is ideal. Remove filler words ("now", "please", "your"). If a button is near a password field, "Reset" is enough — you don't need "Reset password".
- **Avoid double negatives**: Never pair "Cancel" with "Cancel subscription". Instead use "Keep subscription" / "Cancel subscription".
- **Celebrate at the end**: If a user just completed something, the final CTA can acknowledge it. "Done, let's go!" beats "Return to dashboard".

### Tone Calibration
- **Conversion contexts** (marketing, sign-up): Can be warmer and more energetic. "Let's get started" or "Try it free".
- **Task-completion contexts** (admin tools, settings): Should be functional and precise. "Save" or "Apply changes".
- **Destructive actions**: Must be plain and unambiguous. "Delete account" not "Remove" or "Clean up".

### Common Anti-Patterns
| Avoid | Why | Better |
|---|---|---|
| "Get Started" as a generic CTA | Ambiguous — could mean anything. Users often expect informational content but get funneled into sign-up flows. Research shows this misleads both new and returning users. | Use specific labels: "Create account", "See plans", "Take the quiz" |
| "Submit" | Too formal and vague. Doesn't tell the user what happens next. | "Place order", "Send message", "Save changes" |
| "Click here" | Inaccessible, non-descriptive. | Use the action itself: "Download report", "View details" |
| "Learn more" | Lazy and vague. Tells the user nothing about what they'll learn. | "See pricing details", "Read the full case study" |
| "Yes" / "No" in dialogs | Requires re-reading the question to understand. | Use verb labels: "Delete" / "Keep", "Save" / "Discard" |
| "Not now" without "No thanks" | "Not now" implies the user will be asked again. Only use it when the action is genuinely essential and will recur. Provide "No thanks" when the user should be able to fully decline. | "No thanks" for optional features, "Not now" only for deferred essential actions |

### Button Text for Standard Patterns
| Pattern | Recommended Labels |
|---|---|
| Multi-step process navigation | "Back" / "Continue", or more specific: "Back to address" / "Continue to payment" |
| Completing a process | "Done", "Finish", "Complete setup" |
| Dismissing informational content | "Got it", "OK", "Dismiss" |
| Declining an offer | "No thanks", "Skip" |
| Canceling an in-progress action | "Cancel", "Discard changes" |
| Destructive confirmation | Restate the action: "Delete project", "Remove member" |

---

## Headings & Titles

Headings are the pick-up lines of your interface. Users scan them to decide whether to engage with the content below.

### Core Principles (sourced from NNGroup)
- **Front-load keywords**: The first 2 words are the most important. Users' eyes fixate on the beginning of lines. "Payment methods" > "Manage your payment methods".
- **Use sentence case**: Capitalize only the first word and proper nouns. Sentence case is faster to read and feels less formal. "Account settings" not "Account Settings".
- **Be specific, not clever**: Headings should describe content accurately. Puns and wordplay slow down scanning and may confuse non-native speakers.
- **Use the inverted pyramid**: Put the most important information first, then add detail. This matches how people scan — they may never reach the end of your heading.
- **Passive voice is OK in headings**: "Payment received" puts the keyword first, which aids scanning, even though it's passive.

### Screen/Page Titles
- Should orient the user: "Where am I? What can I do here?"
- Should match the navigation label or link that brought the user here.
- Keep to 1-4 words when possible.

### Section Headings
- Use to create a "layer cake" scanning pattern — bold headings with body text beneath.
- Each heading should be understandable without reading the body text.
- Don't number sections unless sequence matters.

---

## Error Messages

Error messages are moments of friction. Well-written errors turn frustration into recovery.

### The Error Message Formula
Every error message needs three components:
1. **What happened** — Describe the problem in human language.
2. **Why it happened** — Give context if it helps the user understand (optional for obvious cases).
3. **How to fix it** — Provide a clear next step or action.

### Writing Rules (sourced from NNGroup, Shopify Polaris, Material Design)
- **Use human-readable language**: No error codes, technical jargon, or system-speak. "Couldn't save your changes" not "Error 500: Internal server error".
- **Be specific**: "Enter an email address" not "Invalid input". "Passwords must be at least 8 characters" not "Password too short".
- **Never blame the user**: Use passive voice to avoid accusation. "A phone number is required" not "You didn't enter a phone number". "This email is already in use" not "You already have an account".
- **Take a positive tone**: Frame requirements positively. "Use 24 characters or fewer" not "Must be less than 25 characters". "Try again" not "Action failed".
- **Don't use "invalid", "illegal", "incorrect", or "forbidden"**: These words feel judgmental. Say what's needed instead.
- **Offer a way forward**: Include a button, link, or instruction. "Couldn't load page. [Try again]" or "This file type isn't supported. Use .jpg, .png, or .gif."
- **Preserve user input**: Never clear a form field because of a validation error. Let users edit their original input.
- **Show errors near the source**: Inline errors beside the problematic field, not in a banner at the top of the page (though a summary banner is helpful for long forms in addition to inline errors).

### Error Severity and Visual Treatment
| Severity | When to Use | Visual Pattern | Example |
|---|---|---|---|
| Critical (red) | Blocks progress, needs immediate fix | Red text, red border, icon | "Enter a valid email to continue" |
| Warning (yellow/amber) | Doesn't block but could cause issues | Yellow banner or inline note | "Changing your currency will disconnect PayPal" |
| Informational | FYI, no action required | Muted text or toast | "Shipping may take longer to rural areas" |

### Timing
- Don't show errors prematurely. If a user clicks into a field and then clicks out without typing, that's exploration — not an error.
- For error-prone fields (passwords, phone numbers), real-time inline validation is helpful.
- For form submissions, validate on submit and scroll to / focus the first error.

---

## Empty States

Empty states appear when there's no content to display — a fresh account, an empty search, a cleared inbox. They're opportunities, not dead ends.

### What to Include
1. **What this area is for** — A brief explanation of the feature.
2. **Why it's empty** — Context for the current state.
3. **What to do next** — A clear action or path forward.

### Examples
- **New feature**: "You haven't added any products yet. [Add your first product]"
- **Empty search**: "No results for 'purple widget'. Try a different search term or [browse all products]."
- **Cleared state**: "All caught up! You have no new notifications."

### Avoid
- Leaving the space completely blank with no guidance.
- Using technical language like "null", "0 results", "no records found".
- Being overly playful when the user might be frustrated (e.g., a failed search).

---

## Form Fields & Labels

### Labels
- Use nouns or short noun phrases: "Email address", "Phone number", "Company name".
- Don't use colons after labels.
- Don't say "Enter your..." — just name the field.
- Refer to the user consistently: either "your" (second person) or "my" (first person), never both in the same context.

### Placeholder Text
- Use to show format examples: "e.g., name@company.com" or "MM/DD/YYYY".
- Never use placeholder as the only label — it disappears on input.
- Don't repeat the label as placeholder: if the label says "Email", don't put "Enter email" in the placeholder.

### Help Text
- Place below the field.
- Use to explain format requirements, data usage, or provide context: "We'll send a confirmation to this address" or "Use the format +1 (555) 555-5555".
- Keep to one sentence.

### Character/Word Limits
- Show the limit and remaining count: "0/280" or "23 characters remaining".
- Explain why there's a limit if it's not obvious.

---

## Notifications & Toasts

### Toasts (brief, auto-dismissing)
- Maximum 3 words for success: "Message sent", "Changes saved", "Item added".
- Include an undo action for destructive changes: "Product archived. [Undo]"
- Don't use for errors (use banners or inline errors instead).
- Don't use for anything that requires the user to read more than a glance.

### Banners/Alerts (persistent, in-page)
- Use for important information that affects the current workflow.
- Include a clear action if one is needed: "Your trial ends in 3 days. [Choose a plan]"
- Match severity to visual treatment (info/blue, success/green, warning/yellow, error/red).

### Push Notifications
- Front-load the key information: "Your order shipped" not "Great news! We wanted to let you know that your order has shipped."
- Be specific: include names, numbers, statuses.
- Respect attention: only notify for things the user cares about.

---

## Dialogs & Modals

### Title
- Should be a concise description of the decision or action: "Delete this project?" or "Unsaved changes".
- Keep to under 6 words.

### Body
- One or two sentences explaining the consequence: "This can't be undone. All project files will be permanently removed."
- Don't over-explain. Reveal detail as needed.

### Buttons
- Primary action should restate the verb from the title: Title "Delete project?" → Buttons: "Delete" / "Cancel".
- Avoid "Yes" / "No" — these require re-reading the question.
- Destructive primary buttons should use danger styling (red).

### Material Design Dialog Patterns
- Keep dialog titles short — match them to the action.
- Body text should be a single paragraph or less.
- Use present tense: "This removes all data" not "This will remove all data".

---

## Onboarding & Walkthroughs

- **Lead with benefits, not features**: "Find restaurants that deliver to you" not "We use GPS to detect your location".
- **One concept per step**: Don't overload. Each screen should teach one thing.
- **Let users skip**: Always provide a way to bypass onboarding. Use "Skip" — not "Maybe later" (which implies nagging).
- **Use progressive disclosure**: Reveal complexity as the user needs it, not all at once.
- **Show, don't tell**: If you can demonstrate with the UI itself, don't use a tooltip.

---

## Navigation & Links

### Link Text (sourced from NNGroup — the 4 Ss)
- **Specific**: Describe where the link goes. "View shipping policy" not "Click here".
- **Sincere**: Don't oversell. The destination should match the promise.
- **Substantial**: Give enough information for the user to decide whether to click.
- **Succinct**: Keep it short, but not at the cost of clarity.

### A Link Is a Promise
- If the link text says "Pricing", the destination must be a pricing page — not a contact form.
- Broken promises destroy trust and hurt credibility.

### Navigation Labels
- Use nouns that describe the destination: "Products", "Settings", "Help".
- Avoid verbs in primary navigation (verbs are for buttons).
- Keep to 1-2 words.
- Test with real users — what makes sense to your team may not make sense to your audience.

---

## Tooltips & Help Text

- Use for supplementary information that most users won't need.
- Keep to 1-2 short sentences.
- Don't put essential information in tooltips — many users will never see them.
- Don't duplicate what's already visible on screen.
- On mobile, tooltips are harder to access — consider inline help text instead.

---

## Loading & Progress States

- **Keep it brief**: "Loading…", "Saving…", "Preparing your report…"
- **Use present tense**: "Signing in…" not "Please wait while we sign you in…"
- **Set expectations for long waits**: "This may take up to 5 minutes" — but only if it actually might.
- **Describe what's happening, not the technology**: "Preparing video…" not "Buffering…"
- **Celebrate completion**: "All set!" or "Done" when the process finishes.

---

## Confirmation Messages

- **Acknowledge the action**: "Order placed", "Account created", "Message sent".
- **Provide next steps**: "You'll receive a confirmation email shortly" or "Your changes will take effect in 24 hours."
- **Include relevant details**: order numbers, dates, amounts.
- **Offer a follow-up action**: "View order details", "Return to dashboard", "Share with team".

---

## Permission Requests

- **Explain why you need access**: "Allow location access to find restaurants near you" — not just "Allow location access?"
- **Be honest about data usage**: "We'll use this to personalize your feed" — not "To improve your experience".
- **Time it right**: Ask for permissions when the user needs the feature, not on app launch.
- **Respect refusals**: If a user declines, provide a graceful fallback, not a dead end.

---

## Settings & Preferences

- **Use clear on/off language**: "Email notifications" with a toggle is clearer than "Would you like to receive email notifications?"
- **Explain consequences**: "Turning this off means you won't receive order updates by email."
- **Group related settings** with clear section headings.
- **Use the user's language**: "Dark mode" not "Interface color scheme preference".

---

## Search

### Placeholder
- Be specific about what can be searched: "Search products…" or "Search by name, email, or order number".
- Don't just say "Search…" if the scope is limited.

### No Results
- Acknowledge the search term: "No results for 'purple widget'".
- Suggest corrections: "Did you mean 'purple widget'?" or "Check your spelling."
- Offer alternatives: "Try browsing [categories] or [popular items]".
- Never leave the results page completely empty.
