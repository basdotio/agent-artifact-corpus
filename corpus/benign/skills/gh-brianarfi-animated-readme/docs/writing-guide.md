# Writing guide

A visitor gives a README about ten seconds. In that time they need to know what it is, whether it
is for them, and what it looks like working. Everything below serves those three questions.

## The order

1. **Headline.** One line about the outcome for the user, in their words. Not the technology.
   - Good: "Your PM admin, done before you open Slack."
   - Weak: "An AI-powered productivity framework for knowledge workers."
2. **One or two sentences** on what it does and the one promise that makes it safe or easy to try.
3. **Hero GIF.**
4. **Sound familiar?** Three to six moments the user already lives through. Concrete: a time, a
   place, a tool, a person. "The status update is due at ten" beats "reporting is time-consuming".
5. **Who it is for, and who it is not for.** Saying who should not use it builds trust.
6. **Before and after** GIF, or a two-column table.
7. **How it works** GIF, then three or four numbered steps in text.
8. **Quick start.** The shortest path to seeing it work. Commands in a code block.
9. **Everything else**: configuration, documentation links, licence.

## The voice

- Write the way a colleague would explain it over coffee. Short sentences. Contractions are fine.
- Second person: "you", "your week". Not "users" or "one".
- Concrete beats clever. Numbers, names, times and file names beat adjectives.
- One idea per sentence. If a sentence has two "and"s, split it.
- No slogans built as contrasts ("X, not Y") or as threes ("fast, simple, powerful"), unless the
  three things are real and different.
- No aphorisms ("the best tool is the one you use"). Say the specific thing.

## Words to cut

seamless, effortless, unlock, supercharge, revolutionize, leverage, empower, robust, powerful,
cutting-edge, next-generation, game-changer, delve, elevate, streamline, harness (as a verb),
"in today's fast-paced world", "whether you're X or Y", "look no further", "it's worth noting",
and every em-dash. Use a comma, a colon or a full stop.

## Scenes

- **Hero:** the prompt the user would type, three or four work lines, and a result card with
  what they get. Use `**word**` in the title to highlight the key phrase.
- **Before and after:** each "before" card is one real, specific frustration. Each "after" row
  answers one of them. Keep "after" rows under 60 characters so they stay on two lines.
- **How it works:** three or four steps, each with up to three short items. Mark the step where
  the user gets the result with `"highlight": true`. Use backticks for file names and commands.

## Alt text

Describe what happens in the order it happens, including the words on screen that matter:

> Animated. A terminal types "Make an animated README for this repo.", reads the project, and
> renders three GIFs. A card lands: README ready for review, with two claims flagged.

Not: "demo.gif", "screenshot", "animation showing the tool".
