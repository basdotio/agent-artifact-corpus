---
name: caveman-marketing
description: >-
  Cut an ad, landing page, signup flow or any single screen down until a
  stranger gets it in 3 seconds: one picture, at most 15 words, one button.
  Use when a page, ad or funnel is wordy, unclear, gets views but no clicks,
  or has no obvious next click, for website redesign, landing page or ad ideas,
  and whenever someone asks to "caveman" something. Not for long persuasive
  copy written from scratch.
---

# Caveman marketing

People don't read. They glance for 3 seconds, then they leave.
So explain it to a caveman.

```
 BEFORE                            AFTER
┌───────────────────────────┐     ┌───────────────────────────┐
│ Products... [Get Started] │     │ ☰                         │
│ AI without workflows is   │     │ ┌───────────────────────┐ │
│ just expensive advice     │     │ │ ticket: New laptop    │ │
│ Most companies have AI    │     │ │ Open  →  Done ✓       │ │
│ but few have the data to  │     │ └───────────────────────┘ │
│ ground it, the workflows  │     │ AI that does the work.    │
│ to deploy it, and the ... │     │            ↓              │
│ Explore Control Tower  →  │     │ ┌───────────────────────┐ │
│ Request Demo  →           │     │ │      See it work      │ │
└───────────────────────────┘     │ └───────────────────────┘ │
  62 words · 11 ways out          └───────────────────────────┘
                                    14 words · 1 button
```

## The caveman test

Look at the screen for 3 seconds. Cover it. A caveman must grunt three answers:

1. **What this?**
2. **Me want?** What do I get?
3. **Where tap?**

One grunt missing means the screen fails. StoryBrand calls a version of this the
grunt test. This skill adds hard numbers and covers ads and funnels too.

## The 7 rules

1. **Picture first.** A picture fills the top half and does the explaining. Show the
   result happening (the ticket closing, the site fixed), not your dashboard. Words only
   label the picture.
2. **15 words, max. 6 in the headline.** Count every word on the screen: headline, button,
   a field's placeholder, small links, the step bar, text inside the picture. Don't count
   emoji, logos or the platform's own fixed text (browser bar, "Sponsored", a card form's own
   field names).
   The headline is one sentence that says what the site is and what it sells you, in words a
   stranger can picture: "A ring that tracks your sleep." Not a slogan, not "a clearer X", not
   two of the page's taglines stitched together. Swap in another company's name: if the line
   still fits, it says nothing ("All in one place."). Name the concrete thing instead
   ("Meeting notes written for you."). Run the checker. Models and humans both miscount.
3. **One button.** Exactly one filled button, the biggest and brightest thing on the
   screen, with 👇 right above it. Everything else is small grey text. Three equal
   choices is a menu. The cookie banner never outshines it.
   Nothing in the picture may look tappable either: a filled pill or chip with words on it
   reads as a second button. Use a stamp, a tick or plain text instead.
   When the one action is typing (a search, an email, a web address), keep ONE field right
   above the button: the field and its button are the one action, and the field's
   placeholder words count.
4. **The button says what happens next, and the next screen keeps the promise.**
   "Get started" that opens a 15-question sales form breaks it. "Pick a time" that
   opens a calendar keeps it.
5. **Show the trail.** Every step of a flow shows a step bar (`① Email › ② Time`), with
   the current step lit. Three steps or fewer before the first win.
6. **No tribe words, no hype.** Words only your industry says: platform, solution, workflow,
   seamless, leverage, end-to-end, interoperability. Spell out an acronym unless the
   buyer says it every day. If a 10-year-old would ask "what's that?", cut it.
   Hype goes on sight: trusted, world's best, world-class, leading, #1, best-in-class,
   powerful, revolutionary, next-gen, cutting-edge, innovative, all-in-one, ultimate.
   Cutting it removes no fact, so "keep the real claims" never keeps it. "The world's best
   commerce platform" becomes what it is: "Sell online with your own store."
