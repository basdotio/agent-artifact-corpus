---
name: emailwarm
description: >-
  Set up and run an email domain warm-up hands-on: audit the domain's SPF, DKIM and DMARC,
  fix the records at the user's registrar in their own logged-in browser, collect warm-up
  mailboxes across different providers, then send and reply on a daily cadence, measuring
  inbox placement until the domain is safe to send real outreach from. Use this whenever
  someone says they have a new domain to warm, asks why their email lands in junk or spam,
  mentions warming a domain or mailbox, is setting up SPF/DKIM/DMARC for sending, asks
  whether a domain is ready for cold outreach, or invokes /emailwarm. Trigger it on
  "warm my domain", "my emails go to spam", "new sending domain", "deliverability",
  or "inbox placement", even when they name no tooling.
---

# emailwarm

Take a domain from "just registered" to "safe to send from", doing the work rather than
describing it. The user supplies the domain and their logins; you audit DNS, fix records in
their registrar, wire up the mailboxes, and run the daily cadence.

Two things are worth knowing before you start, because they shape every decision here:

**Authentication is not reputation.** Perfect SPF, DKIM and DMARC will not put you in the
inbox. In the run this is built from, the first two messages passed all three with full
alignment: one went to Junk, the other was dropped entirely. Get the records right because
failing them loses you the inbox, then earn the reputation separately.

**Reputation comes from observed behaviour**, strongest first: a human replying, someone
rescuing a message from spam, opens, consistency, and the absence of complaints. A steady
trickle looks like a person; silence then a burst looks like a list. That is what the
cadence is imitating, and why it takes a fortnight rather than an afternoon.

## Step 1 - Ask for what you need, once

Collect these up front so the run is not stop-start:

- **The domain** to warm.
- **What they intend to send from it - and ask this every time, without exception.**
  `dns_check.py` probes the domain and says whether it serves a live website, so you do not
  have to remember: when it does, the domain is a brand asset and the question is not
  optional. Normal business mail means this is the right domain and the record fixes are the
  whole job. Cold outreach means it should go from a separate, disposable sending domain
  instead - a blacklisted sending domain costs a registration to replace, while blacklisting
  the brand domain takes the site's mail and every published contact route with it. Thirty
  seconds of pushback here has saved people the asset they cannot buy back.
- **The registrar** (GoDaddy, Namecheap, Cloudflare, 123-reg, IONOS, Squarespace).
- **Where the mailbox lives**, if anywhere yet (Google Workspace, Microsoft 365, other).
- **Warm-up mailboxes they control**, ideally two or more providers. See step 4.
- **What they eventually want to send**, in messages a day, so the ramp has a target.
- **When their machine is actually on and awake**, if the cadence will run there. This gets
  forgotten and it quietly breaks the ramp: a laptop that is shut at 09:00 simply misses the
  run, and consistency is the thing being built. Ask for a window they are confident about
  rather than a single time, and pick a slot inside it.

**Windows:** use `python` or `py -3` wherever these examples say `python3`, and give the
scheduled job the full path to `python.exe` - `python` on PATH is often the Microsoft Store
stub, which opens the Store instead of running anything. Everything else works as written:
the DNS audit falls back to DNS-over-HTTPS when `dig` is missing, and the browser scripts use
Windows process tools rather than `pgrep`.

## Step 2 - Audit the DNS before touching anything

```
python3 scripts/dns_check.py <domain>
python3 scripts/dns_check.py <domain> --selector <from the provider console>
```

It uses `dig` where that exists and DNS-over-HTTPS where it does not, so Windows needs
nothing installed. If no resolver answers at all it says so and exits non-zero rather than
printing a report full of MISSING, which would read as a badly configured domain when the
real problem is the machine.

It reports SPF, DKIM, DMARC and MX, names the mail provider, and separates what must be
fixed from what is worth changing. Run it first so you arrive at the registrar knowing
exactly which records are wrong, and again afterwards to prove the edit landed.

What the fixes look like, on the **sending** domain:

