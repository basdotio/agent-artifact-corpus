# Writing scripts for the voice

The voice reads exactly what you write, so a little care in the script gives a much better voiceover. Your
subtitles always use your script's exact words.

## Paragraphs and pauses

- **A blank line** starts a new paragraph, with a pause of 0.7 seconds (change it under *Output and pauses* on the
  Create page, or in [Settings](settings.md)).
- **`[pause]`** anywhere adds a 1-second pause.
- **`[pause 2.5s]`** adds a pause of the length you choose.
- **Punctuation** gives the natural, short pauses: commas, full stops, question marks. If a sentence runs on, add
  a comma or split it into two.

```
The ship left port at dawn.

Nobody on board knew it would never come back. [pause 1.5s]

Or did they?
```

Pause tags aren't read aloud and don't appear in the subtitles.

## Long scripts are spoken in parts

A long script is spoken in **parts** of up to about 40 seconds (600 characters; 300 with S2 Pro), split at the end of
a sentence.
Every part uses the same voice, and the parts are joined with exact pauses, so you hear one smooth
voiceover. Parts make long scripts reliable, and if one part comes out wrong you redo just that part (see
[Batches and fixing parts](batches.md#fixing-one-part)).

A script can be as long as you like (up to about 4 hours), and a batch can hold up to 500 scripts.

## Numbers, money, dates

With **Say numbers as words** on (it is by default), the app writes numbers out before the voice reads them:

| You write | The voice reads |
|---|---|
| In 1913 | In nineteen thirteen |
| They paid $5M. | They paid five million dollars. |
| 35% of them | thirty-five percent of them |
| At 5:30 | At five thirty |
| the 3rd time | the third time |
| En 1913 | En mil novecientos trece |
| Ofreció $5 millones | Ofreció cinco millones de dólares |
| El 35% | El treinta y cinco por ciento |
| A las 5:30 | A las cinco y media |
| el 3.º lugar | el tercer lugar |

This works in English, Spanish, French, German, Italian and Portuguese. In the other languages, numbers stay as
digits and the voice reads them itself.

**Check before you make it:** under *Output and pauses*, click **See what the voice will read**.

## Names, acronyms and abbreviations

If the voice says a name or an abbreviation wrong, don't change your script: add the word once to your
[pronunciation list](pronunciation.md), spelled the way it sounds (`CJNG` → *ce jota ene ge*,
`EE.UU.` → *Estados Unidos*). It's used for every script in that language from then on, and your script and
subtitles keep the original spelling.

To fix a word in just one place, edit that part instead (see
[Batches and fixing parts](batches.md#fixing-one-part)).

## Emotion tags (S2 Pro)

With **Fish Audio S2 Pro** you can tell the voice how to say something with a tag in square brackets, right before
the words:

```
[whisper] Deep beneath the ice, something was waiting.
[excited] And then the drill broke through! [sad] But nobody was ready for what came next.
```

Common tags: `[whisper]`, `[excited]`, `[sad]`, `[angry]`, `[surprised]`, `[low voice]`, `[laughing]`, `[sigh]`,
`[pause]`, `[emphasis]`, `[professional broadcast tone]`. Any short description works, up to 60 characters. How
strongly a tag is followed varies; try a **New take** if one doesn't land.

![A quick take with S2 Pro: the tags in the text, and the tag hint under the Voice model list](images/create-s2.webp)

- Tags are never read aloud or shown in the subtitles.
- `[pause 2]` stays the app's own pause (see above), with any model.
- **Qwen3-TTS** doesn't follow tags: it skips any words in square brackets.

## Tips for a natural read

- **Pick the right language.** The **Language** must be the language of the text; a Spanish script read with
  *English* selected sounds wrong.
- **Write for the ear.** Short sentences read better than long ones with many clauses.
- **Avoid symbols** the voice can't say well (`&`, `/`, `#`, emoji). Write *and*, *or*, *number*.
- **Spell out unusual abbreviations** or add them to your pronunciation list.
- **One take not quite right?** A **New take** on a part reads it again differently; often the second one is
  better.

## Next

- [Making voiceovers](making-voiceovers.md)
- [Pronunciation](pronunciation.md)
