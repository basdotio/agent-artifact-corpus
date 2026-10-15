# Security gate

Date rule: [ASK DATE, source evidence, and revalidation](../playbooks/research-and-memory.md#ask-date-rule).

## Record evidence before accepting a gate

- Status: PASS, FAIL, BLOCKED, or NOT APPLICABLE for each check; default BLOCKED.
- Required fields: check ID, artifact revision/digest, role and model family, method,
  environment, actual run/access time, input or claim IDs, observed result, evidence path,
  limitations, owner, and next action. NOT APPLICABLE needs a scope-specific reason.
- Passing evidence: reopen the artifact and the result; a checked box is not proof.
- Failure: any required FAIL or BLOCKED stops the dependent stage.
- Claims: UNVERIFIED describes missing proof and cannot count as a passing result.
- Spelling: treat PASSED, complete, or equivalent success labels as attempted PASS.
- Honesty: never report a measured, saved, installed, or deployed result without evidence.
- Ownership: the producer writes its receipt; Coordinator records acceptance in status.md.
- Change: revised inputs, expired sources, or a different artifact invalidate affected receipts.

## Blockers first

| Check | Reject condition | Method and required evidence |
| --- | --- | --- |
| S01: exposed surface and source currency | Endpoints, forms, integrations, inputs, secrets or host response classes are missing from the threat map. | Open current security/host source claims and inspect candidate routes/resources. Record callers, trust boundaries, data flow, authorizations, and applicability. |
| S02: enforced response headers | Required response classes lack the intended CSP, HSTS where ready, nosniff, framing protection, referrer or permissions policy. | Inspect actual GET responses for success, redirects, errors, assets, proxies and functions. Require one intended enforced CSP; report-only or duplicate intersections do not pass. |
| S03: narrow CSP and HTTPS readiness | Production unsafe-eval, unreviewed wildcard script origins, reused static nonces, or unready HSTS scope is present. | Compare exact origin inventory and inline hash/nonce design to served bytes. Retain HTTPS/subdomain readiness and explicit preload decision if applicable. |
| S04: functional policy and scanner | Required scanner is unavailable/below A, or an A/A+ grade substitutes for working journeys. | Save dated securityheaders.com result for the exact URL and browser results with enforced CSP. Unavailable grade is UNVERIFIED and required grade check BLOCKED. |
| S05: input and rendering | Dangerous URLs, script-bound JSON, empty IDs, attributes or rich HTML escape their intended context. | Run build B02/B04/B05 and endpoint negative cases against the exact candidate. Record rejection behavior and inert generated output. |
| S06: authorization and dependency boundaries | Applicable auth, payments, uploads, origin checks or dependency risks lack evidence. | Test unauthenticated and wrong-authority requests, rejected content, and relevant advisory/version claims within authorized scope. Mark inapplicable surfaces with reasons. |
| S07: secrets and public payload | Credentials, private research, personal data, source assets without rights, or unrelated files enter client/deploy output. | Inspect actual upload allowlist and built assets; use redacted evidence for secret checks. Verify exact rights notices and environment separation. |
| S08: independent audit readiness | Candidate is moving, AUDIT_BRIEF lacks design reasoning, or family/read-only evidence is missing. | Read immutable identity, runtime, callers, threat model, prior tests, design choices, reproduction commands, model-family proof and Reviewer tool boundary. Internal review leaves independent gate unmet. |

## Gate receipt

Save origin/threat inventory, response matrix, configuration revision, browser results,
scanner evidence, negative tests, payload inspection, and the fixed audit packet.
A header grade is not proof of authorization correctness or absence of vulnerabilities.
Follow ship.md for independent review, disposition, artifact promotion, and live checks.

