# Stage 5: the product page's texts, in the source language

Everything the store shows in words, settled with the owner in the source language before any translation. One file,
`store/listing/<source>.json` (`SKILL_DIR/tools/listing.py` describes its fields and checks the limits), plus the test
information and the facts App Store Connect asks for, which go into `store/CONNECT.md` (`app-store-connect.md`).

Work field by field, in this order; propose two or three variants of the short ones and say which you would pick.

## Name and subtitle (30 each)

The name is the app's name; add a few words to it only if the owner wants that and the name alone is taken or says
nothing. The subtitle says what the app does for the person, in the person's words, not what it is. Both are searched,
so the subtitle's words are spent keywords: choose them knowing that.

## Promotional text (170)

The problem in the customer's own words, then what the app does about it. It is the one text that can change without
a new version, so it can carry what is current; start with the evergreen one.

## Keywords (100)

Comma-separated, no spaces after the commas, singular or plural as people type them. The store searches the name, the
subtitle and this field, and nothing in the description. So:

- no word that is already in the name or the subtitle (`listing.py` refuses it), no word twice, no competitor's name,
  no "app" or "free";
- words a person types when they have the problem, not words the team uses for the solution;
- a word that would bring the wrong people (a neighbouring category the app is not) costs more than it earns.

You have no search-volume data. Say so; the choice is an editor's judgement, and the owner may know their market
better than you.

## Description (4000)

One item per line in the file; `""` is an empty line; a line that starts with "• " is a point. A shape that works:

1. What it is not, then what it is, in two or three sentences. The first two lines are all that shows before "more".
2. A heading in capitals, then how it works and why that is unlike the others.
3. Four or five points: one feature each, said as what the person does.
4. A heading, then who it is for: people named, never a promise to fix them.
5. One last line: what the app is not (medical, financial, legal, whichever applies), and what it takes off the
   person's hands.

Rules:

- Where the description quotes what the app says (a button, an answer), it quotes the app's text to the letter, in
  quotation marks; list those keys in `listing.quotedKeys` so every language is checked against its own app.
- **True about data.** What the description says about accounts, tracking and what leaves the phone has to match the
  privacy manifest, the privacy policy and the answers given in App Privacy, for every SDK in the build.
- No claim about health, money or the law that the app cannot stand behind: say who it is for, not what it cures.
- No prices, no "new", no mention of other platforms, no praise of itself.
- The project's own tone rules apply; put characters it never uses (an emoji, say) into `forbid`.
- `listing.mustMention` in the configuration lists the fields that have to contain the app's name (`app`). Empty it
  when the name is written differently in some language's store.

## Test information (if the app goes through TestFlight)

- **Beta App Description**: what the app is in one paragraph, how to get started in one, and anything a tester
  should know before installing.
- **What to Test**: three or four numbered things the owner most wants to learn, and where to send remarks.
- **Review notes** (for Apple's reviewer, in English): there is or is not an account; what the first launch asks; the
  steps to reach the main screen; anything that looks unusual and is deliberate.
- Feedback e-mail. The contact person's details and any sign-in details for the reviewer are typed into App Store
  Connect by the owner and are never written into a file.

Write the texts into `store/CONNECT.md` under "Test information", the tester-facing ones in the language of the
testers. They are entered in that one language; if the owner wants them in others, each goes through that language's
translator and auditor like any other text (`languages.md`).

## The facts

Ask once, in one message, and record the answers in `store/CONNECT.md`: support address and e-mail, marketing address,
privacy policy address (these pages have to exist and load before anything is submitted; a dead support link is a
rejection), copyright line, primary and secondary category, age-rating answers, price and the countries, whether the
app should be offered on Macs with Apple silicon and on Apple Vision Pro, and what the app collects (for App Privacy).

## Check and approval

`python3 SKILL_DIR/tools/listing.py` must print no problem; it then writes `store/LISTING.md`, the page everything is copied
from. Show the owner that page. On their yes: record it. Only now is the source language complete, and stage 6 may
start.
