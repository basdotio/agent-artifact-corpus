# Help and UI text

Read when you add help (an info (i) or a visible hint), write labels, buttons, errors, empty states or confirmations, or build a form.

## Contents

1. Help: when to add it, in which form, and when not to
2. What the help says
3. Help by element type
4. The help component
5. Other UI text
6. Forms
7. Numbers, dates and units
8. Review checklist

## 1. Help: when to add it

Help comes in two forms: an info (i) that opens on demand, and a visible hint under a field. Either one tells the user "this one is worth explaining". If every card or field carries help, users stop reading it, the page looks unsure of itself, and the few that matter get lost. Help is rare on purpose, in both forms.

**Add help only when all three are true:**

1. The page's intended user could not work out the item's purpose or effect from its label, its value and what surrounds it.
2. A wrong guess costs something: money, data, a change customers will see, time, or a failed task.
3. A clearer label cannot solve it. Fix the label first.

**Pick the form:**

| What the user needs to know | Form |
| --- | --- |
| A limit or format needed while typing ("Minimum 90 days", "8+ characters") | visible hint under the field |
| A serious or hard-to-undo consequence: people locked out, data archived or deleted, integrations broken, money charged | visible hint; when an action triggers it, a confirmation that states the consequence |
| Nice-to-know detail: where a name appears, when an email is sent, how a figure is counted | info (i) |
| Nothing the label does not already say | no help |

**Never add help:**

- to self-explanatory items: name, email, price, quantity, search, save, cancel;
- to decorative or marketing cards, or to every card "for consistency";
- to hold what the user must see: prices, fees, errors, legal or consent text, required steps, deadlines. Show those on the page;
- to a disabled control to explain why it is disabled. Say why next to it, or keep it enabled and explain what is missing when it is used;
- to explain a confusing design. Fix the design;
- inside another interactive element (a link card, a button, a `<label>`). Nested controls break keyboard, touch and screen readers.

**Density.** It covers hints and (i)s together. If more than about a third of the items in a group seem to need help, check each item against the table above, rewrite the labels, or add one short intro line under the group heading instead. A card gets at most one (i), and most cards and fields get no help at all.

## 2. What the help says

Write what the item does for the user in this place, not what the word means.

| Weak: restates or defines | Useful: purpose, effect, consequence |
| --- | --- |
| "Returns rate: the rate of returns." | "Share of units sent back within 30 days of delivery. Above 8% usually points to a sizing or description problem." |
| "Tax-inclusive prices: prices include tax." | "When on, the prices you enter already contain VAT and customers pay exactly that. When off, VAT is added at checkout." |
| "Payouts: a list of payouts." | "Money the payment provider has sent or will send to your bank, one row per transfer. Use it to match your bank statement." |

- **Lead with the purpose or effect:** "Shows…", "When on…", "Counts…", "Sends…". Never repeat the label as the first words.
- **One or two short sentences, about 30 words at most.** Needing more means a "Learn more" link to a help page, or a redesign.
- **Be concrete:** the unit, the period, who is affected (customers or staff), when it takes effect, and whether it can be undone.
- **Only true statements.** Take behaviour from the code, the project's docs or the owner. When you cannot confirm what something does, do not guess. Leave a visible `TODO(owner): …` in the draft, or no help at all, and ask.
- **Plain words.** Use the user's words, not internal names. No marketing tone, sentence case, no idioms (help gets translated). One term per concept across the product.

## 3. Help by element type

| Element | The help answers | Example |
| --- | --- | --- |
| Page or section | What the page is for and the main job done here; where the data comes from if it is not obvious | "Payouts from your payment provider. Match them against your bank statement." |
| Button or action | What happens, what it affects, whether it can be undone, how long it takes | "Emails the invoice PDF to the customer again. The order does not change." |
| Toggle, switch, checkbox | The effect when on (and when off, if it is not the plain opposite); who notices; when it applies | "When on, customers can pay later by bank transfer. Orders wait unpaid for up to 7 days." |
| Input or threshold | What the value controls, its unit and range, an example | "Signs staff out after this many minutes without activity. Shorter is safer on shared computers." |
| Table column, KPI or metric | What is counted, the period, the source or formula, what is included or excluded, how to read it | "Net revenue per week after refunds and discounts, excluding tax." |
| Status or badge | What the status means now, and what happens next or what the user can do | "Submitted, not yet checked by a moderator. It goes live after approval." |
| Plan, feature or pricing line | The concrete benefit or limit in user terms | "Email replies within one business day." |
| Chart | What is plotted, the period, the unit, known caveats | "Orders per day in your store's time zone. Today is incomplete." |

## 4. The help component

Use the project's own popover primitive if it has one (for example a Radix or shadcn/ui Popover, a Bootstrap popover or an MUI Popover). Otherwise copy `assets/templates/info-toggletip.html`. Either way the behaviour is the same:

