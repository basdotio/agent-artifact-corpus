# Example: cross-industry-steal

> Real output from Claude Code (Claude Opus 5.5), run on 2026-09-23 with v1.0.0 of this skill installed. The output is unedited, except for a closing offer to do more work, which was removed. The scenario is fictional.
> The prompt doesn't name the skill: Claude recognized the situation and used it on its own.
> Since then (v1.3.0), the skill also reads `PRODUCT.md` and the feature's brief first when they exist, and ends with a "Next" line, so a run today ends differently. Since v1.4.0, it also doesn't raise again what the brief records as rejected, doesn't repeat what earlier skills found, and offers once to start a brief when there's none. Since v1.5.0, it also starts with a "Context used:" line, reads the docs that the Sources table in `PRODUCT.md` points to, and writes disagreements between sources under the brief's `## Open`.

## Prompt

```text
I'm stuck on a problem: in our expense-reporting app, employees collect receipts all month and then submit everything at once at the end of the month, which is painful and error-prone (lost receipts, wrong categories). I'd like fresh inspiration from outside our category.
```

## Output

The underlying problem is that each expense gets recorded weeks after it happened. By month-end the receipt is gone and the reason for the expense is forgotten, so people guess. Here are three fields that ran into the same problem.

---

**1. Physical product / offline service**
**Domain:** Hospitality · **Example:** Hotel room folio ("charge it to my room")
**How it works:** When a guest buys something at the bar, spa or restaurant, the merchant posts the charge to the room account right away. At checkout the guest just checks a bill that's already itemized. Nobody asks them to remember what they spent all week.
**Digital translation:** Start from the card transaction feed, not from the employee. Each corporate card charge creates a draft expense automatically, with merchant, amount and date filled in. The employee's month-end job becomes "review and confirm" instead of "rebuild the month from memory."

**2. Non-tech industry**
**Domain:** Healthcare · **Example:** Bedside documentation plus "charting by exception"
**How it works:** Nurses who save their charting for the end of a shift make more errors and miss details, so hospitals moved documentation to the bedside, at the moment of care. Charting by exception goes further: normal findings are assumed by default, and nurses only write down what's different.
**Digital translation:** Pre-fill the category from the merchant type and the employee's history (for example, Uber becomes Travel/Ground). Only ask the employee about exceptions: missing receipts, charges over policy limits, merchants that could fit two categories, or charges with no match. Everything routine goes through without a human touching it.

**3. Nature / biology / psychology**
**Domain:** Behavioral research · **Example:** Ecological Momentary Assessment (EMA), also called experience sampling
**How it works:** Psychologists found that asking people to recall things later (like "how was your mood last week?") gives biased, unreliable data. So EMA pings participants on their phone at the moment something happens and asks one or two quick questions, while the memory is still fresh.
**Digital translation:** When a card is swiped, send a push notification within minutes: "₫1.2M at Pizza 4P's. Snap the receipt? Looks like *Client meal*. Who was there?" It should take about 5 seconds, in the moment the receipt is still in the employee's hand.

---

## Best steal: EMA-style capture at the moment of purchase, with charting by exception at month-end

EMA gets at the actual cause. Receipts get lost and categories go wrong because capture happens weeks after the purchase, not because the form is hard to fill in. Here's how it would work:

1. **Trigger:** A card transaction webhook fires, and the app sends a push notification within about 2 minutes, while the employee still has the receipt.
2. **Micro-prompt:** One screen with the merchant, the amount and a **pre-selected category guess**. The employee has three actions: 📷 snap receipt, ✓ confirm category, or tap to change it. An optional one-line field ("Who / why?") appears only for categories that need a business purpose, like meals and entertainment.
3. **Snooze, don't nag:** If the employee ignores the notification, it's re-sent once that evening ("3 expenses from today still need receipts"). After that, it goes into a queue. Limit it to one follow-up per day, because EMA research shows that too many prompts make people stop responding.
4. **Month-end becomes exception review:** The submit screen shows "42 expenses ready ✓ · 3 need attention." The employee only looks at the 3: a missing receipt, a charge over the policy limit, or a category the app wasn't sure about. Submitting takes a minute instead of an afternoon.
5. **Metric to watch:** Median time from transaction to receipt capture. If it drops from about 20 days to under an hour, lost receipts and wrong categories should fall with it.

**Constraint:** This works best with corporate cards, where you get the transaction feed. For out-of-pocket spending on personal cards there's no swipe event, so you'd need weaker triggers, such as a daily "anything to log today?" nudge on travel days taken from the calendar. Location-based triggers would work too, but they raise real privacy concerns and should be opt-in only.
