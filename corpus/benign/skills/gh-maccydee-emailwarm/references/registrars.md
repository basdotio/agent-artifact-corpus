# Editing email DNS at the common registrars

The records are the same everywhere (see SKILL.md step 2). What differs is where they live
and how each registrar mangles what you type. Read the relevant section before editing, and
read every saved value back afterwards.

## The trap that catches every registrar

**The host/name field.** Some registrars want the bare subdomain (`_dmarc`), others want the
fully qualified name (`_dmarc.example.com`), and several silently append the domain to
whatever you type. Enter `_dmarc`, save, then read it back: if it now says
`_dmarc.example.com.example.com`, that is why the record does not resolve. The same applies
to `@` for the root.

**Long DKIM keys.** A DKIM value is longer than the 255-character limit of a single TXT
string. Good registrars split it for you; some reject it; some truncate it silently. If
`dns_check.py` finds a key but mail still fails DKIM, suspect truncation and re-paste.

**TTL and propagation.** A change is not live until the old TTL expires. If a record does
not show, wait it out rather than editing again - repeated edits during propagation are how
duplicate SPF records appear, and two SPF records fail every check.

## GoDaddy

`https://dcc.godaddy.com/control/<domain>/dns` (or Domains, then DNS, then Manage Zones).

- Host field takes the bare name: `@` for the root, `_dmarc` for DMARC.
- GoDaddy appends the domain automatically, so never type the full name.
- Records are edited in place with a pencil icon; adding a second SPF instead of editing the
  first is the most common mistake here.
- Changes usually show within minutes but the TTL is an hour by default.

## Namecheap

Domain List, then Manage, then Advanced DNS.

- TXT records go under "Host Records" with type TXT Record.
- Host is the bare name; `@` for the root.
- Namecheap has a separate "Mail Settings" section - leave it on Custom MX if the mailbox is
  elsewhere, since switching it can wipe MX records.

## Cloudflare

Select the domain, then DNS, then Records.

- Host takes either form; Cloudflare normalises it and shows the full name.
- **TXT records are never proxied** - the orange cloud does not apply. If you see a proxy
  toggle on something, you are on the wrong record type.
- Changes are effectively instant, which makes Cloudflare the easiest place to verify a fix.

## 123-reg

Domains, then Manage, then Advanced DNS / DNS Management.

- The TXT interface splits long values across fields and has historically mangled DKIM keys.
  Paste, save, then read the value back before trusting it.
- The control panel caches: reload the page rather than trusting the view after a save.

## IONOS

Domains & SSL, then the domain, then DNS.

- Host is bare; IONOS shows the resulting full name beneath the field, which is useful for
  catching the appended-domain problem.

## Squarespace (formerly Google Domains)

Domains, then the domain, then DNS, then DNS Records.

- Google Domains migrated here, so older instructions pointing at domains.google are dead.
- Host is bare. Custom records are a separate section from the presets.

## Where DKIM actually comes from

DKIM keys are generated in the **mail provider's** console, not the registrar:

- **Google Workspace**: Admin console, Apps, Google Workspace, Gmail, Authenticate email.
  Generate the key, then publish the given selector (usually `google`) at the registrar.
  Turning on authentication in the console does nothing until the DNS record exists.
- **Microsoft 365**: Defender portal, Email & collaboration, Policies, Email authentication,
  DKIM. Microsoft publishes two CNAMEs (`selector1`, `selector2`) rather than a TXT key.
- Others differ; take the selector from the console and pass it to
  `dns_check.py --selector`, since DKIM has no discovery mechanism and cannot be found by
  guessing.