```
; one SPF record only - two is a permerror and fails every check
@                      TXT   "v=spf1 include:<provider> -all"
; DKIM - selector and key come from the mail provider's console, not from DNS
<selector>._domainkey  TXT   "v=DKIM1; k=rsa; p=<PUBLIC-KEY>"
; DMARC - start at none, tighten later
_dmarc                 TXT   "v=DMARC1; p=none; rua=mailto:dmarc@<domain>; fo=1"
```

Prefer `-all` over `~all`: a soft fail invites spoofing of a domain whose whole job is to be
trusted by strangers. Tighten DMARC on a schedule rather than in one go - `p=none` for a
week or two while reports come in, then `quarantine` with a low `pct`, then `reject`. Going
straight to `reject` before reading a single report is how legitimate mail disappears.

## Step 3 - Fix the records at the registrar, in their browser

Use the browser tools against the user's own signed-in Chrome, because that is where their
registrar session already lives.

0. **Check where the DNS is actually served before opening anything.** `dns_check.py` prints
   the DNS host from the nameservers. A domain is very often registered in one place and
   served from another - registered at GoDaddy while the nameservers point at Cloudflare is
   a common shape - and an edit made at the registrar in that case changes nothing, because
   nobody is serving that zone. Go where the nameservers point.
1. Open the DNS page for the domain. `references/registrars.md` has the direct
   paths and the per-registrar traps worth knowing (GoDaddy's `@` host, Cloudflare's proxy
   toggle, 123-reg splitting TXT across screens).
2. **If they are not signed in, ask them to sign in, and wait.** Never type a password,
   a one-time code or a recovery answer, and never accept or dismiss a two-factor prompt on
   their behalf. Say where you have stopped and what you need.
3. Make the edits one record at a time, reading back each saved value before moving on. A
   registrar that silently appends the domain to a host field, or splits a long DKIM key, is
   common enough that reading back is not paranoia.
4. Re-run `dns_check.py`. DNS caches, so if a change does not show, wait for the TTL and
   check again rather than editing twice.
5. Send one message to a mailbox they control and read `Authentication-Results` in the
   headers: SPF, DKIM and DMARC should each say `pass`, and each should align to the `From:`
   domain. Alignment fails silently when a mailbox sends as an alias on a second domain, and
   a record that merely exists proves nothing.

## Step 4 - Set up the mailboxes: the one that sends, and the ones that receive

Two different jobs, and both need a signed-in session in the warm-up profile.

**The sending mailbox** is the account that will send as the new domain. Often it is not a
mailbox on that domain at all: a common and perfectly good setup is one mailbox on the brand
domain sending as an alias on the sending domain, which costs nothing extra at most
providers. Whatever the shape, seed this one first, because without it there is no cadence
at all.

**While you are signed in to it, open a compose window and check the sending address is
actually offered in the From dropdown.** If the alias has not propagated or was never added,
that is a twenty-second job for the user and a blocker for every run until it is done.
Finding it now beats finding it at 09:00 tomorrow when the first scheduled run logs blocked.

**The receiving mailboxes** are what the sending mailbox writes to, and every one of them
gets warmed: replied to, and anything of yours in junk dragged back to the inbox. **Use as
many as the user already has.** Two is enough to start, four is better, and the honest line
is that more mailboxes and more providers give the domain more chances to be seen behaving
normally. Nobody should be signing up for accounts they will never use.

Ask for one at **each provider they will eventually email**, by name rather than in
the abstract: "a Gmail address, an Outlook or Hotmail address, and a Yahoo or AOL one" gets
a useful answer where "some test mailboxes" does not. The script knows `gmail`, `outlook`
(Hotmail and Live), `office365`, `yahoo`, `aol`, `icloud`, `proton`, `zoho`, `fastmail` and
`gmx`, and takes any other mailbox as a URL.

There are four reputation systems that matter, and warming one teaches you nothing about the
others: **Google**, **Microsoft**, **Yahoo** (which also runs AOL) and **Apple**. Each judges
your domain only on what IT sees - mail into its own mailboxes, and the replies and rescues
that happen there - so effort spent at one does not carry to another.

