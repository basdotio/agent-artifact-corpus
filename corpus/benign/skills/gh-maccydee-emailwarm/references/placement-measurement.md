# Measuring inbox placement

The question is always "which folder was this message **delivered** to", recorded at the
time, before anything moves it. Everything below serves that.

## The rule that matters most

Record placement at delivery, then rescue. A folder check made later cannot distinguish a
message that landed in the Inbox from one that landed in Junk and was moved by hand. In the
source project a warm-up was declared finished on exactly that mistake: every test message
was sitting in the Inbox, because earlier runs had rescued them all, and the gate it was
scored against explicitly required *unassisted* landings.

If you cannot be certain a message was unassisted, it does not count towards the gate.

## Microsoft (Graph / Outlook)

Use the per-folder endpoint, not the all-folders list.

```
list-mail-folder-messages
  mailFolderId: <the Junk Email folder id>
  filter: from/emailAddress/address eq 'sender@sending-domain'
  select: id,subject,receivedDateTime
```

- The all-folders `list-mail-messages` endpoint **ignores a `mailFolder` parameter** in some
  versions and returns everything. A call scoped to "junkemail" came back spanning Inbox,
  Junk, Deleted Items and Sent Items, while reporting itself as a junk check.
- KQL `search` excludes Junk and Deleted Items, so a `from:` search silently omits the
  messages a placement check exists to find. Use `filter`, not `search`.
- The same filter against the all-folders endpoint can fail with `InefficientFilter`. Run it
  per folder.
- Check Deleted Items as well as Junk. Delivered is not the same as still there, and a
  message that was delivered to the Inbox and then deleted stops earning you anything.
- Microsoft's own headers settle it: `dest:J` means Junk, `dest:I` means Inbox, and `RF:`
  names the rule. `SCL` is the spam confidence level. Read them when you have the raw
  message.

## Google

Gmail has no per-folder API that maps cleanly onto Junk, so search by label instead:
`in:spam from:sender@sending-domain` and `in:inbox from:...`, and note that Gmail's category
tabs (Promotions, Updates) are not spam but are not the primary inbox either. If your
recipients are Workspace users, the admin Email Log Search reports final delivery disposition
directly and is the better source.

## Yahoo and AOL

AOL runs on Yahoo's stack, so warming one warms the other, and neither tells you anything
about Google or Microsoft. There is no usable API for a personal mailbox, so placement is
read in the web client. Automate it the way you would a browser, and confirm the account is
actually signed in by navigating to the mailbox and reading the final URL rather than
trusting a cookie check.

## Recording it

One field, recorded per run: the folder the measured message was delivered to, and the
provider it was measured at. Gate progress is computed from that field alone, so protect it:
a run that could not measure records "unknown" rather than guessing, and "unknown" never
counts towards the gate.
