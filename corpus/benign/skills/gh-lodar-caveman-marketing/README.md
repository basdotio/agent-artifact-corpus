<div align="center">

<img src="assets/caveman-icon.svg" alt="Caveman marketing" width="120">

# Caveman marketing

![license](https://img.shields.io/badge/license-MIT-blue)

</div>

<p align="center"><img src="assets/hero.png" alt="explain it to cavemen" width="360"></p>

**Your AI agent cuts any ad, landing page or signup to one picture, 15 words and one button.**

```bash
npx skills add lodar/caveman-marketing
```

Then tell your agent: **caveman my website**

## Use it for

Website redesigns. Ad ideas. Landing pages. Signups.

Anything people glance at for 3 seconds, then leave.

## Tested on famous homepages

Three fresh agents each got only this skill and one real homepage, on a phone, on 2026-10-20.
The real screenshot is on the left and the skill's version is on the right.

<p align="center"><img src="assets/apple.png" alt="apple.com before and after" width="480"></p>

<p align="center"><img src="assets/hubspot.png" alt="hubspot.com before and after" width="480"></p>

<p align="center"><img src="assets/atlassian.png" alt="atlassian.com before and after" width="480"></p>

## On desktop too

The same rules on a 1440×900 screen. The picture takes the left half, and the words and the one button
sit on the right.

<p align="center"><img src="assets/hubspot-desktop.png" alt="hubspot.com on desktop, before and after" width="480"></p>

## The test

Look for 3 seconds, then cover the screen. Can you answer all three?

1. What is this?
2. Do I want it?
3. Where do I tap?

## The rules

1. A picture fills the top half.
2. 15 words max. Every word counts, buttons too.
3. One filled button, with 👇 above it. Nothing in the picture looks like a second one.
4. The button says what happens next.
5. A step bar on every step of a signup.
6. No words only your industry uses.
7. The signup ends when they get the thing.

`scripts/check.py` counts the words and buttons on each screen, because models miscount.
How the skill runs is in [SKILL.md](SKILL.md), and every example is in [examples/](examples/).

## Why it works

**One screen. One clear action. Minimum decisions before the user gets value.**

- **Hick's law** (Hick 1952, Hyman 1953). The time it takes to choose grows with the number of
  choices, roughly with log₂(n + 1). Every extra button slows the decision down.
- **Choice overload, the paradox of choice** (Iyengar & Lepper 2000, Schwartz 2004). With 6 jams
  on the table, 30% of the shoppers who stopped bought one. With 24, 3% did. It hits hardest when options are hard
  to compare and people don't know yet what they want (Chernev et al. 2015), which describes a
  stranger on your landing page.
- **Progressive disclosure.** Show only what this step needs, and reveal the rest later. That's
  why a signup asks one thing per screen.

<sub>The right-hand screens are mocks, not the companies' pages. Each keeps the company's own
claims. Apple's picture is Apple's own photo; HubSpot's and Atlassian's are drawings. Not
affiliated with any company shown.</sub>

Made with [5dive](https://5dive.ai)'s AI agents.
