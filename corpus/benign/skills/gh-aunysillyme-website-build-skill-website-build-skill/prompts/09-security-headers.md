ASK DATE prerequisite: follow playbooks/research-and-memory.md#ask-date-rule.
Researcher establishes it before intake or research; later roles read scope.md.
Never ask the user for the date or infer it from model knowledge. Apply the
same source, two-date, freshness, reuse, and blocked-gate rules to this stage.

Configure security headers for the real host and built site, then verify their behavior.
Read playbooks/security-headers.md and inspect the site's actual resource requests first.

INVENTORY
- Record scripts, styles, fonts, images, media, connections, frames, forms, and endpoints.
- Explain each external origin and remove unused allowances.
- Choose the starter matching the host and response type; static configuration does
  not necessarily cover server-rendered or function responses.

CONFIGURE
- Enforce a tailored CSP with object-src 'none', base restrictions, and framing protection.
- Prefer self-hosted fonts and click-to-play embeds to keep permissions narrow.
- Handle legitimate inline content with exact hashes or an appropriate nonce design.
- Never add unsafe-eval to production to silence an error.
- Set nosniff, framing protection, Referrer-Policy, and a relevant Permissions-Policy.
- Use two-year HSTS only after verifying HTTPS readiness; inspect all subdomains
  before includeSubDomains, and never opt into preload as an incidental cleanup.
- Avoid duplicate CSP headers that accidentally intersect into a broken policy.

VERIFY
- Inspect actual headers for normal pages, redirects, errors, static assets, and functions.
- Exercise the main journey in a real browser with the enforced policy active.
- Confirm fonts, images, payments, forms, and authorized embeds still work.
- Run securityheaders.com and retain the dated grade; target A or A+.
- A scanner grade cannot prove authorization, input validation, or application security.
- If the scanner is unavailable, retain direct evidence and mark its grade UNVERIFIED.

SAVE
Write site-work/qa/security-headers.md with configuration, exceptions, observed responses,
browser results, scanner result, and any unresolved release blockers.
Hand the immutable candidate and this report to the independent auditor.

EVIDENCE
Never report a measured, saved, installed, or deployed result without evidence.
Apply the stage route and named checks in manifest.json before handing off.
