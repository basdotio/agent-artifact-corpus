# Evidence behind the rules (research compiled 2026-10-11)

Flags: [V] vendor-documented, [S] survey or study with a stated sample, [A] practitioner or blog consensus, [W] weak or conflicting.

## Parsing and ATS
- Greenhouse cannot parse files over 2.5 MB or with unrecognized characters; the recruiter then re-keys the profile by hand. [V] https://support.greenhouse.io/hc/en-us/articles/200989175-Unsuccessful-resume-parse
- Lever parses DOCX/PDF/RTF/HTML/ODF, not images; "if you can't highlight it, it won't parse." [V] https://help.lever.co/hc/en-us/articles/20087345054749
- Workday loses right-column text from two-column layouts and drops text in tables, text boxes, and headers/footers; in one test, 14 of 20 Canva templates failed and the 6 single-column ones survived. [A] https://atsverification.com/blog/canva-templates-workday-test/
- LaTeX/Typst ligatures can break keyword matching ("fi" glyph). [A] https://atsverification.com/blog/latex-resume-ats-friendly/
- Of 25 recruiters interviewed (Enhancv, 2025), 23 said their ATS does not auto-reject on format; the "75% rejected by ATS" figure traces to a 2012 sales pitch. The real risk of a bad parse is a garbled profile that recruiter search and AI filters then miss. [W] https://enhancv.com/blog/does-ats-reject-resumes/

## AI screeners
- Ashby: the recruiter writes criteria; the AI marks each Meets / Does not meet / unknown, cites resume text, and doesn't rank or score. [V] https://www.ashbyhq.com/blog/product/ai-assisted-application-review
- Greenhouse Talent Matching: LLM extracts skills, titles, years, dates, and employers and compares them to requirements; there's no auto-reject. [V] https://support.greenhouse.io/hc/en-us/articles/41131616864283-Talent-Matching-Data-Processing-FAQ
- Workday HiredScore: A-D grades, with an LLM fit-and-gap check per qualification. [V] https://doc.workday.com/hiredscore/en-us/workday-hiredscore/recruiter-productivity-/concept--hiredscore-grades.html
- LinkedIn Hiring Assistant: "Top fit" means all must-haves met; missing any must-have means "Not a fit". [V] https://business.linkedin.com/hire/ai-transparency/hire
- LLM screeners favor LLM-written resumes (self-preference bias); the study found no evidence of AI-detection penalties in screeners. [S] https://arxiv.org/html/2509.00462v3
- Keyword stuffing: some models are fooled by it and others penalize it. [W] https://arxiv.org/pdf/2507.11548 , https://giesbusiness.illinois.edu/news/2026/06/29/msba-research-examines-bias-in-ai-resume-screening
- Hidden-text prompt injection appears in about 1% of resumes, is now detected in production (hireEZ, Greenhouse), and helps only marginally. [S] https://www.metaview.ai/resources/blog/resume-prompt-injection , https://builtin.com/articles/hidden-ai-prompts-in-resume

## Hiring managers
- Initial skim is about 7.4 seconds; simple layouts with clear headings and bold titles do best. [V, recruiters, small sample] https://www.hrdive.com/news/recruiters-spend-74-seconds-looking-at-your-resume/541582/
- Hiring managers write the requirements and interpret resumes more flexibly than recruiters. [A] https://www.freecodecamp.org/news/how-to-write-a-developer-resume-recruiters-will-read/
- XYZ bullet formula (Google / Laszlo Bock). [A] https://www.inc.com/bill-murphy-jr/google-recruiters-say-these-5-resume-tips-including-x-y-z-formula-will-improve-your-odds-of-getting-hired-at-google.html
- Staff/principal signals: scope, cross-team direction, influence, external standing. [A] https://www.techinterview.org/post/3233474617/staff-principal-engineer-resume/
- Engineering manager resumes lead with scope, then team outcomes. [A] https://www.techinterview.org/post/3233474624/engineering-manager-resume/
- Teal admits its AI "sometimes generates numbers that aren't accurate." [V] https://tealhq.helpscoutdocs.com/article/60-using-ai-achievements
- Brag document prompts (Julia Evans). [A] https://jvns.ca/blog/brag-documents/

## AI tells and attitudes
- Use of at least one of spearheaded/leveraged/orchestrated/honed/streamlined rose from 32% of resumes (2023) to 52% (2025); em dashes rose from 0.1% (2024) to 2.7% (2026); bullets cluster at a uniform 14-18 words. The costliest tell is polished claims with no tools or numbers. [V, directional] https://simplify.jobs/blog/can-recruiters-tell-if-ai-wrote-your-resume
- TopResume (600 hiring managers, 2025): 19.6% would reject an AI-generated resume or letter; only 33.5% correctly identified the AI one in a test. [S/V] https://topresume.com/career-advice/ai-in-hiring-survey
- Wikipedia "Signs of AI writing" (the basis of the humanizer skill). https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing

## Cover letters
- Resume Genius (625 hiring managers): 83% read cover letters, most in under 2 minutes. [V, not engineering-specific] https://resumegenius.com/faq/who-reads-cover-letters
- Engineering view: letters are mostly ignored at big companies and matter for startups, pivots, and referrals. [A] https://www.techinterview.org/post/3233474628/cover-letters-engineers/

## Known gaps
No vendor parsing specs exist for Workday, iCIMS, or SmartRecruiters. No study isolates whether AI screeners reward quantified results. Resume-length data is old and comes from vendors. This skill uses a 3-4 sentence summary; practitioner guides lean toward 2-3.