- A real `<button type="button">` placed right after the label, heading or column name. Its accessible name is "About {label}". The icon itself is decorative.
- It opens on click, tap, Enter and Space, and closes on Escape, an outside click or a second press. Focus stays on the button.
- Hover alone never opens it, and the `title` attribute is never the help: neither works on touch, and `title` is unreliable for keyboard users.
- One panel is open at a time. The panel sits next to its button, stays inside the viewport and is readable in every theme. It uses at most a quick fade.
- The panel is plain text, with at most one "Learn more" link. Anything with fields or actions is a dialog, not help.
- In the DOM, the panel comes right after its button, so screen readers reach it next.
- **Placement:**
  - after a `<label>` element, never inside it: a button inside a label is invalid and toggles the field;
  - after a heading, not inside it, so the heading's name stays clean;
  - after a column's sort button, never inside it.
- Every (i) looks the same: same icon, size and position. The target is at least 24×24 px, with a larger hit area on touch screens.

**Tooltip vs toggletip.** A hover/focus tooltip only names an icon-only button ("Edit", "Duplicate"). An explanation is always a toggletip.

**(i) vs the optional information card.**

- The (i) explains one item when asked.
- The optional card (X, Minimize to `!`, Remind me in a week, Never show again) volunteers one non-critical note about the page.

Critical information never lives only in either of them.

## 5. Other UI text

- **Buttons:** verb + object ("Save changes", "Download invoice", "Add to cart"), never "OK", "Submit" or "Yes". The same action has the same label everywhere.
- **Labels:** short, sentence case, always visible. A placeholder is never the label.
- **Helper text:** sits under the field and holds the format or limits needed while typing ("At least 8 characters").
- **Errors:**
  - say what happened and how to fix it, next to the field, in plain words ("The card number is 2 digits short");
  - no blame, and no bare error codes;
  - keep what the user typed.
- **Empty states:** say what will appear here and the first step ("No invoices yet. They appear here after your first sale."). Keep three cases apart:
  - nothing yet;
  - nothing matches these filters (offer "Clear filters");
  - could not load (offer "Try again").
- **Confirmations:**
  - only for destructive, irreversible or costly actions;
  - the title names the action and the object ("Delete 3 products?");
  - the body states the consequence;
  - the confirm button repeats the verb ("Delete products"), and Cancel is the safe default.
  - Prefer real undo over a confirmation when the system supports it.
- **Pending and success:**
  - "Saving…" while it runs, "Changes saved" when it is confirmed;
  - never show success before the real confirmation, and do not celebrate routine actions.
- **Consistent terms:** keep one word per concept (cart or basket, not both). When terms repeat, keep a short glossary in the design contract.
- **Page titles and icons:**
  - every route has its own `<title>`, such as "Order history · Brand";
  - never leave a framework default such as "Vite + React" or "Create Next App";
  - replace the framework's favicon with the brand's own.

## 6. Forms

- **Layout:** one column. Labels above fields. Related fields are grouped under a short heading.
- **Required vs optional:** when most fields are required, mark the optional ones "(optional)" instead of starring the required ones.
- **Input attributes:** set the correct `type`, `inputmode` and `autocomplete`, so phones show the right keyboard and browsers can autofill.
- **Field width:** matches the expected length (postcode vs street).
- **Validation:**
  - validate when the user leaves a field or submits, not on every keystroke;
  - clear an error as soon as it is fixed.
- **Submitting with errors:**
  - move focus to the first invalid field, or to an error summary with links for long forms;
  - keep every value the user entered.
- **Submit button:** disable it only while submitting, with a pending label. Do not keep it disabled until the form is valid; show what is missing instead.

## 7. Numbers, dates and units

- **Locale formatting:** format with the user's locale through `Intl.NumberFormat`, `Intl.DateTimeFormat` or the framework's i18n, including currency, separators and decimals.
- **Numbers in tables:**
  - right-align them and use tabular figures (`font-variant-numeric: tabular-nums`, the theme's numeric role);
  - put the unit in the column header;
  - keep the same decimals within a column.
- **Dates:**
  - use absolute dates for records (orders, invoices);
  - use relative time ("2 hours ago") only for recent activity, with the exact time in `<time datetime>` and on focus/hover;
  - show the time zone wherever the time matters.
- **Missing and small values:**
  - missing is not zero: show "—" plus the reason;
  - do not round away meaning (0.4% is not 0%).
- **Truncation:**
  - truncated text keeps its full value in the accessible name, and shows it on focus and hover;
  - never truncate prices, status or IDs the user must copy.

## 8. Review checklist

- Help (a hint or an (i)) on self-explanatory items, on every card or field, more than one per card, or on more than about a third of a group's items
- A visible hint that carries nice-to-know detail instead of a limit or a serious consequence
- Help that restates the label or defines the word, is longer than two sentences, or states behaviour nobody confirmed
- Help that opens only on hover, lives in `title`, cannot be reached by keyboard or touch, or sits inside a label, link or button
- Essential information (price, fees, errors, legal terms) available only inside help
- Vague button labels, placeholder-as-label, errors without a fix, empty states without a next step, two words for one concept
- Framework-default page titles or favicons, or the same title on every route
