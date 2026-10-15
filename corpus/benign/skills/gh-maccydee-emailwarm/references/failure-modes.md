# Failure modes worth knowing before you automate this

Every entry here produced a wrong answer or a lost day in practice.

## A tool reporting a send it did not make

The worst outcome available, because it corrupts the only evidence you have. Three separate
causes in one project:

| Cause | Symptom | Fix |
|---|---|---|
| Wrong send shortcut for the platform (`Ctrl+Enter` vs `Cmd+Enter` on macOS) | three "sends" reported, all three still in Drafts | click the actual Send control, then confirm in Sent |
| Reading `innerText` to verify a compose window | subject and From read as empty on a perfectly correct draft | read input values (`input_value()`), not rendered text |
| A same-document navigation to the Sent view | the old view kept rendering, so confirmation read the wrong rows | confirm on a fresh page |

Always confirm from the Sent folder. Treat the send step's own success report as a claim,
not evidence.

## Sign-in checks that lie

A cookie-presence check is a cheap pre-filter, not proof. Cookies survive session expiry, so
a check printed "already signed in" while the mailbox redirected to a full sign-in form. The
only honest test is navigating to the mailbox and reading the final URL. Cached status files
are worse again: check live.

## Sending as the wrong identity

The domain that earns the reputation is the one in the `From:` address, not the account you
are signed in as, and when a mailbox sends as an alias those are deliberately different.
Confirm the `From:` value in the compose window before every send. If the alias is missing
from the dropdown, that is a blocker to report, not a reason to send from the brand domain.

Account index URLs (`/mail/u/0/`, `/u/2/`) are an index into signed-in accounts and they
move. Hardcoding one eventually sends from somebody's personal mailbox. Open the mailbox and
read the account, then read the From address separately.

## Clipboard and compose traps

Type into compose fields rather than pasting: a stale clipboard has inserted unrelated text
into a compose window more than once, and at outreach time that goes to a stranger. Recipient
autocomplete overlays the subject field, so commit the address to a chip before typing the
subject. Screenshot and check the draft before sending.

## Browser profile locks

A browser automation profile killed rather than closed leaves a singleton lock that blocks
every later run. Clear it only after confirming no live process holds the profile, because
deleting a live lock corrupts the session the profile exists to hold. Note that a process
search for the profile path matches the search command itself.

## Pausing a scheduled job from inside that job

If the warm-up task is itself the scheduled job, disable future runs rather than tearing the
job down, or you kill the process mid-write and lose the log entry and the alert that justify
the pause. Leave the schedule definition in place so it is one command to resume.

## Reporting into a file nobody reads

Nine consecutive blocked runs were recorded in a log that nobody opened. The blocker was a
twenty-second job for the owner. When a run is blocked on a human, tell that human through a
channel they actually read.
