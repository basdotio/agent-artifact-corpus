# Interview: building the career profile and asking gap questions

The best resume tools interview first and write second. Generators that skip the interview fill gaps with invented numbers (Teal's own docs admit its AI "sometimes generates numbers that aren't accurate"). Your job here is to get real facts out of the user's head and into `profile/career-profile.md`.

## Ground rules

- **Harvest before asking.** Read everything in `profile/sources/` first (old resumes, LinkedIn PDF export, brag docs, perf reviews, promo packets, design docs). Pre-fill the profile and only ask about what's missing or vague. Never ask for something a document already answers.
- **Batch questions.** One role at a time, 3-6 questions per round. Use the agent's question tool, if available, when the answer is a choice (team size bands, level, yes/no); use a plain numbered list when answers are free text. Tell the user they can answer roughly, skip, or say "don't know".
- **Follow the thread.** When an answer mentions something bigger than the question ("we also had to rebuild the on-call rotation after that"), ask about it. Those side stories are often the best bullets.
- **Get honest numbers.** If they don't know an exact figure, ask for a range, a ratio, or a before/after they're confident about, and how they know it (dashboard, postmortem, OKR review, finance report). Record the confidence in the profile.
- **Non-numeric results count.** A passed audit, a customer kept, a team that stopped paging at 3am, a standard others adopted, a promotion of someone you mentored.
- **Capture their words.** Write down phrases the user uses to describe their work. Their phrasing beats yours in the final document and keeps it sounding like them.
- **Save as you go.** Update the profile file after each role so nothing is lost if the session ends.

## Order for a new profile

1. **Basics.** Name, city/state (or "Remote, US"), email, phone, LinkedIn, GitHub/portfolio, work authorization or clearance if relevant, willingness to relocate.
2. **Target.** Levels and role titles (see `levels.md`), company stage/size preferences, domains they want or want to avoid. Stored in frontmatter; changeable with `/tech-resume target`.
3. **Roles, newest first.** For each: title(s) with dates (month + year, including promotions), company, location, one-line company context (what it does, plus one size or stage fact such as funding stage, revenue, customers, or headcount; the resume prints it for companies a hiring manager may not know), team/org size, what they owned. Then the question bank below, focused on the 3-6 things that mattered most in that role. Spend most time on the last 2-3 roles; compress anything older than ~10-12 years.
4. **Projects, OSS, talks, writing, patents** if they support the target.
5. **Education and certifications.**
6. **Skills inventory.** For each technology: years, last used, depth (production owner / used regularly / familiar). Only "production owner" and "used regularly" go on a resume.
7. **Voice samples.** Ask for 2-3 things they wrote themselves without AI: work emails, Slack posts, a blog post, a design doc intro. Save to `profile/voice/`. These calibrate the cover letter.
8. **Stories.** 4-6 stories in situation/action/result form for cover letters and interviews: hardest technical problem, biggest disagreement, a failure and what changed, the work they're proudest of.

## Question bank

Pick from these; don't ask all of them.

**Impact and metrics**
- What changed because this existed? Before vs after on latency, cost, uptime, incidents, deploy frequency, revenue, conversion, support tickets, or hours saved.
- What was the baseline, and how do you know? (dashboard, postmortem, OKR review)
- How many users, requests per second, data volume, services, or teams depended on it?
- If you don't have an exact number, what's an honest range or ratio?
- You have a percentage: what is it in dollars per month or year, saved or earned? (the bill, a finance report, or count x unit price)
- No number at all? How fast was it (weeks, ahead of a deadline)? Did it win an award or a customer, or unblock another team's project?
- What would have happened if you hadn't done it? (risk avoided, deadline met, compliance, customer kept)
- Did anything show it worked months after launch?

**Scope**
- How many engineers, teams, or orgs did this touch? Budget or headcount?
- Was it one team, cross-team, org-wide, or company-wide?
- How long did it run, and what was at stake? (launch date, contract, audit)

**Ownership**
- Which part was specifically yours: the idea, the design, the build, the rollout, or getting people to adopt it?
- Who else was involved, and what would have been missing without you?
- Did you write the design doc or RFC? Who approved it, and who adopted it?

**Leadership, influence, conflict**
- Tell me about a disagreement over direction. What did you argue for and how was it decided?
- Who did you mentor? Did anyone get promoted or take on new scope?
- What process, standard, or practice did you introduce that people still use?
- (Managers) How many people did you hire, keep, or let go? Team size, attrition, delivery pace, engagement scores before vs after? Budget owned?
- (Directors and up) How many managers reported to you? What did the org look like when you arrived vs when you left? What business number did the org move?

**Technical decisions**
- What alternatives did you reject and why? What did the tradeoff cost?
- What was the hardest technical problem, and what was non-obvious about the fix?
- What would you do differently now?

**Brag-doc prompts** (useful when the user says "I don't know, I just did my job")
- If you were convincing a friend to join that team, what would you say about your work there?
- What did someone thank you for or praise you for?
- What broke less, got cheaper, or got faster after you showed up?
- What were you the go-to person for?

## JD gap questions (per application)

Ask only for must-haves that are weak or missing in the profile, plus the cover-letter inputs.

- The JD stresses [X]. Where have you done X, even partly, in a side project, or under a different name?
- They use [tool/domain]; you list [adjacent one]. How close was your work, and how fast did you ramp up last time?
- This level implies [scope]. What's your largest example of that scope?
- Your strongest percentage result for this JD: what is it worth in dollars?
- Is the company context line missing for any employer on this resume? (what it does, one size or stage fact)
- Why this company and role specifically? Anything concrete from their product, engineering blog, talks, or stack?
- Any referral, mutual connection, or earlier contact with the hiring manager?
- Is there anything in this JD you can't honestly claim, so we leave it out instead of stretching it?

## Profile completeness check

After `profile`, report per role: number of facts, how many have numbers, which have a stated baseline, and the 3 weakest spots. A role is "ready" when it has at least 3 facts with a scale or result and one with a before/after.
