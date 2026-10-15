# Design contract - {product}

> Save this file in the project (for example `docs/design-contract.md`) so every future AI or human session builds on the same decisions. Keep it in the project: never copy it into an assistant's global instructions or memory. Change it only through an approved decision; record the date. Each decision has an ID that pages and reviews can cite.

**Version** {n} · **Approved by** {owner} · **Date** {date} · **Theme source** `{path}`

## Product

| ID | Decision | Value |
| --- | --- | --- |
| DC-01 | Audience and main tasks | {who, doing what, with which hesitation} |
| DC-02 | Brand traits (3) / anti-traits (3) | {e.g. calm, exact, trustworthy / loud, gimmicky, vague} |
| DC-03 | Product branches | {physical / digital / configurable / subscription} |
| DC-04 | Real data sources | {price, stock, delivery, reviews, metrics: where each comes from; what is missing} |
| DC-05 | Locales, currencies, direction | {list; longest locale for layout tests} |
| DC-06 | Themes and modes | {light, dark, system; how the switch is stored} |
| DC-07 | Density | {customer pages vs admin} |

## Visual system

| ID | Decision | Value |
| --- | --- | --- |
| DC-10 | Layout | container {px}, reading width {ch}, gutter {role}, grid {columns} |
| DC-11 | Breakpoints | where content stops fitting: {values and why} |
| DC-12 | Type roles | display / h1 / h2 / h3 / body / small / label: family, size, line height, weight |
| DC-13 | Colour roles | canvas, surface, text, subtle, brand, on-brand, border, focus, status - see theme source |
| DC-14 | Contrast pairs | `contrast-pairs.json` - all themes pass: {date} |
| DC-15 | Spacing scale and roles | scale {values}; control / card / stack / section / page |
| DC-16 | Shape and depth | radius roles, shadow roles, where borders are used |
| DC-17 | Layers | base < raised < sticky < dropdown < drawer < modal < toast < tooltip |
| DC-18 | Icons | set {name}, stroke {w}, size grid {px}, fill rules, rights |
| DC-19 | Imagery | ratios, crop-safe area, lighting/treatment, fallback, rights |
| DC-20 | Content tone | voice; buttons = verb + object; sentence case; errors = what happened + how to fix; empty states = what appears + first step; number, date and currency formats; glossary of recurring terms |

## Interaction

| ID | Decision | Value |
| --- | --- | --- |
| DC-30 | Motion roles | instant {ms}, quick {ms}, panel {ms}, story {ms}; easing |
| DC-31 | Motion policy | floor: brief feedback on every change the user causes; ceiling: nothing moves on its own except real progress and at most one attention moment per view; one-shot over loops; reduced motion = final state |
| DC-32 | List controls | filter / sort / view / columns live in one toolbar on lists that need them |
| DC-33 | Optional notices | X closes; menu: Minimize (in-place `!` box), Remind me in a week, Never show again; stored {where} |
| DC-34 | Same-page actions | save / filter / add to cart update without full reload where the existing data flow supports it |
| DC-35 | Feedback | pending, success, error and empty patterns; toast position, look, maximum shown and timing |
| DC-36 | Info (i) help | only where purpose or effect cannot be inferred and a wrong guess costs; text = purpose or effect in at most two sentences; at most one per card; component {project popover / `info-toggletip.html`} |
| DC-37 | Controls | control heights {32 / 40 / 48 px}, one radius and text size per row; button variants and their states |
| DC-38 | Overlays | page locked and inert under modals; opaque layers; dialog sizes {400 / 560 / 720 px}; close button {36-40 px}; backdrop-click rule |

## Components and variants

| Component | Variants allowed | States specified | Notes |
| --- | --- | --- | --- |
| Button | primary, secondary, ghost, destructive | default, hover, focus, pressed, pending, disabled + reason | one primary per task block |
| Card | {roles used} | loading, empty, long text, missing image | |

## Scope and exceptions

- Approved change scope: {pages / components} - {date}
- Page exceptions: {route: what differs and why}
- Out of scope without separate approval: backend, database, API, payments, permissions, business rules
