# Examples: four real screens, before and after

Big companies with good products. They're here because even they lose the 3-second
glance. Snapshots from 2026-10-20; the live pages may have changed since. Every
BEFORE is copied word for word into `examples/`, and every count comes from
`scripts/check.py`.

---

## 1. Ad: Workday on LinkedIn

[LinkedIn Ad Library, ad 1584209083](https://www.linkedin.com/ad-library/detail/1584209083)

**BEFORE** · 54 words · two buttons that say different things ("Read Now" drawn on the
image, "Learn more" under it), neither filled · grunts: what ✓ (a report) · want ? · tap ?

> Workday was named a Market Shaper in the Gartner report on AI agents for HR as of
> September 2026. Explore how enterprise controls, interoperability, and HR context are
> shaping this emerging market.

**AFTER** · 12 words · 1 button

```
Choosing AI for HR? 👇
picture: the same laughing team, with the report cover held up in front, "Gartner" on it
Gartner's report on AI for HR
[Download]
```

What changed:
- The first line asks the reader's question. The award moved onto the report cover.
- One button, and it names what you get. LinkedIn's list has Download, so use it.
- "Interoperability" and "enterprise controls" are for page 4 of the report.

---

## 2. Landing page: the ServiceNow homepage

[servicenow.com](https://www.servicenow.com/), first view at 1280×800

**BEFORE** · 62 words · 11 ways out, and the only filled button is the small "Get Started"
in the menu bar · grunts: what ? · want ? · tap ?

> **AI without workflows is just expensive advice**
> Most companies have AI but few have the data to ground it, the workflows to deploy it,
> and the security to govern it. Super Intelligence Control Tower is built for all of it.
> So AI doesn't just think, it acts.

**AFTER** · 14 words · 1 button

```
☰
picture: a help-desk ticket "New laptop" flipping from Open to "Done ✓", closed by the AI
AI that does the work.
👇
[See it work]
(Talk to sales)
```

What changed:
- Their own last line ("it acts") became the headline, and the picture shows it acting.
- Six menu words became one icon. Four links became one button and one grey line.
- The button opens their existing demo page, so the promise holds.

---

## 3. Funnel: what ServiceNow's "Get Started" opens

[servicenow.com/contact-us](https://www.servicenow.com/contact-us.html)

**BEFORE** · 162 words · 13 questions and 2 checkboxes on one screen · the button you
tapped said "Get Started", and this page says "Talk with a sales expert" and ends in
"Contact Sales" · grunts: what ✓ · want ? · tap ✓ (after 15 answers)

**AFTER** · 2 steps · 1 question · 12, 8 and 10 words

```
# step 1: email
① Email › ② Time
picture: a calendar with one time circled
Talk to an expert.
{Your work email}
👇
[Pick a time]
---
# step 2: time
① Email › ② Time
picture: this week's calendar, open times in green
Pick a time.
👇
[Book Tue 10:00]
---
# done: the first win
picture: a calendar invite "Call with ServiceNow, Tue 10:00" with a green ✓
You're booked.
(Add to calendar)
```

What changed:
- The new homepage's grey "Talk to sales" opens this, and the page says the same thing.
- One question. Job level, department and the rest get asked on the call.
- The funnel ends on a booked call, the thing the visitor came for, instead of a form
  that was sent.

---

## 4. Search page: google.com

[google.com](https://www.google.com/), first view on a phone (390×844), seen from Germany

**BEFORE** · 31 words · the search box sits under the logo with nothing to press, and the
only filled button is "Sign in" at the top · a list of trending searches fills the rest ·
grunts: what ✓ · want ? · tap ? (the box or Sign in?)

**AFTER** · 9 words · 1 field and 1 button

```
☰
picture: the Google logo, big
Search the web with Google.
{Search Google}
👇
[Google Search]
```

What changed:
- Typing is the one action, so the box stays, right above its button. A "Google Search"
  button with nothing to type into would be a button that does nothing.
- The headline says what the site is and what you get from it.
- Sign in and the trending list are for after the first search.

---

## Test run: three famous homepages

Three fresh agents each got only this skill and one real homepage on a phone (390×844,
2026-10-20), and wrote the screen files themselves. The rendered pairs are on the skill
page, `README.md`.

| Page | BEFORE | AFTER | Files |
| --- | --- | --- | --- |
| apple.com | 18 words · 2 filled buttons · "Hello, hello." says nothing | 10 words · 1 button | `examples/apple-home.*` |
| hubspot.com | 44 words · 2 filled buttons · "agentic", "platform" | 15 words · 1 button | `examples/hubspot-home.*` |
| atlassian.com | 32 words · an event banner where the picture goes | 12 words · 1 button | `examples/atlassian-home.*` |
| hubspot.com, desktop 1440×900 | 76 words · 2 filled buttons · "agentic", "platform", "solutions" | 15 words · 1 button (same copy, picture left) | `examples/hubspot-desk.*` |

Apple's AFTER line "The first iPhone that folds" comes from Apple's own iPhone Duo page
("the first foldable iPhone"). tesla.com was in the plan but blocks automated browsers.
