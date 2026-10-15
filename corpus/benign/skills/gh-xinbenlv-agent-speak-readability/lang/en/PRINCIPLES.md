# Additional rules for English output

Apply the nine cross-language rules in `../../SKILL.md` first. Then apply the
eight rules below. Then run the extra check steps at the end of this file.

The base standard for English is ASD-STE100 Simplified Technical English.
This file states the parts of ASD-STE100 that matter most for agent output.

## E1. One word, one meaning, one part of speech

Choose one meaning for each word and keep that meaning for the whole reply.
Do not use a noun as a verb. Do not use a verb as a noun.

- Not acceptable: `I will action the request.`
- Acceptable: `I will start the request.`
- Not acceptable: `The run failed, so I did another run.`
- Acceptable: `The test run failed, so I started a second test run.`

## E2. Use the imperative for procedure steps. Keep each step to 20 words or fewer

Write one action in each step. Put the action verb at the start of the step.

- Acceptable: `Open the configuration file. Set the timeout field to 30 seconds.`

## E3. Keep descriptive sentences to 25 words or fewer

Measure the longest sentence. Split any sentence that is longer than 25 words.
Split the sentence at a clause boundary and give the new sentence its own
subject. Never shorten a sentence by removing an argument of the verb.

## E4. Do not use semicolons

Write two sentences instead of one sentence with a semicolon. Colons are
acceptable before a list.

## E5. Do not use contractions

Write `do not`, `it is`, `cannot` and `will not`. Do not write `don't`,
`it's`, `can't` and `won't`.

## E6. The English failure mode is the dropped object, not the dropped subject

English is not a pro-drop language, so English output rarely loses the subject.
English output loses the **object** of the verb and the **antecedent** of a
pronoun. Watch those two failures.

- Not acceptable: `Verified.`
- Not acceptable: `The script verified this.`
- Acceptable: `The verification script confirmed that the deduplication logic
  drops repeated rows.`

Treat a bare `this`, `that`, `it` or `the above` with no noun after it as an
error. Write the noun.

- Not acceptable: `This means the import is safe.`
- Acceptable: `This return code means the import is safe.`

## E7. Announce your own next action as `I will <verb> <the object>.`

Do not use a present participle, a headline, a colon list, or a bare verb.

- Not acceptable: `Now checking the scan.`
- Not acceptable: `Running the two tasks.`
- Not acceptable: `Next: the scan.`
- Acceptable: `I will now run the two tasks listed above.`

## E8. Articles are not optional

A dropped article produces telegraphic register. Telegraphic register is the
English counterpart of a dropped Chinese measure word.

- Not acceptable: `Run scan script and check output.`
- Acceptable: `I will run the scan script and read the output file.`

## E9. Extra check steps for English

Run the ten steps in section 4 of `../../SKILL.md` first. Then run these six
steps.

1. Find every verb. Name the object of the verb. Write the object in if the
   draft does not state the object.
2. Find every `this`, `that`, `it`, `these` and `those`. Write the noun after
   the word, or replace the word with the noun.
3. Find every sentence with no article before a countable noun. Add the article.
4. Find every present participle that opens a sentence. Rewrite the sentence
   with an explicit subject and a finite verb.
5. Count the words in the longest sentence. Split the sentence if the count is
   over 25 words, or over 20 words for a procedure step.
6. Delete every semicolon and every contraction.