**Start where the real recipients are, and cover it properly, rather than spreading thin.**
Two mailboxes at the provider that matters is worth more than one each at four, because a
single mailbox at a provider has to both build the reputation and measure it, and it cannot
honestly do both (see step 6). Add another provider when enough recipients are there to
justify a second pair.

**A consumer address does not tell you which system it belongs to**, so check before
choosing. `sky.com` and `btinternet.com` are Yahoo, which is why an AOL or Yahoo mailbox is
what tests them. `hotmail.co.uk`, `live.com` and `msn.com` are Microsoft. `me.com` and
`mac.com` are Apple. `CONSUMER_STACKS` in `scripts/seed_login.py` has the mapping; if the
user can export or name the domains they will be emailing, count them and pick warm-up
mailboxes in that proportion rather than guessing.

A mailbox on the user's own business provider is worth having too, since mail between two
Google Workspace tenants is a different path from Gmail to Gmail.

**If they do not have an account at one of the providers, say the ideal and then let them
choose.** The wording that works is roughly: *"ideally create a free one there, since it is
the only way to see how your mail is treated by that provider - but if you would rather not,
we carry on without it."* A free mailbox takes a couple of minutes and covers a whole
reputation system, so it is usually worth the bother, and saying so is more useful than
quietly proceeding with a gap.

**Creating the account is theirs to do, not yours.** Never sign anyone up: it means handling
a password, and often a phone number and a captcha.

Be concrete about what is lost when they decline, because "best results" on its own means
nothing:

- **A provider with no mailbox produces no evidence at all.** You will not know whether mail
  to it lands, and you can only report on providers you actually sent to. Say which ones
  the run covers, rather than implying the domain is warm everywhere.
- **One mailbox is enough to measure a provider**, so declining a second is a much smaller
  loss than declining the provider entirely. If they will only do one extra, put it wherever
  most of their real recipients are.
- **Their own inbox counts.** Most people already hold a Gmail or Hotmail address they have
  forgotten about, and an old account with real history is better warming evidence than a
  freshly created one, which has no reputation of its own for filters to weigh.

For each: ask them to sign in to it in the browser, then confirm it yourself by loading the
mailbox and reading the final URL. A cookie check is a cheap pre-filter, not proof: in the
source project a sign-in check printed "already signed in" while the mailbox was redirecting
to a login form.

Warming against mailboxes the user controls is real but limited. It teaches filters that
mail from this domain gets read and replied to, which is genuinely what they measure, but it
cannot simulate a stranger choosing to reply. Encourage them to use the domain for ordinary
supplier and account email too, because that traffic is the strongest accelerant available.

## Step 4b - Seed the logins the scheduled run will use

This is the step that decides whether the cadence survives past the first day, and it is
easy to miss: **a scheduled run cannot use the user's normal browser.** It has no extension,
no desktop session and no way to answer a login prompt, so it drives its own Playwright
profile, and that profile needs the sessions in it.

```
python3 scripts/seed_login.py list
python3 scripts/seed_login.py seed gmail        # the SENDING mailbox first
python3 scripts/seed_login.py seed outlook      # then each receiving mailbox
python3 scripts/seed_login.py seed https://mail.example.com --name work
python3 scripts/seed_login.py check             # verifies every seeded mailbox
```

`seed` opens the mailbox in the warm-up profile and waits while the user signs in by hand.
Do not type the password, the one-time code or a security answer, and do not accept a
two-factor prompt for them - that is theirs, and the whole point of seeding is that they do
it once in a window you opened.

`check` decides signed-in status by loading the mailbox and reading the final URL, never by
looking for a cookie. Auth cookies outlive the session they belong to, so a cookie test
cheerfully reports a mailbox as signed in while it redirects to a login form. That exact
false positive let a warm-up log sends it had never made.

Sessions expire, usually in weeks rather than days. Run `check` at the start of every run.
If a mailbox is signed out, stop that leg and say so: a run that quietly skips a provider
leaves a hole in the record, and nobody notices until the placement figures make no sense.

## Step 4c - Schedule it

