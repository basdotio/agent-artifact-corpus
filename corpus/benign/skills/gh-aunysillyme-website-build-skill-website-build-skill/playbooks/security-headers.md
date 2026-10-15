# Tailor headers to the real response

Date rule: [establish ASK DATE and revalidate claims](research-and-memory.md#ask-date-rule).
Source status: external facts and example commands are UNVERIFIED until checked for the chosen version and engagement.
Record opened URLs, source dates or unknown, actual access dates, and supporting evidence.

Question: which restrictions fit the site's actual host, resources, and endpoints?

## Inventory before configuring

List every script, stylesheet, image, font, media source, frame, connection, and form target.
Record exact origins, inline blocks, required permissions, and the user task each serves.
Remove unused resources before adding allowances.
Map normal HTML, redirects, errors, static assets, proxies, and function responses separately.
Verify HTTPS readiness and recovery before enabling long-lived HSTS.

## Review the starter assumptions

These starters assume HTTPS, self-hosted resources, no inline scripts or styles,
no third-party frames or APIs, and no need for another site to frame this site.
They are UNVERIFIED configuration proposals, not deployed or scanned examples.
Keep existing redirects, rewrites, and unrelated settings while merging the rules.
The supplied HSTS preset is max-age=63072000; verify the chosen policy and readiness.
Never add includeSubDomains without an HTTPS inventory of every affected subdomain.
Never enable preload as incidental cleanup; it needs a separate explicit decision.

## Select the static host format

### Vercel static deployment

Merge this proposal into vercel.json, then inspect actual response coverage.

```json
{
  "headers": [{
    "source": "/(.*)",
    "headers": [
      {"key": "Content-Security-Policy", "value": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; media-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests"},
      {"key": "Strict-Transport-Security", "value": "max-age=63072000"},
      {"key": "X-Content-Type-Options", "value": "nosniff"},
      {"key": "X-Frame-Options", "value": "DENY"},
      {"key": "Referrer-Policy", "value": "strict-origin-when-cross-origin"},
      {"key": "Permissions-Policy", "value": "camera=(), microphone=(), geolocation=()"}
    ]
  }]
}
```

Starting source: https://vercel.com/docs/project-configuration
Current syntax, matching, and response coverage require source opening and a host test.

### Cloudflare Pages static output

Place this proposal in the deployed static directory as _headers.

```text
/*
  Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; media-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests
  Strict-Transport-Security: max-age=63072000
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
```

Starting source: https://developers.cloudflare.com/pages/configuration/headers/
Verify the current documented exclusion of function responses; set and test their
headers in the response path rather than assuming this static file covers them.

### Netlify static output

Place this proposal in the publish directory as _headers.

```text
/*
  Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; media-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests
  Strict-Transport-Security: max-age=63072000
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
```

Starting source: https://docs.netlify.com/manage/routing/headers/
Verify current behavior for proxies, functions, and edge functions separately.
Static rules alone cannot be treated as proof of headers on every response class.

## Adapt CSP to actual resources

Add reviewed exact frame-src origins for authorized embeds and connect-src origins for APIs.
Retain object-src 'none', a reviewed base-uri, form-action, and framing policy.
Avoid wildcard script origins and production unsafe-eval.
Self-host fonts and use local-poster embed facades to keep the resource graph small.

Static inline blocks need hashes of their exact served bytes when a hash policy is chosen.
Regenerate hashes when bytes change and test the final artifact, including line endings.
A nonce design needs unpredictable per-response values shared by the header and allowed blocks.
Do not reuse a fixed nonce in static output or publish cached nonce-bearing HTML blindly.
Do not copy a strict static CSP onto a framework and assume hydration still works.
Read the selected framework's current CSP guidance and inspect emitted scripts.
Safe JSON serialization remains required even when CSP is enforced.

## Verify the policy, then the journey

Use an actual GET response and preserve status, redirect chain, relevant headers, and URL.
Avoid relying on HEAD alone when the host handles it differently.
Check normal HTML, redirect responses and destinations, errors, assets, and functions.
Require exactly one intended enforced CSP per response, with no accidental duplicate policy.
Report-only CSP helps diagnosis but cannot satisfy the enforced-policy gate.

Exercise navigation, forms, fonts, images, authorized players, and payments when applicable.
Inspect browser violations with production policy active and retain functional evidence.
Run securityheaders.com against the exact authorized public URL and save its dated result.
Require A or A+ plus working journeys; a grade alone cannot prove application security.
If the scanner cannot run, record UNVERIFIED and leave its required gate blocked.

## Record exceptions and recovery

Write site-work/qa/security-headers.md with candidate identity, origin inventory,
config revision, response matrix, browser results, scanner receipt, and remaining failures.
An exception needs scope, reason, owner, expiry, and evidence; do not silently lower a gate.
Keep the prior known-working configuration and an authorized rollback procedure.
New resources or endpoints invalidate affected header checks before release.
Apply checklists/security.md S01 through S08.

## Failure modes

- Duplicate CSP: intersecting policies silently break allowed behavior.
- Partial coverage: a static header file leaves function errors unprotected.
- Scanner substitution: an A grade hides broken forms or authorization gaps.
- Premature HSTS: unready subdomains become inaccessible for returning browsers.
- Hash drift: minification changes inline bytes after policy generation.
