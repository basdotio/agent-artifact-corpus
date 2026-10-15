# Pronunciation

The pronunciation list teaches the voice how to say names, acronyms and abbreviations. Each word you add is used
for every script in that language from then on. Your script and subtitles keep the original spelling: only what
the voice reads changes.

Open it from the menu button at the top right (the sliders icon, next to **?**) → **Pronunciation**, or from the **Pronunciation** link under *Output and pauses*
on the Create page.

## Add a word

1. **Written** — the word as it appears in your scripts, for example `CJNG`.
2. **Say it as** — spelled the way it sounds in that language, for example `ce jota ene ge`.
3. **Language** — the language it applies to, or *Every language*.
4. **Only with these capitals** — tick it when the capitals matter. It keeps `US` (the country) from also changing
   the word `us`.
5. Click **Hear it** to hear it in your default voice, then **Add**.

Examples:

| Written | Say it as | Language |
|---|---|---|
| CJNG | ce jota ene ge | Spanish |
| EE.UU. | Estados Unidos | Spanish |
| Dr. | Doctor | English |
| NASA | nasa | Spanish |
| Nguyen | win | English |

Longer entries win over shorter ones, so `EE.UU.` is used before `EE.` if you have both.

## Try a sentence

Type or paste a sentence in **Try a sentence** and pick its language: below it you see exactly what the voice will
read, with your list and *numbers as words* applied. Use it to check a word before you make a whole voiceover.

## Your words

The list shows every word, with its language and whether capitals matter.

- **Search** — find a word.
- **Hear** — hear how it's said.
- **Edit** — change it.
- **Delete** (bin icon) — remove it.

## Import and export

Keep your list in a spreadsheet, share it between PCs, or start from a ready-made one.

**Export:** click **Export**, choose **CSV** (opens in Excel and Google Sheets, accents included) or **JSON**, and
all languages or one. Words set to *Every language* are included in every language's export.

**Import:** click **Import** and choose a file:

- **CSV** — columns `written`, `said`, `language`, `exact_capitals`. Spanish column names work too (`escrito`,
  `dicho`, `idioma`, `mayúsculas`), and the file can use commas or semicolons.
- **JSON** — a file exported from the app.
- **TXT** — one word per line, like `CJNG = ce jota ene ge`.

**Language for rows that don't say** sets the language of rows without one. Leave **Update words that are
already in the dictionary** ticked to replace their pronunciation with the file's. If some lines can't be read, the
good ones are still imported and the app lists the problem lines so you can fix them.

Example CSV:

```
written,said,language,exact_capitals
CJNG,ce jota ene ge,es,yes
EE.UU.,Estados Unidos,es,yes
Dr.,Doctor,en,yes
```

### Ready-made lists

The app's GitHub page has two lists to start from, with common abbreviations and titles:

- [English list](https://github.com/hassanxs/fatima-voice-studio/blob/main/dictionaries/pronunciation-english.csv)
  (Mr., Ms., Prof., Jr., and more)
- [Spanish list](https://github.com/hassanxs/fatima-voice-studio/blob/main/dictionaries/pronunciation-spanish.csv)
  (Sr., Srta., Dra., Ud., EE.UU., and more)

Open the list, click the **Download raw file** button, and import it.

## Numbers

Numbers are handled separately, by **Say numbers as words** (on by default): see
[Writing scripts](writing-scripts.md#numbers-money-dates). You only need the pronunciation list for numbers you want
read in a special way.

## Next

- [Writing scripts for the voice](writing-scripts.md)
- [Batches and fixing parts](batches.md): *Re-run* a batch to hear it with your new words.