7. **The hunt ends with meat.** A funnel ends on the moment the customer gets the thing:
   the job done, the call booked, the first result. Ask one thing per screen, and only
   what you need to get them there. The rest can wait until after they're in.

The caveman grunts are only the test. The new copy is plain, normal English.

## Why it works

If someone asks why one button and 15 words, the answer is that every extra choice costs time
and conversions:

- **Hick's law:** decision time grows with the number of choices, roughly log₂(n + 1).
- **Choice overload** (Iyengar & Lepper 2000; Chernev et al. 2015): too many options make people
  choose nothing. It's strongest when they can't compare the options and don't know yet what they want.
- **Progressive disclosure:** show what this step needs, and reveal the rest later.

One screen. One clear action. Minimum decisions before the user gets value.

## How to run it

Input: a URL, a screenshot or pasted copy of an ad, a page, or each step of a flow.

1. **Grunt the BEFORE.** Write the three answers it gives, `?` for each one missing.
2. **Count the BEFORE.** Words on the first screen, filled buttons, every other way out
   (links, menus, second buttons), steps to the first win. These numbers lead your report.
3. **Name the one job.** One sentence: who it's for and what they get. If you can't
   write it, the offer is the problem, not the copy. Say so and stop.
4. **Rewrite each screen** in the screen format below: picture, then a headline of at most
   6 words, then one button, at most 15 words in all. Keep the real claims and invent none. Caveman cuts words, not truth.
5. **Check it.** `python3 scripts/check.py after.txt` until every screen passes. Warnings
   are judgment calls. Failures are not.
6. **Show BEFORE above AFTER**, same size, counts under each. If you can render images,
   render both. If not, the `picture:` line is the brief for whoever draws it.
7. **Grunt the AFTER.** All three answers, in 3 seconds, or go back to step 4. Then swap
   a competitor's name into the headline. If it still fits, it says nothing: back to step 4.

## Screen format

```
# landing / top
picture: a chat bubble "Fix my site" and a reply "Done ✓"
Say it and it's done.
👇
[Hire your team]
(Log in)
---
# a search page
picture: the logo, big
Search the web with Google.
{Search Google}
👇
[Google Search]
```

- `[...]` is the one filled button. `(...)` is small grey text or a link.
- `{...}` is one text field, its placeholder inside. Only when typing is the one action, and
  right above the button (a 👇 between them is fine).
- `picture:` describes the picture. Only its words "in quotes" count, because they show
  on screen.
- Every other line counts, and the first one with words is the headline. `#` names a screen.
  `---` starts the next one.

`scripts/check.py` reads this format, prints PASS or FAIL per screen with the reason,
and exits non-zero if any screen fails. `scripts/test.sh` checks the checker.

## Per surface

- **Ad.** One screen. The first line of the post text is all most people see, so it
  carries the grunt. Ad platforms make you pick the button label from a list: choose the
  one that names what happens (Download for a report, Sign up for a trial). Never paint a
  second button with other words into the image.
- **Landing page.** The screen is the first view on a phone (390×844). The menu becomes
  one icon. Each screen further down follows the same rules and repeats the same button.
  On desktop the picture fills the left half, and the words, 👇 and button sit in the right
  half. Same copy, same 15-word cap.
- **Funnel.** Every step is a screen, from the ad to the first win. Sign-in is one button
  ("Continue with Google") with email as a small link. A legal line the lawyers need is
  one short grey line, and it counts.

## Report

```
BEFORE  62 words · 11 ways out · grunts: what ? · want ? · tap ?
AFTER   14 words · 1 button   · grunts: what ✓ · want ✓ · tap ✓
```

Then each screen, BEFORE above AFTER, and one line per rule the BEFORE broke.

## Examples

`references/examples.md` walks through a LinkedIn ad, a homepage, a signup funnel and a
search page, all real pages from big companies, each with its BEFORE and AFTER in
`examples/`, plus a test run on the apple.com, hubspot.com and atlassian.com homepages
(rendered in `README.md`).
