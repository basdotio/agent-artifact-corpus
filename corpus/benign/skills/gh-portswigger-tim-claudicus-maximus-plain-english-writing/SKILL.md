---
name: plain-english-writing
description: Write and edit clear, plain English. Use it whenever you write, edit, rewrite or proofread text, even a single sentence: docs, READMEs, guides, explanations, error messages, release notes, emails and chat messages.
---

# Plain English writing

Write so that the reader understands on the first read. Find the reader and their goal, then write in plain words. If you are writing a documentation page, also choose its type (section 2).

**These rules are guidelines, not laws.** Follow them by default. Depart from one when following it would take away meaning or make the text harder to read. The test is the reader: does the text still say the right thing, clearly? Say in one line what you did and why.

`references/ste-and-style.md` has the ASD-STE100, Strunk and gov.uk rules in full, with the reason for each. Open it to check why a rule exists, or when two rules seem to conflict.

## 1. Write plainly (any text)

Find the reader and their goal first. If you cannot say it in one sentence, ask the user.

**Sentences and structure**
- Put the main point in the title and the first sentence. Many readers stop early.
- Keep sentences short: 20 words or fewer in steps, 25 or fewer elsewhere.
- Give each paragraph one topic and no more than 6 sentences.
- Use the active voice, so the reader sees who does what.
- Keep related words together. Put the key word at the end of the sentence.
- Use parallel form in lists and headings. Write headings in sentence case, and make them descriptive.

**Words**
- Use one term for one thing, every time. Two names make the reader think there are two things. Define a technical term once, at first use.
- Use the simple word (*use*, not *utilise*) and the verb, not the noun form (*decide*, not *make a decision*).
- Be specific: "The build fails if the file is missing", not "Problems can occur".
- Cut filler such as *very*, *really*, *basically* and *just*. Avoid *simply*, *easy* and *please*: they are opinions or padding, and *simple* can make a struggling reader feel at fault.
- Avoid idioms, slang, metaphors and Latin abbreviations (*e.g.*, *i.e.*, *etc.*). They do not translate, and not every reader knows them.
- Keep the articles and the subject ("Remove the bolt and the stop"). Use "that" after "make sure" and "show".
- Rewrite noun stacks of more than 3 words: "error when the session token is not valid", not "session token validation error".
- Write link text that says where the link goes, never "click here".
- Use "you" for the reader. Use "we" for the organisation, or for writer and reader together in a tutorial.

**Strict text.** In steps, warnings and reference, also avoid contractions, semicolons, and lowercase *may*, *might*, *shall* and *should*. Use *must* for a requirement and *can* for an ability. In a friendly tutorial or explanation, contractions and *should* are fine.

## 2. Documentation pages: choose a type

Use this section when you write or restructure a documentation page: a README, guide, tutorial, reference or explanation page. Skip it for an email, a commit message, an error message, a release note or a single sentence. For those, section 1 is enough.

Choose **one** type (Diataxis). If a page needs two, split it and link the pages.

- **Tutorial** ("teach me"). State what the reader will achieve. Give one path, with no choices. Show the expected result after the key steps. Keep any definition to a sentence or two and link out for background: do not add a "What is X?" section. End by saying what the reader built and where to go next.
- **How-to guide** ("help me do X"). Name the task in the title. List the prerequisites. Give numbered steps (see section 3). Link to background and do not explain it. End when the task is done.
- **Reference** ("tell me the facts"). Be neutral, complete and consistent. Use the same format for each entry (name, type, default, description, example), shaped like the thing it describes. Give no opinions and do not teach.
- **Explanation** ("help me understand"). Write prose: context, reasons, trade-offs, alternatives. Opinions are fine if you argue them. Give no steps.

Quick test: a reader who is studying needs a tutorial or an explanation. A reader who is working needs a how-to or a reference.

## 3. Steps and warnings

