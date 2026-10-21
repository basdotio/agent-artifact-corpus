# Saved profile

Facts confirmed for one job hold for the next, so a saved profile turns the next run into a few questions instead of a full interview. Read at setup when a profile exists, and at delivery.

## Saving

At delivery, offer once: "Save what you told me (your resume, your own words and the facts you confirmed) on this computer, so your next job needs fewer questions? It stays in [path], goes nowhere else, and you can delete the folder any time."

- Only on a yes, copy `candidate.md`, `own_words.md`, `signoff.md`, `not_true.md` and `standins.md` to `~/.resume-tribunal/`, or a folder the user names.
- On later runs, update it: a newer resume replaces `candidate.md`, this run's entries are added to the other files under the date, and new stand-ins are added to `standins.md`.
- A newer answer about the same claim replaces the older one in both files ("I now use Tableau" removes "I have not used Tableau" from `not_true.md`).
- "I confirm everything in my original resume is true as written" covers only the resume it was said about. When a newer resume replaces `candidate.md`, remove that line and ask again at the sign-off.

## Using it

At setup, if `~/.resume-tribunal/` or a folder the user names exists:

1. Pass it to `prompt.py setup --profile`, which copies it into `.tribunal/` and keeps its stand-ins.
2. Say so: "Using your saved facts from [date]."
3. A resume the user also gives replaces the saved one for this run.
4. Add what they say is new since then to `own_words.md` under the date.

## Without lasting files

Most chat apps keep no files between chats. At delivery, offer the same content as one block titled "My resume facts, saved [date]", with personal details restored, for the user to keep and paste with their next job posting. Treat a pasted block the same way as a saved folder, applying stand-ins first.
