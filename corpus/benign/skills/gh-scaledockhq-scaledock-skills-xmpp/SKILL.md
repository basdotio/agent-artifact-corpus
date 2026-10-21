---
name: xmpp
description: >-
  XMPP (RFC 6120): build clients and servers for the Extensible Messaging and Presence Protocol. Covers RFC 6120. Use when implementing XMPP. Triggers: XMPP.
license: MIT
metadata:
  author: ScaleDockHQ
  version: "1.0.1"
  kind: standard
---

# XMPP

RFC 6120: Extensible Messaging and Presence Protocol (XMPP): Core | RFC Editor Your browser has JavaScript disabled. Most of this site works without JS, but some features require it. If something seems broken please try enabling JavaScript and reloading the page. The JavaScript used by this site is served directly from IETF infrastructure and does not include any code that links to a third party service. Skip to content

The publisher of the pinned text is named in [Sources](#sources). With this skill the agent applies that text: when implementing XMPP.

**Follow the workflow below step by step.** Every rule here comes from a source in [Sources](#sources). Quoted requirements are sentences taken from the pinned text. When a rule and the pinned source disagree, the source wins; when the source has a newer revision than the pin, follow the refresh steps.

## Inputs (fill in, or ask before starting)

- Role: producer or consumer of this specification.
- Target version: RFC 6120 (default). See [`references/versions.md`](references/versions.md).
- Revision: the pinned revision in [Sources](#sources), unless the user names another.
- Sources: when refreshing this skill, re-read every URL in [Sources](#sources) and check the publisher index for a newer revision or version line.

## Invariants

1. **RFC 6120 : Extensible Messaging and Presence Protocol (XMPP): Core.** "Terminology The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119 [ KEYWORDS ]."
2. **RFC 6120 : Extensible Messaging and Presence Protocol (XMPP): Core.** "Scope As XMPP is defined in this specification, an initiating entity (client or server) MUST open a Transmission Control Protocol [ TCP ] connection to the receiving entity (server) before it negotiates XML streams with the receiving entity."
3. **RFC 6120 : Extensible Messaging and Presence Protocol (XMPP): Core.** "(However, if the result of the SRV lookup is a single resource record with a Target of ".", i.e., the root domain, then the initiating entity MUST abort SRV processing at this point because according to [ DNS-SRV ] such a Target "means that the service is decidedly not available at this domain".) 4."
4. **RFC 6120 : Extensible Messaging and Presence Protocol (XMPP): Core.** "If the initiating entity receives a response to its SRV query but it is not able to establish an XMPP connection using the data received in the response, it SHOULD NOT attempt the fallback process described in the next section (this helps to prevent a state mismatch between inbound and outbound connections)."
5. **RFC 6120 : Extensible Messaging and Presence Protocol (XMPP): Core.** "If the initiating entity does not receive a response to its SRV query, it SHOULD attempt the fallback process described in the next section."
6. **RFC 6120 : Extensible Messaging and Presence Protocol (XMPP): Core.** "Fallback Processes The fallback process SHOULD be a normal "A" or "AAAA" address record resolution to determine the IPv4 or IPv6 address of the origin domain, where the port used is the "xmpp-client" port of 5222 for client-to-server connections or the "xmpp-server" port of 5269 for server-to-server connections (these are the default ports as registered with the IANA as described under Section 14.7 )."
7. **RFC 6120 : Extensible Messaging and Presence Protocol (XMPP): Core.** "If an entity chooses to reconnect, it: o SHOULD set the number of seconds that expire before reconnecting to an unpredictable number between 0 and 60 (this helps to ensure that not all entities attempt to reconnect at exactly the same number of seconds after being disconnected)."
8. **RFC 6120 : Extensible Messaging and Presence Protocol (XMPP): Core.** "o SHOULD back off increasingly on the time between subsequent reconnection attempts (e.g., in accordance with "truncated binary exponential backoff" as described in [ ETHERNET ]) if the first reconnection attempt does not succeed."

## Workflow

1. **Pick the version.** Use the current line unless a named consumer needs a supported one. Do not author a legacy line. Emit a preview only when its posture is build and the user asked for that draft.
   -> [`references/versions.md`](references/versions.md)
   ✓ The target version is recorded, and it is not a legacy line.
2. **Apply the pinned requirements.** Walk the quotes in [`references/requirements.md`](references/requirements.md) and implement each one that applies to the role.
   -> [`references/requirements.md`](references/requirements.md)
   ✓ Each applicable quote is either implemented or recorded as out of scope for the role, with the heading it came from.
3. **Upgrade** (only when asked). Follow the upgrade section from the source line to the target.
   -> [`references/versions.md`](references/versions.md)
   ✓ The result cites the target line and no longer depends on a requirement that only the old line stated.

## Verify before done

- [ ] The artifact cites the target line's revision from [Sources](#sources).
- [ ] Every applicable quoted requirement in [`references/requirements.md`](references/requirements.md) holds.
- [ ] Nothing from a preview line is emitted unless its posture is build and the user opted in.

## Reference index

- **`references/versions.md`**: every version line, which one to use, and how to upgrade. Load for steps 1 and 3.
- **`references/requirements.md`**: quotes taken from the pinned specification. Load for step 2.

## Related skills

Install related spec skills by name with `npx skills add ScaleDockHQ/scaledock-skills --skill <name>`.

## Sources

Status uses the publishing body's own maturity term. Checked is the date the source was last read.

- [RFC 6120](https://www.rfc-editor.org/rfc/rfc6120): RFC, RFC 6120, fetched 2026-10-06 (RFC, 2026-10-06), checked 2026-10-06.