Once the mailboxes verify, offer to schedule the run rather than leaving it to be
remembered - the whole value of a ramp is that it is consistent. On macOS use a launchd
agent (weekday mornings), elsewhere cron. Two things worth getting right:

- **Schedule it inside the hours the machine is really on.** Mid-morning and mid-afternoon
  beat 06:00 on a laptop that gets opened at nine. If they use a desktop that is always on,
  anything goes; if it is a laptop that travels, expect missed days and say so now rather
  than treating the first gap as a fault.
- **Use the scheduler the machine actually has, and turn on catch-up.** The ramp is a shape,
  so a run skipped because the machine was off is the thing that breaks it.
  - **macOS: a launchd agent, not cron.** A `StartCalendarInterval` job whose time passed
    during sleep runs once on wake; a cron job asleep at the appointed minute never runs.
  - **Windows: Task Scheduler, not cron.** Create it with `schtasks` or the GUI, and tick
    **"Run task as soon as possible after a scheduled start is missed"** - without it,
    Windows behaves like cron and simply drops the run. `schtasks /Create /SC WEEKLY /D
    MON,TUE,WED,THU,FRI /TN emailwarm /TR "..." /ST 10:00` sets the weekday schedule; the
    catch-up flag is on the Settings tab, or `/Z /V1` era switches depending on version, so
    confirm it in the GUI rather than assuming.
  - **Linux: a systemd timer with `Persistent=true`**, which fires a missed run on next
    boot. Plain cron has no catch-up.
- **A missed day is not a reason to double up.** The log carries the run number, so the next
  run continues the ramp where it left off. Sending twice as much to catch up is the exact
  shape warming exists to avoid.
- **Give the job the same profile.** Set `EMAILWARM_PROFILE` in the job's environment if it
  is not the default, or the scheduled run will start from an empty profile and every
  mailbox will look signed out.
- **Name the model in the job** (see "Which model to run each part on", below): sonnet for
  the cadence, so a job
  that inherits whatever default is current does not drift up or down without anyone
  deciding to.
- **Scheduled jobs get a minimal PATH.** Use absolute paths to python and the scripts. A
  job that cannot find its interpreter fails silently and the ramp stalls for days before
  anyone looks. On Windows that means the full path to `python.exe`, since `python` on PATH
  is often the Microsoft Store stub that opens the Store instead of running anything.

## Which model to run each part on

These steps differ enormously in how much judgement they need, and the daily one repeats
forever, so it is worth matching them deliberately rather than running everything on the
most capable model available.

| Work | Model | Why |
|---|---|---|
| The daily cadence (steps in 5) | **sonnet** | The browser work is in `scripts/`, so the model orchestrates rather than clicking, but it still has to notice a compose window that came up wrong, a mailbox that quietly signed out, and the difference between delivered and delivered-then-rescued. Those judgements are what the placement record is built from, and getting them wrong is not recoverable by rerunning. |
| Setup: DNS audit, registrar edits, seeding, scheduling | **sonnet** | Done once or twice, and a wrong DNS edit breaks mail for the whole domain until someone notices. Reading a value back from a registrar that silently rewrote it is exactly the kind of care worth paying for here. |
| Diagnosis when placement will not move | **opus** | Genuinely hard and adversarial: DMARC alignment failing only for an alias, a provider treating one leg differently, a stop rule that fired for a reason nobody has spotted. A plausible wrong answer here costs weeks of warming. |

**Reliability beats the saving here, so do not drop the cadence below sonnet.** The daily run
is cheap because the browser work is deterministic, not because the model is small: each run
is a handful of tool calls and four sentences of prose. What it cannot afford is a log entry
claiming a send that did not happen, or a placement recorded from the wrong folder, because
the placement record is built from those entries, and a wrong one is invisible until the
warm-up ends on a false result.

**If a provider has no driver in `scripts/`, build one rather than leaning on the model to
click through the mailbox every run.** Writing it takes one session and then every later run
is deterministic. The procedure below produced the Outlook and AOL drivers, each in well under
an hour, including the mistakes.

Name the model explicitly in the scheduled job, since whatever the default is today will
change under you:

