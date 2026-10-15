---
name: agent-speak-readability
description: Rules and a mandatory pre-send check that make an agent's natural-language output readable to a human reader. Load this skill before you write any prose a human will read - a status line, a progress report, an explanation, a plan, a summary, a chat reply. Also load it when the user says your writing is hard to understand, vague, telegraphic, clipped, full of jargon, metaphors or invented words, or when the user says 看不懂, 说人话, 你的中文很难懂, 把话说完整, 不知道你在说什么. Cross-language rules live in this file. Load lang/zh/PRINCIPLES.md for Chinese output and lang/en/PRINCIPLES.md for English output.
version: 0.1.0
license: Apache-2.0
---

# agent-speak-readability

## 1. What this skill fixes

An agent writes for itself. The agent already knows the actor, the object, the
file and the result, so the agent compresses them out of the sentence. The
human reader does not know them. The result is text that looks confident and
carries almost no information.

This skill is not a style preference. This skill is a set of edits you perform
on your draft before you send the draft.

## 2. How to use this skill

1. Read the nine cross-language rules in section 3.
2. Read the rules for the language you are writing in:
   - Chinese: `lang/zh/PRINCIPLES.md`
   - English: `lang/en/PRINCIPLES.md`
   - Another language: apply section 3 alone, and use `lang/en/PRINCIPLES.md`
     as the model for what a language file adds.
3. Write your draft.
4. Run the pre-send check in section 4 on the draft. Edit the draft.
5. Send the edited draft.

If you write two languages in one reply, run the check once for each language.

Every file in this skill is written in English. The examples inside a language
file stay in the language of that file, because those examples are the thing
being taught.

## 3. Cross-language rules

### R1. Fill every slot of the action. This rule is the master rule.

Every clause describes an action. An action has slots: the **actor**, the
**action**, the **object acted on**, the **instrument**, the **place**, and
the **result**. Write every slot that exists. Never drop a slot because the
reader can work the slot out from an earlier sentence.

R1 is not about tidy noun phrases. R1 is about the arguments of the verb.
Adding the actor alone does not satisfy R1.

- Not acceptable: `Verified.`
- Still not acceptable: `The verification script reported a pass.` (the object
  of the verification is still missing)
- Acceptable: `The verification script confirmed that the deduplication logic
  drops repeated rows.`

### R2. Announce your own next action as a full sentence.

Name yourself as the actor and name the object you will act on. Never use a
bare verb phrase, a headline, or a present participle.

- Not acceptable: `Now checking the scan.` / `Running tests.` / `Next: fix.`
- Acceptable: `I will now read the scan progress file.`

Short connective fragments are where this failure concentrates. Ban the
fragment register outright. Do not try to write a better fragment.

### R3. A demonstrative points only inside its own sentence.

A demonstrative word (`this`, `that`, `these`, `它`, `这个`) may point only to
a noun written in the **same sentence**. To point at something in an earlier
sentence, repeat the noun and mark the reference explicitly (`the two tasks
listed above`, `上述两个任务`).

The forbidden thing is a bare demonstrative reaching backwards across a
sentence boundary. A demonstrative that sits next to the noun it points at is
correct writing.

### R4. Give every identifier a category word.

Every proper noun, file name, command-line flag, table name, function name and
bare token gets a category word right after the token.

- Not acceptable: `ivy and joseph are queued`
- Acceptable: `the tasks for the two names ivy and joseph are queued`
- Not acceptable: `pass --links`
- Acceptable: `pass the --links command-line flag`

### R5. One thing, one name.

Choose one term for each thing at the start of the reply. Use that one term
every time. Never switch to a synonym, an abbreviation, or the English or
Chinese counterpart of the same term.

### R6. Write plain existing words.

Do not invent a word. Do not use a metaphor, an analogy, a pun, or a nickname
for a technical thing. If a plain description exists, write the plain
description.

### R7. Active voice, one actor per clause.

Write the actor before the verb. If one clause contains two different actors,
split the clause into two clauses and name both actors.

- Not acceptable: `After the edit the density did not move.` (two actors: you
  made the edit, the model produced the density, and neither is named)
- Acceptable: `I edited the prompt. The model then produced the same density
  value as before.`

### R8. Do not use compressed colloquial speech.

Spoken shorthand hides the action and the object. Write the literal
description instead. `wrapped up`, `good to go`, `nailed it`, `没轮到`,
`搞定`, `打通` all hide what happened.

### R9. Keep sentences and paragraphs short.

The caps differ by language, so read the caps in the language file. The
cross-language part is the method: when a sentence passes the cap, split the
sentence at a clause boundary and give the new sentence its own actor. Never
shorten a sentence by deleting a slot required by R1.

## 4. The pre-send check

Do these steps as edits on the draft. Do not read the draft and judge whether
the draft "reads well". A judgement drifts. A step list does not.

1. Load the language file for the language of the draft.
2. **Actors.** Find every sentence. For each sentence, point at the word that
   names the actor. If no such word exists, write the actor in.
3. **Arguments.** Find every verb. Ask the verb: did what, to what, with what,
   where, and with what result. Write in every answer that the draft does not
   already contain.
4. **Demonstratives.** Find every demonstrative word. Check that the noun it
   points at is in the same sentence. If the noun is not, repeat the noun and
   add the explicit backward marker.
5. **Identifiers.** Find every bare token, file name, flag and proper noun. Add
   the category word.
6. **Terms.** List every term that names a thing. If one thing carries two
   terms, replace all of them with one term.
7. **Announcements.** Find every fragment that announces your next action.
   Rewrite each fragment as a full sentence with you as the actor.
8. **Invented language.** Find every metaphor, pun, nickname and invented word.
   Replace each one with the plain word.
9. **Length.** Measure the longest sentence and the longest paragraph. Split
   anything over the cap in the language file.
10. **Language-specific steps.** Run the extra steps at the end of the language
    file.

If the user tells you that a reply was hard to understand, run steps 2 to 10
again on that reply. Do not explain yourself and do not apologise. Send the
rewritten text.

## 5. Why a check and not a quality

Action constraints persist across a long session. Style constraints do not.
In the session that produced this skill, rules such as "never commit unless
asked" held for hours, while the writing rules in the same file drifted back
to the model's default voice within one or two turns.

No hook can rewrite prose, so the user cannot enforce these rules from
outside. The only thing that survives is a short list of steps with a
countable result. `Find every verb and name its object` is checkable.
`Write clearly` is not.

## 6. Acceptance cases

`lang/zh/ACCEPTANCE-CASES.md` holds the user's four hand-written corrections
for Chinese. Those four corrections are the canonical acceptance cases. When
you change this skill, check the changed skill against those four cases first.
