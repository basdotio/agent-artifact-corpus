---
name: linkedin-roast
description: Roast a LinkedIn profile with five separate Claudes (a recruiter, a hiring manager, a founder, an expert in the owner's field and a peer), then fix it: a new headline, an About section with search keywords, every experience entry rewritten, a banner file and a headshot prompt. Use when the user types /linkedin-roast followed by a profile (a PDF path, pasted text or a screenshot), or asks to "roast my LinkedIn", "review my LinkedIn profile" or "fix my LinkedIn".
---

# /linkedin-roast

The user gives you a LinkedIn profile after `/linkedin-roast`. Five reviewers roast it, each one alone. Then you fix it. Never flatter the profile, and never invent anything about the person.

## Numbers to use (from LinkedIn's help pages and blog, October 2026)
- Headline: 220 characters at most. LinkedIn's help pages do not print this number (it is the widely reported limit), so tell the user to trust the counter in the editor if it differs.
- About: 2,600 characters at most (LinkedIn's Talent Blog). LinkedIn Help suggests one or two short paragraphs about mission, motivation and skills.
- Banner: 1584 x 396 pixels, JPG or PNG, under 8 MB. It sits behind the profile photo, and the crop shifts with the browser window.
- Profile photo: JPG or PNG, from 400 x 400 up to 7680 x 4320 pixels, under 8 MB. LinkedIn says it must reflect the user's likeness.
- Saving a profile as a PDF: desktop only. Me, View profile, then More or Resources, then Save to PDF. English profiles only.

## 1. Read the profile
Everything after `/linkedin-roast` is the profile: a PDF path, a text file, a screenshot, or pasted text. If there is nothing, ask ONE question and stop: "Send me your profile as a PDF path, pasted text or a screenshot. On LinkedIn (desktop): Me, View profile, More, Save to PDF."

If a PDF cannot be read directly, try `pdftotext <file> -`. If that fails too, ask for pasted text or a screenshot.

Pull out: headline, About, every experience (title, employer, dates, bullets), education, skills, and any notes about the banner and photo (a saved PDF may not show them: write "not in the file" and move on). Remove email, phone and street address; nobody downstream needs them. Ask for nothing else.

Work out three things and print them on one line starting with "Assumed:": the owner's field (for example "product marketing"), their level (early career, mid, senior or leader) and the kind of job they seem to want. If the user says what job they want or what field they are moving into, use their words instead of guessing. Do not stop to ask; the user can correct you after.

Work only from what the user gave you. Do not open LinkedIn, log in, or search the web for this person.

## 2. Five roasters, each alone
Start FIVE sub-agents at once: one message with five Agent calls (older Claude Code versions call the tool Task). Wait for all five. Each prompt is its persona, the cleaned profile text, the rules and the format below, and nothing else. Never put one roaster's persona or answer into another's prompt, and never run a second round. That is what keeps them honest: five readers who cannot copy each other.

The five personas (use these words, filling in {field} and {level}):
1. **Recruiter.** "You are a recruiter hiring for roles like the ones this person seems to want. You look at 100 profiles a day and search by job title and keyword. You decide in six seconds whether to message."
2. **Hiring manager.** "You manage the team this person would join and you have an open seat. You ask one thing: can they do the job from day one, and what is the proof?"
3. **Founder.** "You run a small company and can make one hire. You have no patience for buzzwords. You want someone who owns results and ships."
4. **Expert in the field.** "You are a senior expert in {field} with 15 years in it. You can tell real depth from borrowed jargon, and you notice claims that do not add up."
5. **Peer.** "You work at the same level as this person, in {field} ({level}). Would you trust this profile? What would you copy? What makes you roll your eyes?"

Rules to put in every prompt:
- Read the profile alone. Use no tools and do not look this person up. Answer only from the text. If you cannot see something (a photo, a banner, a badge), do not mention it.
- Be brutal and specific about the writing and the evidence, never about the person: no comments on looks, age, gender, name, race, nationality, health or family.
- Quote the exact line you are roasting, then say what is wrong in plain words. No generic advice.
- If a section is missing or empty, that is the roast.
- Under 300 words.

Answer in exactly this format:
1. HEADLINE ROAST: quote it, then at most 3 sentences.
2. ABOUT ROAST: quote the worst line, then at most 3 sentences.
3. THREE WEAKEST EXPERIENCE BULLETS: each one quoted, with one sentence on why it is weak.
4. FIRST 6 SECONDS: what you would do in the first six seconds on this profile, and why.
5. SCORE: a whole number from 1 to 10.
6. FIRST FIX: the one change you would make first.

## 3. Show the roasts
Print the five answers, one block each with the role and score. Recruiter first, and open with the recruiter's headline roast. Do not soften a roast; cut only exact repetition. Then print:
- **What all five agree on:** a short numbered list of the problems at least three roasters raised, worst first, each ending "(n of 5)".
- The average score, and the lowest score with whose it is.

## 4. Fix it
Use only the profile and the five roasts. Never invent employers, titles, dates, schools, degrees, tools, skills, numbers or results. Where a fact is missing, leave `[ADD YOUR NUMBER: what to count]` (or `[ADD: what is missing]`) and ask at the end. Show before and after for everything.

**4a. Headline.** Write one new headline of 220 characters or fewer (count them and say the count), then two alternates. Put the job and the strongest search words first, then what you do and for whom, or the result. No mood words ("passionate", "driven"). Facts from the profile only.

**4b. About.** Rewrite it in 2,600 characters or fewer (count them), in one to three short paragraphs. The first sentence says what the person does and for whom, and the best proof comes early. First person is fine here.
- Choose 8 to 12 keywords: job titles, tools, methods and industries that (a) the profile already backs up and (b) the five roasters say people in this field search for. Use each in a real sentence about real work, once or twice at most. No keyword lists, no stuffing.
- Under the new About, print a table: keyword, where it went, why it helps. The reason: recruiters search by these words, and LinkedIn Recruiter's search highlights matches in the Summary, Experience and Skills sections.
- Keywords the profile does not back up go in a separate "Add only if true" list, not in the About.
- Say plainly: LinkedIn does not publish how it ranks profiles. This makes the profile match what recruiters type. It cannot promise a rank, interviews or connection requests.

**4c. Experience: every entry, with the Harvard MCS bullet format.** Rewrite EVERY experience entry, including the ones the roasters liked. Harvard College's Mignone Center for Career Success (MCS) does not publish a bullet formula by name. This skill uses what the MCS resume guide and its sample resume teach (careerservices.fas.harvard.edu/resources/create-a-strong-resume/):
- Start each bullet with an action verb, and use a different verb each time. MCS groups its verbs by type: leadership, communication, research, technical, teaching, quantitative, creative, helping, organizational.
- Say what you did, specifically, and end on the result. Make it fact-based: quantify and qualify. MCS lists "not demonstrating results" among the top resume mistakes.
- Specific, not general. Active, not passive. Written to express, not to impress. No flowery words.
- No "I", no slang, no unnecessary abbreviations, no story-telling. Easy to skim: one or two lines a bullet.
- Present tense for the current role and past tense for finished ones, as in the MCS sample resume. Write numbers as numerals, the same way each time.
- Keep each entry's title, employer and dates exactly as they are. Two to five bullets a role, strongest first. A bullet with no information in it ("various tasks as needed") can be removed: show it as "Removed" with the reason.
- A bullet that needs a number the profile does not have gets `[ADD YOUR NUMBER: ...]`. Never guess one. The user must be able to defend every line.

## 5. Images
You cannot draw or edit photos by yourself. Never say you did.

**5a. Banner.** Write `linkedin-roast-output/banner.svg` with `width="1584" height="396" viewBox="0 0 1584 396"`: a solid or two-colour background, and in large type the new job title plus one short line that is true in the profile (a specialty or a proof point). At most two lines of text, each about 40 characters or fewer at 56 px. Put the text in the middle or on the right, away from the lower left where the profile photo overlaps. No logos, no photos, no faces, no invented claims.

Then make `banner.png` from it. Try these in order and stop at the first that works: `rsvg-convert -w 1584 -h 396`, `magick`, `inkscape`, python `cairosvg`, or a headless browser (write `banner.html`: a margin-free page with the SVG in an `<img width="1584" height="396">`, then run Chrome, Chromium or Edge with `--headless --screenshot=banner.png --window-size=1584,396`). Check the size with `file banner.png` or `sips -g pixelWidth -g pixelHeight banner.png`: it must be 1584 x 396. Look at the PNG once to see that no text is cut off. If no converter works, keep only the SVG and say that LinkedIn takes JPG or PNG, so the user must convert it (open it in a browser and screenshot it, or use any free converter).

**5b. Headshot.** Look at the tools you have. ONLY if an image tool is connected that can generate or edit an image from a reference photo: ask the user for their own photo (a file path), run it, save the result in the output folder and say which tool made it. Never use anyone else's photo.

Otherwise write `headshot-prompt.md`: a ready-to-paste prompt for the image tool of their choice, plus "attach your own photo". The prompt asks for a clean, shoulders-up professional headshot of the person in the attached photo, keeping their real face and features, plain neutral background, soft even light, clothes that suit their field. Add three notes: LinkedIn says the photo must reflect your likeness, so do not let a tool change your face; use a square crop of at least 400 x 400 pixels, JPG or PNG, under 8 MB; the photo goes to whichever image tool they use, so they should read its privacy terms.

## 6. Write the result
Create ONE folder, `linkedin-roast-output/`, in the user's working directory:
- `roasts.md`: the five full answers and "What all five agree on".
- `new-profile.md`: the headline and two alternates, the About, the keyword table, the "Add only if true" list, every experience entry before and after, and every `[ADD YOUR NUMBER]` question.
- `banner.png` (and `banner.svg`), and `headshot-prompt.md` or the image the tool made.

Touch no other files. You cannot edit the live LinkedIn profile and must not try: the user pastes everything in themselves.

Finish in chat with the folder path, then the `[ADD YOUR NUMBER]` questions as one list ("answer these and I will update new-profile.md"), then this checklist:
1. Headline: paste the new one (220 characters or fewer).
2. About: paste it in.
3. Experience: replace each role's text, and fill in the `[ADD YOUR NUMBER]` gaps first.
4. Banner: upload `banner.png` (1584 x 396).
5. Photo: upload your new photo (at least 400 x 400, and it must look like you).

## Rules
- Be honest. If the profile is strong, say so, and say which roaster came closest to a bad verdict and why it held. Still run every step.
- Do not invent facts about the person, their employers or real companies. Say "assumed" when you guess.
- The five roasters are one model playing five roles alone. They are a structured second opinion, not five real people, and not career advice. Nothing here guarantees interviews, connection requests or a job.
- The profile goes to Claude like anything else the user shares. Tell them to leave out what they would not paste into a chat.
