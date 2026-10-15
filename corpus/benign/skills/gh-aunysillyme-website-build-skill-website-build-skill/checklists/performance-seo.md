# Performance and discovery gate

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
| PS01: reproducible route budgets | Budgets are absent, chosen after failure without approval, or the best run replaces a full series. | Record routes, byte budgets, environment, tool version, three comparable cold mobile reports, calculator/runner median, and declared target. Preserve invalidated runs with reasons. |
| PS02: field evidence and current metrics | Lab score is called field performance or threshold facts lack source/access evidence. | Apply research AD03/AD04 to current metric claims. Keep device class, reporting window, sample sufficiency, p75 evidence and limitations separate from lab results. Missing field data is UNVERIFIED with an owner and follow-up. |
| PS03: asset and third-party costs | Hero delivery is delayed needlessly, dimensions are invented, fonts contact unapproved origins, or a facade requests its provider before activation. | Inspect selected resources, image crops/bytes/dimensions, font failure/shift, and cold pre/post-activation network logs. Check rights and production CSP. |
| PS04: useful interaction and motion | A score improves while a primary journey, reduced-motion mode, hidden-tab suspension, or no-JavaScript content fails. | Retain browser journeys and trace evidence for the exact candidate; review animation and third-party costs without sacrificing functionality. |
| PS05: initial HTML and routing | Public content requires unavailable JavaScript, routes return wrong status, or intended-public pages are orphaned. | Fetch initial HTML and inspect actual status, redirect chains, internal links, useful content, and route inventory. |
| PS06: metadata freshness and parity | Title, canonical, description, social card, sitemap or llms.txt disagree with the validated content revision. | Change one synthetic record, rebuild, and compare every derived surface on rendered output. Inspect actual image dimensions and canonical hosts. |
| PS07: truthful structured data | Entity facts are invented, visible content disagrees, or syntax validity is called consumer eligibility. | Compare owner-approved facts and visible content to the graph; retain schema/consumer validator results and current support claims separately. |
| PS08: discovery and crawler policy | Private/draft/redirect routes leak into discovery, policy changes lack authority, or llms.txt is marketed as a ranking requirement. | Inspect robots, route inclusion rules, sitemap, llms.txt, canonical map and explicit owner policy; verify supported submission actions before any authorized request. |
| PS09: social-response limits | A correct origin response is called proof that an external cached card refreshed. | Save direct bot-agent HTML response and image-fetch evidence separately from any actual third-party preview result. Label missing cache evidence UNVERIFIED. |
| PS10: receiving-property proof | A loaded analytics script is called a delivered event or indexing/citation is claimed without observation. | Inspect the intended property's event receipt or indexing evidence with authorized access; record event, property identity, time and limitations. Missing access leaves the claim UNVERIFIED. |
| PS11: agent handshake | Handshake files grant permissions, advertise payment/email endpoints, drift from the route registry, or are the only home of safety rules. | Fetch /.well-known/agents.json and /.well-known/ai-instructions.json on the candidate, compare action entries to the validated route/offer registry, and confirm human-confirmation markup on payment/signup controls. Verify endpoint and safety definitions also live outside the handshake. |

## Gate receipt

Link route budgets and raw lab reports, current metric source records, content/discovery
revision, validators, receiving-property evidence, and explicit field-data follow-ups.
Missing post-launch field data does not falsely fail a launch, but cannot earn a field PASS.
All required functional, lab-budget, metadata, and truthful-discovery checks still apply.
