---
name: frontend-testing-debugging
description: Verify rendered UI, interactions, responsive behavior and browser failures in the actual authorized app. Use for frontend testing or diagnosis; this does not initiate a redesign or scaffold a test framework.
---

# Frontend testing and debugging

Read the [ADLC contract](../../references/adlc-contract.md) and the applicable [Claude Code](../../guides/claude-code.md) or [Codex](../../guides/codex.md) capability guide. Use only tools actually available in this session.

## Establish the target

Reuse the task's expected behavior, acceptance criteria and valid prior evidence. Identify the app URL, environment, running artifact where relevant, affected flow, account/role and permitted data. If a supplied URL or browser tab is the target, inspect it before substituting a local checkout or another environment.

Identify the authorized browser and profile through supported tool configuration or observed state. Follow explicit project/user constraints: when `Work vecton.ai` Chrome is required, use it for all browser work. Do not infer a profile from its account email or silently substitute an in-app browser, fresh automation context or another profile. If the required target, profile or tool is unavailable, stop the affected browser check, report what is missing and ask for the specific access or alternative needed. Continue independent source inspection where useful.

Before starting a stopped app, inspect its documented command and configuration for external services, migrations, secrets and environment selection. Start it only within existing authority and safe local conditions; do not install dependencies, alter persistent host configuration or connect to production merely to obtain a screenshot. Preserve running services and unrelated changes.

## Check the affected flow

Choose checks that can expose the reported failure or demonstrate acceptance. A small layout edit needs less than a changed sign-in or save flow. Use the project's existing tests and browser tools; no new framework, design skill or full application audit is a prerequisite.

1. Observe the starting state and perform the relevant user action through the UI. Check the resulting state rather than merely that a click succeeded. Cover relevant loading, empty, error and success states with authorized synthetic data or controlled fixtures; label mocks and the integrations they bypass.
2. Check relevant narrow and wide layouts and the changed responsive boundary. For affected controls, exercise keyboard navigation, visible focus, accessible names/labels and error recovery. Check zoom/reflow or contrast when the change touches those properties. These focused checks do not establish complete accessibility conformance. See [WAI's preliminary checks](https://www.w3.org/WAI/test-evaluate/preliminary/).
3. For an unexplained failure, correlate the action with the relevant console error, request status, rendered state and affected source. Distinguish a failed request from a rendering defect; narrow the hypothesis before editing. Use bundled [systematic-debugging](../systematic-debugging/SKILL.md) when investigation crosses boundaries or remains uncertain.

When using an existing Playwright setup, prefer role/label or stable contract locators, isolate test data and assert meaningful outcomes with supported retrying assertions. Wait for the required state with a bounded timeout; do not hide races with sleeps, forced clicks or repeated retries. Resolve ambiguous elements instead of choosing an arbitrary match. Read [Playwright's practices](https://playwright.dev/docs/best-practices) when writing those checks; this does not authorize a dependency upgrade or a profile change.

## Keep evidence safe and accurate

Use accounts and records authorized for this check. In review-only work, do not edit source, save records, change settings or trigger external effects. Browser interactions that mutate data still need applicable authority. Do not sign out an existing account or clear shared browser state to manufacture a test condition.

Collect the smallest useful evidence. Avoid customer data, tokens, cookies, request bodies and credential-bearing URLs in screenshots, logs or reports. Never commit or share authenticated browser storage; [Playwright documents its impersonation risk](https://playwright.dev/docs/auth). Prefer filtered status/timing evidence to full network exports. If a HAR is necessary and authorized, use the [sanitized export](https://developer.chrome.com/docs/devtools/network/reference/) and inspect remaining URLs and payloads before sharing; sanitization of authentication headers is not a guarantee that every field is safe.

A screenshot supports a rendering claim at the captured state. It does not prove interaction, persistence, server authorization or a real provider result. For a save claim, inspect the appropriate reload/read-back result when authorized. For access-control changes, check relevant rejected and allowed behavior at the trusted boundary; a hidden control is insufficient. Screenshot-only access must be reported as such.

## Fix and finish within scope

When fixes are authorized, make the smallest change supported by the diagnosis. Preserve the product's design and behavior outside that change. Add or update a focused regression test when it supplies useful repeatable evidence, using bundled [TDD](../tdd/SKILL.md) if appropriate. Rerun affected checks and repository-required checks; reuse still-valid evidence elsewhere.

Report the tested app/environment, browser/profile and relevant viewport/auth state without sensitive identifiers; state the action, expected result and observation. Link safe evidence and precise findings. Separate observed failures, hypotheses, fixes and untested states. Stop when the requested checks pass or a specific missing capability/evidence prevents the remaining claim. Do not claim deployment, cross-browser coverage or release acceptance from a local browser result.