```
claude -p "/emailwarm run the daily cadence" --model claude-sonnet-5 \
  --output-format json --dangerously-skip-permissions
```

## Adding a driver for a provider that has none

Do this against the live mailbox, never from memory. Every guess made from memory in these
drivers was wrong: the Outlook compose control is "New email" and not "New mail", and a
contains-match on "From" hit the message list's "Sort message list by From" button.

1. **Open the signed-in mailbox and dump what is there.** List buttons and their aria-labels,
   then click compose and list every input, textarea and contenteditable with an aria-label
   or placeholder. That gives the real selectors in two passes.
2. **Copy the shape of `send_outlook` or `send_aol`.** Same order every time: confirm the URL
   is the mailbox, confirm the account is the one asked for, open compose, fill, verify, send,
   confirm in Sent.
3. **Expect these four, because every client has some of them.**
   - The recipient becomes a chip and the input clears. Outlook then shows only the contact
     NAME and keeps the address nowhere in the DOM; AOL keeps the real address in the row
     around the field. Check which, and if the address is gone, verify it from the Sent item
     instead.
   - A suggestion list or an interstitial covers the next field. Escape closes it; filling
     rather than clicking sidesteps the rest.
   - Closing popups by a generic "anything labelled Close" will close the compose window.
     Target the interstitial's own control only.
   - Reaching Sent by clicking the sidebar is unreliable. AOL exposes no element whose text
     is "Sent"; the folder URL works. Getting this wrong reports a sent message as a failure,
     which is worse than not checking at all.
4. **Prove it in three runs.** `--dry-run` composes and verifies without sending. Then one
   real send to a mailbox the user controls, which must come back `"sent": true` with the
   subject found in Sent. Then a deliberately wrong `--from-address`, which must refuse.
5. **Register it in `DRIVERS`** and say in the code whether it was tested against a live
   mailbox. Yahoo shares AOL's client and reuses that driver, and the code says it is
   untested, because a reader deserves to know which claims were checked.

   **If you reuse a driver across two providers, make the host follow the provider.** Yahoo
   pointed at AOL's URL for a day because the driver hardcoded it: asking for Yahoo signed
   into AOL and tried to send from there. Same client, different mailbox.
6. **Then ask if they fancy sending it upstream.** Once a driver passes its three checks it
   works for everyone else with that provider, and the next person gets it for free instead
   of rediscovering which button is called "New email" this year. Offer to open the pull
   request for them, keep it to one sentence, and drop it if they are not interested - they
   came here to warm a domain, not to maintain someone else's repo.

## Step 5 - Run the cadence

Weekdays only. A brand-new business domain sending steadily through the weekend is a pattern
more common in bulk senders than in people.

| Run | Sends per weekday |
|---|---|
| 1-3 | 2 |
| 4-7 | 4 |
| 8-14 | 6 |
| 15+ | 10 |

Never jump the ramp; the shape of the curve is the point, not the total. If the target is
higher than 10 a day, keep climbing at the same gradient rather than stepping to it. If a
day is missed, continue from where the log left off rather than doubling up.

Each run, in this order:

1. `python3 scripts/seed_login.py check` first: a signed-out mailbox means this run is
   blocked, not that its leg is skipped. Then `python3 scripts/warmup_log.py next --log
   <path>` for the run number and today's target.
2. **Rescue** anything from the domain sitting in Junk into the Inbox, and sweep Deleted
   Items too - a message delivered and then deleted stops counting as signal earned.
3. **Send** today's messages from the sending mailbox's seeded session, rotating
   recipients across the receiving ones, and confirming the From address is the
   sending domain before each send. Plain text only: no images, no links, no
   attachments, no unsubscribe footer. Vary the subject and body every time, because
   identical repeated messages are the bulk pattern you are trying not to resemble. Two to
   four ordinary sentences about real work, some ending in a question.
4. **Reply** from the receiving side to what arrives. Replies are the strongest positive
   signal a provider has, so this two-way traffic is the point rather than a nicety.
5. **Measure placement** on one message, before rescuing it, and record where it was
   delivered. See below.
