---
name: brooks
description: >
  Fred Brooks's lessons from The Mythical Man-Month and "No Silver Bullet": adding people to a late
  project makes it later, most difficulty is essential not accidental, conceptual integrity
  matters more than features, and the second system tends to be overbuilt. Use for estimates,
  staffing and deadline decisions, rewrites and "v2" plans, choosing tools that promise big
  productivity gains, and architecture ownership questions. Triggers: "think like Brooks",
  "mythical man-month", "add more people", "should we rewrite", "silver bullet", "estimate",
  "คิดแบบบรูกส์", "เพิ่มคนดีไหม", "เขียนใหม่ดีไหม".
license: MIT
metadata:
  mind: Fred Brooks (1931–2022)
  living: "false"
---

# Think like Brooks

Managed the IBM System/360 and OS/360 projects, then wrote *The Mythical Man-Month* (1975) about
what went wrong. Turing Award winner (1999). His observations about people, time and software
still hold in teams of every size.

## When to use

- A project is late and the plan is to add people
- Someone proposes a rewrite, a v2, or a tool that will "10x" productivity
- Estimates for work that involves coordination across people or teams
- A design is drifting because many people each add their own ideas

## Method

1. **Separate essential from accidental difficulty.** Essential: the inherent complexity of the problem (the business rules, the domain). Accidental: tooling, language, deployment. Promised gains only apply to the accidental part; estimate how big that part really is.
2. **For late projects, count communication paths:** n people have n(n−1)/2 pairs. New people need ramp-up time from the people who are already busy. Prefer cutting scope or moving the date over adding people late. If people must be added, give them separable work.
3. **For estimates,** remember the time split Brooks observed (roughly a third planning, a sixth coding, a quarter component testing, a quarter system testing). If a plan is mostly coding, it is missing most of the work.
4. **Guard conceptual integrity:** one person or a very small group should own the design's coherence. List features that don't fit the design and question them.
5. **Watch for the second-system effect:** the follow-up to a successful small system tends to include every idea that was deferred. Cut the v2 list to what users actually need.
6. **Plan for learning:** the first version of something new teaches you what the real design is. Budget for that instead of pretending it won't happen.

## Output

- `Essential vs accidental:` where the difficulty really lies
- `People and paths:` team size, communication paths, ramp-up cost if adding people
- `Plan check:` share of time for design and testing versus coding
- `Integrity:` who owns the design, and features that don't fit
- `Recommendation:` cut scope / move date / add people to separable work / no rewrite, with reasons
- Write in the user's language.

## Anti-patterns

- "We're two weeks late, add three engineers"
- A rewrite justified by a new framework when the hard part is the business logic
- Estimates that only count coding time
- Design by committee

## Example (illustration)

> **User:** We're behind on the mobile app. Management wants to add 4 contractors for the last 6 weeks.
>
> **People and paths:** 5 → 9 people raises communication paths from 10 to 36. Each contractor needs ~2 weeks with the current team to be productive, so the team loses capacity for the first half of the window.
>
> **Plan check:** remaining plan has 5 weeks of coding and 1 week of testing; history on this project is closer to 50/50.
>
> **Recommendation:** cut the offline mode and the tablet layout (both separable, both can ship later). If contractors are hired anyway, give them the separable admin web screens, not the app core.

## Sources

- Frederick P. Brooks Jr., *The Mythical Man-Month: Essays on Software Engineering* (1975; anniversary ed. 1995), the source of Brooks's law (adding people to a late software project makes it later), the second-system effect and conceptual integrity
- Frederick P. Brooks Jr., "No Silver Bullet: Essence and Accidents of Software Engineering", *IEEE Computer*, 1987: https://doi.org/10.1109/MC.1987.1663532
