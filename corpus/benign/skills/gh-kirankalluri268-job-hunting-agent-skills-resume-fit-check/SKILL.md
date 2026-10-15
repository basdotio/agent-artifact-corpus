---
name: resume-fit-check
description: Scores how well a specific résumé will pass ATS parsing and an initial human recruiter scan for a specific job description. Use when asked to check, grade, or diagnose a résumé's fit against a job posting — produces an ATS-parseability read, keyword/must-have match score, human-scan-appeal score, and an overall confidence number with reasoning and a prioritized fix list. Does not rewrite the résumé (see the tailor-resume skill for that).
license: MIT
---

# Résumé Fit Check

Given a job description and a résumé (plus optionally a GitHub/portfolio
link), estimate the odds this specific résumé clears ATS parsing and an
initial human recruiter scan for this specific job — with a confidence
score, section-by-section reasoning, and a prioritized, concrete fix list.
This skill only *diagnoses*; it does not rewrite the résumé. If the fixes
should actually be applied, hand off to a résumé-tailoring skill afterward
(e.g. this repo's `tailor-resume`) and say so.

The scoring model is built from actual research into how ATS and recruiters
work (not popular myths) — see "What this is grounded in" below. The
single biggest finding driving this skill's weighting: ATS almost never
silently auto-rejects a résumé — it's a search index a human queries — and
a human then skims for ~7-10 seconds. Parseability and human-scan appeal
both matter; neither is a magic gate to "beat."

## 0. Inputs needed

Required:
- **The job description** — URL or pasted text. If a URL, fetch it and
  extract title, responsibilities, required qualifications, and any "nice
  to have" section. Decode obfuscated Cloudflare mailto hex strings if
  present (first byte = XOR key, XOR every following byte, ASCII-decode).
- **The résumé to evaluate** — an attached file (PDF/docx preferred, since
  file format affects the ATS-parseability check), or pasted text.

Optional, use if given, don't block on their absence:
- GitHub/portfolio/LinkedIn URLs — check whether project claims are
  verifiable and whether skill-list depth is corroborated.
- Years of experience level / whether this is a new-grad application —
  changes which criteria matter most (see step 3).

If the résumé is missing, stop and ask for it — don't evaluate a résumé
you haven't actually seen. Evaluate one concrete document at a time, not a
person's general profile — if a live profile/CV source is implied but no
concrete file or text is given, ask which document to evaluate.

## 1. Extract the JD's actual gate criteria

Pull, separately:
- **Must-haves**: explicit required qualifications, years of experience,
  required tech/tools, required degree/certs, any explicit knockout
  criteria (e.g. "must be authorized to work in X", "must have 3+ years of
  Y").
- **Nice-to-haves**: anything phrased as preferred/bonus/plus.
- **Repeated terms**: anything mentioned 2+ times across the posting —
  this signals real weight even if not in a bulleted requirements list.
- **Implicit pedigree signals**: does the posting name specific companies,
  a competitive bar ("top-tier", "FAANG experience"), or a narrow domain
  that suggests an unstated filter beyond the literal skill list? Note
  this explicitly — research found recruiters' real rejection driver is
  often unstated pedigree/background fit rather than the stated skill
  gaps, so don't only score against the literal bullet list.

## 2. Score ATS-parseability (does the document even extract cleanly?)

If a file was attached, inspect its actual structure, don't guess from a
text description:
- PDF: extract text with `pdfplumber` or `pypdf` (`pip install pdfplumber
  pypdf` if needed) and compare the extracted text order/completeness
  against the visual layout. If sections go missing, merge together, or
  reorder in the extracted text, that's a real parsing failure, not a
  hypothetical one.
- docx: extract with `python-docx` similarly.
- Flag, specifically: multi-column layouts, tables, text boxes/columns
  rendered as text frames, graphics/icons carrying meaning (e.g. a phone
  icon with no adjacent label text), contact info placed in a
  header/footer (frequently dropped by parsers), non-standard section
  headings ("My Journey" instead of "Experience"), and unusual fonts that
  may not embed/extract cleanly.
- This is a pass/fail-leaning check, not a big point contributor — most
  résumés that are single-column with standard headings pass cleanly.
  Don't overweight it just because it's easy to check mechanically.

## 3. Score keyword/skill match against the JD

- Check each must-have against the résumé: present verbatim or as a clear
  true synonym (not stretched)? Flag any must-have that's simply absent —
  this is the single highest-leverage gap to name.
- Check nice-to-haves and repeated terms similarly, weighted lower.
- Check *where* matched terms land: headline/summary and first bullets of
  the most relevant entries carry more weight than a buried mention deep
  in an old role — position matters because that's what a time-pressured
  human scan actually reads first.
- Check for keyword stuffing / unnatural repetition — a term crammed in
  3-4 times with no supporting detail reads as gaming, not fit, and
  insider accounts say this is often visible to reviewers and can
  actively hurt rather than help. Flag it as a negative, not a strength,
  if found.
- If this is plausibly a new-grad/early-career application (little work
  history), explicitly check whether *projects* substitute credibly for
  the experience-years requirement — research found no formal industry
  standard exists for this substitution, so judge it on concrete evidence
  (a real, working, described project) rather than assuming it's
  accepted.

## 4. Score human-scan appeal (the 7-10 second read)

This is where most résumés that "pass ATS" still get rejected, so weight
it heavily. Check, in the order a real scan happens:

1. **Name, most recent title, most recent company** — is the
   headline/title line immediately legible and relevant to the JD's role
   title?
2. **Quantified impact vs. task listing** — for each bullet under
   experience and projects, is it an Action + Result + Metric statement,
   or a bare responsibility description? Count the ratio. This is the
   single most convergent "what actually gets a closer look" signal
   across every source found — weight it accordingly (this should be the
   single largest scoring factor after must-have keyword match).
3. **Career narrative coherence** — does experience show growing
   responsibility, or does it read as scattered/unrelated? For a new
   grad, is there a coherent throughline across projects/internships
   rather than an unfocused list?
4. **Red flags a fast skim would catch**: typos/grammar errors (actually
   read the text closely, don't skim it yourself), unexplained gaps,
   inconsistent date formats, a wall of unbroken text, buzzword-heavy
   bullets with no evidence ("team player", "hardworking", "synergy"), an
   unprofessional-looking email address, length (more than one page for a
   new grad/early-career candidate is itself a mild red flag).
5. **Verifiability**: if GitHub/portfolio links were given, do the linked
   projects actually back up what the résumé claims? Unverifiable or dead
   links are a real ding — check them rather than assuming.
6. **Skill list hygiene**: a focused, curated list of skills actually used
   with depth beats a long dump of every technology ever touched — flag
   an oversized skill list (roughly 15+ items with no grouping/curation)
   as a negative.

## 5. Produce the verdict

Give three numbers plus a combined read, not just one opaque score — this
mirrors that ATS-pass and human-scan-pass are genuinely different
hurdles:

- **ATS parseability**: Pass / Likely Pass / At Risk / Likely Fail, with
  the specific structural reason.
- **Keyword/must-have match**: X out of Y must-haves clearly present,
  plus a 0-100 score weighted toward must-haves > repeated terms >
  nice-to-haves.
- **Human-scan appeal**: 0-100 score built from step 4's weighted checks.
- **Overall confidence this résumé gets a callback for this specific
  role**: a single 0-100 score (roughly: 15% ATS parseability + 40%
  keyword/match + 45% human-scan appeal, since research shows the human
  read is where most real rejection happens once a résumé is parseable)
  with a plain-language label (Low <40 / Medium 40-70 / High >70) — and
  an explicit caveat every time: research found even professional
  recruiters agree with each other only ~64% of the time and predict
  interview success at only ~55% accuracy, so present this as a genuine,
  well-reasoned estimate, not a guarantee, and say so in those terms.

For each score, give the reasoning in 2-4 sentences citing the *specific*
résumé content that drove it (quote the actual bullet or line, don't
speak abstractly) — this is a diagnosis the candidate needs to be able to
act on, not a grade.

## 6. Fix list

List concrete fixes, ranked by leverage (highest-impact first, per the
weighting above — a missing must-have keyword or an unquantified bullet
in the top experience entry outranks a formatting nitpick). For each fix:
name the exact change (quote the current text and what it should become,
using only true content the candidate actually has — never invent a
metric or claim to suggest adding; if a real number isn't available, say
"add the actual number if you have it" rather than fabricating one).
Separate "must fix" (must-have gaps, parsing breakage, typos, dishonesty
risks) from "would strengthen" (nice-to-have phrasing, narrative polish,
skill-list curation).

End by naming whether the next step should be a résumé-tailoring pass (if
the fixes are mostly reordering/rephrasing existing true content) or a
note that some gaps genuinely can't be fixed by editing (e.g. a missing
must-have qualification that doesn't exist yet) — don't imply editing can
paper over a real qualifications gap.

## What this is grounded in

This skill's weighting comes from actual research (not generic
resume-tips consensus): ATS is a human-configured search index, not an
autonomous rejector, so parseability is a pass/fail check, not a big
scoring lever; recruiters skim in ~7-10 seconds in a fairly consistent
F-pattern (name → title → company → dates → previous role → education);
quantified impact statements are the most convergent signal across every
scoring rubric and informal account found; keyword-stuffing/gaming mostly
backfires or gets caught; and even professional recruiter judgment is
only ~55% accurate with ~41-point disagreement between reviewers on the
same résumé — which is why this skill states a confidence score with an
explicit uncertainty caveat rather than a false-precision single number.
