# Resume rules

Two readers, in this order: software (ATS parser, then often an LLM screener that checks the recruiter's criteria against the resume text), then a hiring manager who skims for about 7 seconds and then reads the parts that match what they need. Write for both. Neither one rewards decoration.

## Format (fixed; `scripts/build.py` enforces it)

- One column, reverse-chronological, US Letter, Arial 10.5pt body, 0.6-0.7in margins.
- Name and contact line as plain text at the top of the body. Never in a Word header or footer (Greenhouse, Workday and others drop header/footer content).
- No tables, text boxes, columns, icons, photos, skill bars, charts, logos, or colored backgrounds. No emojis. Only plain bullets.
- Section headings use standard names only: Summary, Experience, Projects, Education, Certifications, Skills (also accepted: Publications, Patents, Open Source, Speaking). Parsers and LLM screeners locate sections by these names.
- Order: Summary, Experience, (Projects), Education, (Certifications), Skills. Skills goes at the bottom so the first screen is the summary and recent work.
- Role line: `Title | Company | Location | Mon YYYY - Mon YYYY` (or `Present`). Plain hyphen with spaces. One format throughout. Month + year on every role, because Greenhouse and Workday compute years of experience from these dates.
- Promotions at one company: one `###` line per title, each with its own dates, so title progression is visible.
- Contact line: City, ST | email | phone | linkedin.com/in/x | github.com/x. No full street address. Drop "https://" and "www".
- Length: 1 page under ~5 years of experience; 2 pages for senior and up (forcing a staff/director resume onto one page reads as under-leveled). Never 3.
- Word budget: 475-750 words of resume text. About 600 is the sweet spot for one page and ~700 for a senior two-page resume; past that, readers skim past the best material. `verify.py` warns outside the range.
- Files: DOCX (most reliable for Workday/iCIMS) and PDF (for Greenhouse/Lever/Ashby and email). Both under 2.5 MB. File name `First-Last-Resume-Company.pdf`.
- Plain ASCII punctuation: straight quotes, no em/en dashes, no ellipsis character. The em dash is also a measured AI tell in resumes (Simplify data: 0.1% of resumes in 2024, 2.7% in 2026).

## How AI screeners read it (design for this)

Ashby, Greenhouse Talent Matching, Workday HiredScore, and LinkedIn Hiring Assistant pull structured facts (titles, employers, dates, years, skills) and then check the recruiter's written criteria against the text, often citing the line that proves each one. A criterion with no findable evidence comes back "unknown", which is close to a miss. So:

- **Every must-have needs a bullet that proves it in context**, not just a Skills entry. "Kubernetes" in Skills plus "Moved 40 services from EC2 to Kubernetes (EKS)..." in a bullet beats a Skills entry alone. `verify.py` warns on Skills-only terms.
- **Use the JD's exact spelling at least once.** Recruiters still run literal Boolean searches. If the JD says "Amazon Web Services (AWS)", use both forms once, then either.
- **Titles and dates must be clean and consistent with LinkedIn.** They drive years-of-experience filters and "title relevance" scores.
- **Don't keyword-stuff.** Some screeners reward it, others penalize it, and every human notices. Each keyword appears where it's true, usually 1-3 times total.
- **Knockout facts** (work authorization, location, clearance) go in the contact line or summary only when the JD makes them a requirement.

## Summary (top, 3-4 sentences, rewritten for every JD)

1. Level and specialty in the JD's own title words, plus years if they help: "Engineering director with 15 years in infrastructure and security products, the last six leading platform teams of 20-40 engineers."
2. The strongest proof point for the JD's main problem, with a number the user supplied.
3. A second requirement with evidence.
4. (Optional) The differentiator: a domain, a scale, a kind of team built, a notable outcome.

No first person, no objective ("seeking a role where..."), no unsupported traits (results-driven, passionate, detail-oriented, excellent communicator). Each sentence states facts the hiring manager can check against the bullets below. If a sentence would fit any candidate's resume, cut it.

## Experience bullets

The pattern is what you did, to what, at what scale, with what result. Google's XYZ ("accomplished X as measured by Y by doing Z") is the reference shape, but don't force every bullet into it; uniform bullets are a tell.

- Start with a plain, specific verb: built, wrote, cut, moved, migrated, ran, led, hired, designed, replaced, shipped, fixed, set up, took over, rebuilt, negotiated. Some bullets can lead with the result ("Cut AWS spend $1.2M/yr by...").
- Name the system and the technology inline. Hiring managers look for stack in context.
- Give scale (rps, users, data size, services, teams, headcount, budget) and a result with a baseline where possible ("p99 from 900ms to 180ms", not "improved latency").
- Show ownership honestly. "Led" means they led. "Co-designed" is fine and more credible than an inflated claim.
- Vary length: 8 to about 28 words. A simple fact gets a short bullet.
- Bullet budget: 3-5 for each of the two most recent roles, 1-3 for older roles, title line only beyond ~15 years (or an "Earlier experience" line). Start from the three best accomplishments in each role and add only what this JD needs. `lint.py` warns past the budget.
- Front-load every bullet. Eye-tracking shows recruiters read the first 5-8 words of a bullet in an F-shaped scan and decide there whether to keep reading. Those words carry the accomplishment with its context, or the metric itself ("Cut GPU spend ~45% by..."). Don't open with a context clause (As part of, In order to, Working with).
- Prefer money when the user has it: a percentage plus what it saved or earned ("cut GPU spend ~45%, about $X a month"). With no number at all, use another objective signal: speed (shipped in 6 weeks), awards, customers won, or a project it unblocked.
- Not every bullet needs a number. Roughly half to three quarters with a number is natural; a number in every line looks manufactured.
- No duty bullets ("Responsible for...", "Worked on..."). No -ing riders tacked on for weight (", ensuring...", ", resulting in...", ", fostering..."): make the result its own clause.
- No pronouns in bullets (I, me, my, we, our). Team words (collaborated, assisted, supported, helped) are fine once or twice where they're accurate; past that, say what the user owned.
- Order bullets within a role by relevance to this JD, not by date. The strongest bullet goes first: readers skip the last bullets of a role and barely read older roles.
- Optional `- Stack: ...` as the last bullet of the two most recent roles: the main technologies used there, JD terms first. It puts skills in context for screeners, so they aren't only in the Skills list, and it doesn't count toward the bullet budget. Use it instead of repeating the same tools in every bullet.

Before/after:

> Spearheaded migration to Kubernetes, ensuring seamless deployments and driving operational excellence.
> Moved 40 services from hand-built EC2 hosts to EKS over two quarters; deploys went from weekly to 30+ a day and the on-call page rate dropped by half.

> Responsible for managing a team of engineers and fostering a culture of collaboration.
> Hired 9 of the 14 engineers on the data platform team; two were promoted to senior within 18 months.

## Skills (bottom)

- 3-5 labeled rows, e.g. `Languages`, `Cloud and Infrastructure`, `Data and Streaming`, `Security`, `Observability`, `Leadership` (manager tracks may skip a leadership row; those skills belong in bullets).
- 10-25 items total. Each must be something the user can be interviewed on (profile depth "production owner" or "used regularly").
- Put JD must-haves first in each row, using the JD's spelling. No duplicates across rows. No soft skills. No version numbers unless the JD asks.
- Drop stale or trivial items (MS Office, Jira, "Agile") unless the JD names them.

## Company context

A hiring manager skimming the left edge looks for company names and titles first. A company they don't recognize gets one short line under the role header saying what it does, plus one size or stage fact from the profile: "AI security platform for enterprise prompt traffic; Series B". Skip the line for household names. Use only facts in the profile's `Context` field; if it's empty, ask or leave the line out.

## Selection and tailoring

- Pull from the profile only what serves this JD. Older or unrelated roles get compressed, not deleted (gaps raise questions).
- Mirror the JD's problem: if they're scaling from 10 to 50 engineers, lead with the time you did that.
- Keep the title true. If an internal title was unusual ("Member of Technical Staff"), the standard equivalent can follow in parentheses only if accurate: "Member of Technical Staff (Staff Engineer level)".

## Red flags hiring managers cite

Unexplained gaps (one line explaining is fine: "Career break: family care, 2021"), titles that don't match LinkedIn, metrics without baselines, laundry-list skills, brand names without scope, keyword stuffing, over-designed layouts, typos, buzzword adjectives, and polished claims with no named tools or numbers. That last one is the strongest "AI wrote this" signal.
