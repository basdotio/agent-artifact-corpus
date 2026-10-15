# Domains, providers and DNS

## Two domains, not one

| Domain | Role | Carries |
|---|---|---|
| brand | the asset that must survive | website, preview links, your own address, client contact |
| sending | disposable | cold outreach only |

Sending domains get blacklisted and neither kind recovers quickly. Replacing a sending
domain costs a registration fee. Replacing a brand domain kills every link you have ever
published and every existing contact route. Pick a sending domain that is recognisably
related to the brand (a prefix like `get-` or `try-` is normal and does not hurt), keep the
two in separate reputation pools, and never send cold mail from the brand domain even once.

One mailbox can send as both. A provider alias on the sending domain costs nothing and
needs no second licence, which is usually simpler than running two mailboxes.

### Which address to use for account signups, invoices and suppliers

**The brand domain, every time.** People ask this because the sending domain feels like the
"work" one, and it is the wrong instinct twice over:

- The sending domain is **disposable by design**. If it gets blacklisted you replace it, and
  every account whose password reset, billing notice and two-factor recovery points at it
  goes with it. That is a bad day you cannot undo by buying another domain.
- Signup confirmations and invoices are **inbound**, so they build no sending reputation.
  You gain nothing by routing them through the domain you are trying to warm.

The opposite is true and worth saying out loud: ordinary correspondence with suppliers,
accountants and services is the **strongest** reputation signal available, because it is real
two-way mail with humans and systems that reply. Point it at the brand domain, which is the
asset that has to survive, and keep the sending domain for outreach and nothing else.

## Choosing a provider

Check the acceptable use policy before you commit, because this is a real constraint rather
than a formality: several large transactional providers ban cold outreach outright and close
accounts without warning, taking the reputation with them.

| Route | Cold outreach | Notes |
|---|---|---|
| Transactional APIs (Postmark, Resend and similar) | usually prohibited | read the AUP; transactional only |
| Amazon SES | permitted with care | needs production access, you own compliance |
| Google Workspace / Microsoft 365 | tolerated at low volume | ~10/day is inside ordinary use |
| Dedicated outreach platforms | built for it | warm-up automation included |

At ten sends a day an ordinary mailbox is indistinguishable from a person and needs no
special approval. Reach for a platform when volume genuinely demands it.

## DNS records

Set these on the **sending** domain. Substitute your provider's values.

```
; SPF - exactly one SPF record. Two is a permerror and fails every check.
SENDING-DOMAIN.        TXT   "v=spf1 include:_spf.example-provider.com -all"

; DKIM - selector and key come from the provider console
selector._domainkey    TXT   "v=DKIM1; k=rsa; p=<PUBLIC-KEY>"

; DMARC - start at none and observe before enforcing
_dmarc                 TXT   "v=DMARC1; p=none; rua=mailto:dmarc@SENDING-DOMAIN; fo=1"
```

Prefer `-all` (hard fail) over `~all`: a soft fail invites spoofing of a domain whose whole
job is to be trusted by strangers.

### Tighten DMARC on a schedule

| Week | Policy | Why |
|---|---|---|
| 1-2 | `p=none` | collect reports, confirm SPF and DKIM align before enforcing |
| 3-4 | `p=quarantine; pct=25` | enforce on a quarter of traffic, watch for false positives |
| 5+ | `p=reject` | full enforcement |

Going straight to `p=reject` before reading a report is how legitimate mail disappears
silently.

### Verify alignment, not just presence

A record that exists is not a record that passes. Send one message to a mailbox you control
and read `Authentication-Results`: SPF, DKIM and DMARC should each say `pass`, and the
domains should match the `From:` domain. Alignment failures are common when a mailbox sends
as an alias on a second domain, and they are invisible until you read a header.

## What the message itself needs, once you are past warm-up

- A working unsubscribe route, honoured immediately and recorded.
- A real postal address, where the jurisdiction requires it.
- Plain text, no tracking pixel, no link shortener. All three are spam signals.
- Content a human would plausibly send to one person.
