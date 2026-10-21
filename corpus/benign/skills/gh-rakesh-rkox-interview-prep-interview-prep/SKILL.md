---
name: "interview-prep"
description: "Interview-prep front door: shows what to practise today, runs a 15-minute daily drill from a question bank, and points to the right coach skill. Use for 'what should I practise today', 'daily drill' or 'weekly review'."
---

# Interview Prep (front door)

Use for "what should I do today", "daily drill", "weekly review", or when the user is unsure which coach to use. It reads the tracker, recommends one session, and runs the short daily drill. Full rounds are run by specialist skills; this skill does not replace them.

## Specialist skills (optional companions)
This skill works alone. If a companion skill below is installed, route to it; if not, run a short version of that session inline.
- `question-bank`: import files, add or refresh questions, bank report.
- `interview-coach`: technical concept rounds, learn log, job description intake.
- `sql-pandas-practice`: SQL and Pandas problems that are actually run.
- `behavioral-interview-coach`: stories, intro pitch, behavioral rounds.
- `presentation-interview-coach`: project walkthroughs and mock presentations.
- `resume-defense-coach`: defending every resume bullet.
- `analytics-case-coach`: KPI, root-cause, dashboard and pipeline cases.
- `interview-debrief`: log a real interview, readiness check, funnel.

## Tracker (Notion)
Find the parent page titled **"Interview Prep Coach"** (search by title) and locate the databases below under it by name. If the page or a database is missing, tell the user and point to the README for the schema. Do not invent IDs.

| Database | Purpose |
|---|---|
| Topics | Skills to practise, with status, scores, difficulty, last asked |
| Presentation Topics | Project walkthrough topics |
| Question Log | One row per answered question, with the full answer in the page body |
| Question Bank | Reusable questions with times asked and average score |
| Inbox | Files or notes waiting to be turned into questions |
| Reference Library | Study material |
| JD Targets | Jobs being pursued, with status, interview date, readiness, weakest required topic |
| Real Interviews | Actual interviews and their outcomes |
| Resume Bullets | Resume claims to be defended |
| Story Bank | Behavioral stories |
| Projects | Projects used for walkthroughs |

Property names follow the README schema. Date properties are written as `date:<Property>:start` with `date:<Property>:is_datetime` = 0.
Never delete or archive rows. This skill is read-only except for the Question Log, Question Bank and Topics rows written by the daily drill.

## Mode 1: Today's plan
Query active JD Targets (Status Researching, Applied or Interviewing, with Interview Date, Readiness Verdict, Weakest Required Topic), Topics and Presentation Topics, Resume Bullets, the last 30 Question Log rows, Real Interviews with Outcome Pending, and Inbox rows with Status New or Needs Approval.

**Lead with one recommended session**, chosen by the first rule that applies:
1. A real interview within the next 3 days: run a mock of that round type for that job, starting with its weakest required topic.
2. A real interview that has happened with no debrief logged: `interview-debrief`.
3. A Core topic overdue (Last Asked empty or more than 14 days ago): the coach that owns that category.
4. The active job with the lowest readiness: its Weakest Required Topic, with the coach that owns it. If readiness was never checked, run the readiness check via `interview-debrief`.
5. Final resume bullets still Not Tested: `resume-defense-coach`.
6. Otherwise: the daily drill.

Give the reason in one line, then the two next-best options in one line each. Do not list everything. Add one line if Inbox files are waiting (New or Needs Approval), because real questions in the bank are the priority material; point to `question-bank`.

## Mode 2: Daily drill (about 15 minutes)
1. Select 3 topics: **1 from an overdue Core topic, 1 from the weakest topics, 1 from the active job's required topics.** Mix technical and behavioral. SQL or Pandas topics get a short conceptual or read-the-query question here; point to `sql-pandas-practice` for executed practice.
2. Get the questions from the bank, preferring real questions (aim for at least 30% when available, real ones first). If `question-bank` is installed, follow its "Serve questions" mode. If no suitable Active question exists, write one and save it to the bank first (Active, Bucket = Generated, Verification = Model-written).
3. Ask one at a time. Score each with the rubric, caps and difficulty of the coach that owns the topic (`interview-coach` for technical, `behavioral-interview-coach` for behavioral); load that skill if it is available. 7 to 8 means genuinely interview-ready; do not inflate.
4. After each answer: score, why, what was missing, at most one improvement, and a one-line comparison with the earlier attempt on that topic.
5. Write back: a Question Log row per question with the Bank Question relation and the full answer verbatim in the page body, Attempt, Previous Score, Answer Excerpt, Session = "Daily drill <date>"; update each bank row (Times Asked + 1, Last Asked, Latest Score, Average Score) and each Topic (Latest Score, Average Score, Times Asked + 1, Last Asked, Current Difficulty, Status, Gap Notes).
6. Close with one line: the topic to look at next.

## Mode 3: Weekly review
When asked: sessions and questions in the last 7 days by Stage, average score versus the previous week, topics that moved up or down, core topics still overdue, share of questions from the real buckets, readiness changes for active jobs, and one recommendation for the coming week. Conclusion first, one screen.

## Daily reminder
If the user wants a daily reminder and Calendar tools are available, offer a recurring 15-minute "Interview drill" block. Ask for the time and days, then create it **only after they confirm**. If Calendar tools are not available, say so.

## Working style
Lead with the conclusion. No strategic reframes the user did not ask for. Flag contradictions in the tracker before acting. Confirm before anything irreversible or external.