6. `python3 scripts/warmup_log.py append --log <path> --sent N --replied N --rescued N
   --measured-to inbox|junk|promotions|missing --provider <name>`.

Offer to schedule this daily rather than leaving it to be remembered, and check `status`
each run so progress and the stop rule are evaluated rather than eyeballed.

### Before sending anything, check the From address

The domain that earns reputation is the one in the `From:` address, not the account signed
in, and when a mailbox sends as an alias those are deliberately different. Confirm the
`From:` value in the compose window every time. If the alias is missing, that is a blocker
to report, not a reason to send from the brand domain.

Type into compose fields rather than pasting - a stale clipboard has put unrelated text into
a compose window more than once - and confirm from the **Sent** folder that each message
actually left. `references/failure-modes.md` covers the three separate bugs that produced
"sent" messages still sitting in Drafts, and the other traps worth knowing before automating
a mailbox through a browser.

## Step 6 - Measure honestly, and know when to stop

**Record where a message was delivered, at the time it was delivered, before anything moves
it.** A folder check made later cannot tell an Inbox landing from a Junk landing that was
rescued by hand. A warm-up in the source project was declared finished on exactly that
mistake. `references/placement-measurement.md` has the per-provider methods, including which
API calls are genuinely folder-scoped and which only look it up.

**When it is done: two weeks of consistent sending across every mailbox they gave you.**
That is the finish line, and it is deliberately a simple one. Ten sending runs, roughly a
fortnight of weekdays, with each mailbox replying and pulling anything out of junk.

**Say what that buys, and do not oversell it.** Two weeks of steady, engaged sending is the
single best thing you can do for a new domain, and it measurably improves how providers
treat it. It is not a guarantee of inbox placement and nobody can honestly offer one: a
filter weighs the recipient's own history, the content, the links, the volume and a dozen
signals nobody outside the provider can see. The claim to make is "this improves your
chances", never "your mail will now land in the inbox".

**Record where messages land anyway, because it is the only feedback there is.**
`warmup_log.py status` reports the placement mix across the run. Read it as a trend rather
than a verdict:

- **Mostly inbox by the end** - the domain is being treated reasonably. Start sending, at low
  volume, and keep watching.
- **Still mostly junk at the end** - say so plainly rather than declaring the warm-up
  finished on the calendar. Something else is wrong: check authentication actually aligns,
  check the domain is not on a blocklist, and consider that the content or the sending
  platform is the problem rather than the domain's age.
- **Improving but not there** - keep going. Extending a warm-up costs nothing but time, and
  it is the cheapest lever available.

One honest caveat worth stating once to the user: these mailboxes reply to you and rescue
your mail, so their inbox placement reflects that relationship as much as the domain's
standing. It flatters the numbers. That is fine - the engagement is the point, and it is
what builds the reputation - but it means the placement mix is encouraging evidence, not
proof of how a stranger's filter will treat you.

**Corroborate where the provider says it outright**, since folder placement is noisy:

- **Microsoft** puts the verdict in the headers: `dest:I` for Inbox, `dest:J` for Junk, and
  an `SCL` of 1 or lower means it was not treated as spam.
- **Google Postmaster Tools** shows domain reputation and spam rate, but needs the domain
  verified and more volume than a warm-up produces, so it is often blank. Report "no data
  yet" rather than reading an empty dashboard as a good sign.
- **Gmail's tabs**: Promotions is not spam, but it is not the primary inbox either. Record it
  as `promotions` rather than counting it as an inbox landing.

**The stop rule:** if placement is still Junk after about 15 runs, stop and tell the user
plainly, through a channel they actually read. A warm-up that is not working needs to be
known about rather than run indefinitely. The same goes for a run that cannot send: log it
blocked, say exactly what blocked it, and stop. Never fall back to the brand domain, and
never invent replies to make a blocked run look productive.

## What is off limits

Typing passwords, one-time codes or answers to security questions; accepting two-factor
prompts; buying domains or mailboxes. Those are the user's, and the run stops and says so.
This skill also never emails anyone except the warm-up mailboxes the user supplied - real
outreach is a separate job that starts once the warm-up is finished.