- Write each step as **one action**, in the imperative: "Click **Save**." Do not join actions with "and", "then" or a second sentence. Count the verbs you tell the reader to do. Aim for 1.
- Text after a step gives information only. If it hides an instruction ("Copy it now", "Replace `OLD_ID` with the real ID"), make that its own step, or move it to a "Before you start" line.
- Put a condition before the action: "If the file exists, delete it."
- Put a warning before the step it applies to, as a line above the step list or as its own step. Start with the command and then give the result: "Do not disconnect the drive. Data can be lost." Avoid putting it after the step or inside it.
- Use only the actions the user described. If the reader needs another (for example a check before a destructive action), add it and say so in your report. If you do not know a command, name or behaviour, write `TODO: confirm ...`. Do not guess.

Do not:
> 1. Create the new key: `vault-cli key create --name prod`
>    The command prints the new key. Copy it now.
> 2. Do not revoke the old key until the app works. Revoke the old key: `vault-cli key revoke --id OLD_ID`
>    Replace `OLD_ID` with the ID of the old key.

Do:
> Before you start, get the ID of the old key. You use it as `OLD_ID` in step 4.
>
> **Warning:** Do not revoke the old key before step 3 passes. The app loses access.
>
> 1. Create the new key: `vault-cli key create --name prod`
> 2. Copy the new key from the command output.
> 3. Make sure that the app uses the new key.
> 4. Revoke the old key: `vault-cli key revoke --id OLD_ID`
>    The old key stops working at once.

Two other short forms:
- **Error message.** Say what happened, why, and what to do next: "Cannot save `report.pdf`: the disk is full. Delete some files, then try again."
- **Release note.** Start with the change from the user's point of view. Then give the reason and any action needed: "Exports now include the row ID. Update any scripts that read column 1."

## 4. Edge cases and bending the rules

Order of priority: accuracy and the reader's task, then the project's own style guide and terms, then these rules.

- **Opinion and argument.** A longer sentence or a hedge such as "usually" can carry a claim better than clipped sentences. Keep the hedge if the claim is uncertain.
- **Exact terms.** Keep *idempotent* or *TLS handshake* when a plain word is wrong or vague. Define it once.
- **Passive voice.** It is fine when the actor is unknown or unimportant: "The token is revoked after 24 hours."
- **Tone.** A light touch of personality is fine in explanations, but not in reference or steps.
- **Requirement words.** Specifications and API contracts can use the RFC 2119 keywords (MUST, MUST NOT, SHOULD, SHOULD NOT, MAY, and so on) in capitals only, as RFC 8174 says. Add the standard line near the top: "The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY in this document are to be read as described in RFC 2119 and RFC 8174." Use them for real requirements, not casual advice.
- **Spelling.** ASD-STE100 uses American English and gov.uk uses British English. Follow the project. If it has no rule, ask.
- **Certified STE.** This skill does not include the ASD-STE100 dictionary. If the user needs certified STE, point them to the official specification and dictionary.

## 5. Check and report

- [ ] A clear reader goal. For a documentation page, one page type.
- [ ] The title and first sentence say what the page is for.
- [ ] Terms are used consistently and defined at first use.
- [ ] Each step has one action, in order, with the expected result.
- [ ] Sentences are short, active and free of filler.
- [ ] Links say where they go. Code and commands can be copied and run.
- [ ] For a documentation page of about 150 words or more, the readability check is run and its targets are met, or the miss is explained.

**Readability check.** For a documentation page of about 150 words or more (not a reference page), run the script `scripts/readability.py` in this skill's folder on your draft. It reads a file or standard input, ignores code, and prints Reading Ease, grade level and the longest sentences. The targets are Reading Ease 40 or higher and grade 10 or lower. If you miss a target, shorten the longest sentences it lists and run it once more. The score is a check, not a goal, and meaning comes first. If you keep a miss on purpose, for example in a technical explanation, say so in your report.

When you edit existing text, keep the author's meaning and facts. Do not add actions, commands or names that the original does not state. Fix the structure first, then the sentences, then the words. Ask, or mark the gap with `TODO`, instead of inventing facts.

In your report, say which page type you wrote (for a documentation page), what you added or left as a `TODO`, and where you bent a rule and why. Give a short summary of the main changes, not a line-by-line diff, unless the user asks for one.
