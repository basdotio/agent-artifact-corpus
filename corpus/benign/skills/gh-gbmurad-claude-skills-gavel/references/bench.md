# Gavel: the bench of jurors

The judge seats 3 to 8 of these per case, or invents a seat the case needs. Pick for the criteria, not for
variety: every seat must have a question no other seat covers. All jurors run on the same model, so a seat adds
a lens, not an independent mind. Fewer, sharper seats beat a full box of overlapping ones.

| Seat | The question it owns |
|---|---|
| premortem (always) | It is a year from now and this failed. What were the three most likely reasons? |
| engineer | Can this be built and run as described? What breaks first, at what scale? |
| designer | Will the people it is for understand it and use it without help? |
| finance | What does it cost in total, what does it return, and when does it pay back? |
| customer | Would I, the person this is for, pay for it or change what I do for it? |
| operations | Who runs this every day, and what does it add to their load? |
| security and privacy | What could leak, be abused, or put someone at risk? |
| legal and compliance | Which rule, contract or policy does this touch, and what is the exposure? |
| data | What would we measure, and does the evidence in the record actually show what it claims? |
| competitor | If I were the strongest rival, how would I answer this, and how fast? |
| domain expert | What does someone who has done this for ten years know that the record misses? |
| ethicist | Who is affected who is not in the room, and is that fair to them? |
| skeptical investor | Why now, why us, and what has to go right that nobody has proven? |
| first time user | Coming in cold, where do I get stuck or give up? |
| maintainer | In two years, who keeps this alive, and what does it cost to change? |

Defaults when the user names nothing: 5 seats for a full trial (premortem plus the four that bear most on the
criteria), 3 for `--quick` (premortem plus two).
