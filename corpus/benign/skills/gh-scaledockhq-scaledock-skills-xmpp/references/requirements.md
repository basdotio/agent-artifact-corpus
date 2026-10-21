# Requirements from the pinned text

These sentences were read from the pinned sources on 2026-10-06. They are the normative or conformance sentences the extractor found (MUST, SHOULD, or REQUIRED). Apply the ones that match the role. Section headings are the nearest heading in the published document.

## RFC 6120

Source: https://www.rfc-editor.org/rfc/rfc6120

RFC 6120: Extensible Messaging and Presence Protocol (XMPP): Core | RFC Editor Your browser has JavaScript disabled. Most of this site works without JS, but some features require it. If something seems broken please try enabling JavaScript and reloading the page. The JavaScript used by this site is served directly from IETF infrastructure and does not include any code that links to a third party service. Skip to content

- **RFC 6120 : Extensible Messaging and Presence Protocol (XMPP): Core.** Terminology The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119 [ KEYWORDS ].
- **RFC 6120 : Extensible Messaging and Presence Protocol (XMPP): Core.** Scope As XMPP is defined in this specification, an initiating entity (client or server) MUST open a Transmission Control Protocol [ TCP ] connection to the receiving entity (server) before it negotiates XML streams with the receiving entity.
- **RFC 6120 : Extensible Messaging and Presence Protocol (XMPP): Core.** (However, if the result of the SRV lookup is a single resource record with a Target of ".", i.e., the root domain, then the initiating entity MUST abort SRV processing at this point because according to [ DNS-SRV ] such a Target "means that the service is decidedly not available at this domain".) 4.
- **RFC 6120 : Extensible Messaging and Presence Protocol (XMPP): Core.** If the initiating entity receives a response to its SRV query but it is not able to establish an XMPP connection using the data received in the response, it SHOULD NOT attempt the fallback process described in the next section (this helps to prevent a state mismatch between inbound and outbound connections).
- **RFC 6120 : Extensible Messaging and Presence Protocol (XMPP): Core.** If the initiating entity does not receive a response to its SRV query, it SHOULD attempt the fallback process described in the next section.
- **RFC 6120 : Extensible Messaging and Presence Protocol (XMPP): Core.** Fallback Processes The fallback process SHOULD be a normal "A" or "AAAA" address record resolution to determine the IPv4 or IPv6 address of the origin domain, where the port used is the "xmpp-client" port of 5222 for client-to-server connections or the "xmpp-server" port of 5269 for server-to-server connections (these are the default ports as registered with the IANA as described under Section 14.7 ).
- **RFC 6120 : Extensible Messaging and Presence Protocol (XMPP): Core.** If an entity chooses to reconnect, it: o SHOULD set the number of seconds that expire before reconnecting to an unpredictable number between 0 and 60 (this helps to ensure that not all entities attempt to reconnect at exactly the same number of seconds after being disconnected).
- **RFC 6120 : Extensible Messaging and Presence Protocol (XMPP): Core.** o SHOULD back off increasingly on the time between subsequent reconnection attempts (e.g., in accordance with "truncated binary exponential backoff" as described in [ ETHERNET ]) if the first reconnection attempt does not succeed.
