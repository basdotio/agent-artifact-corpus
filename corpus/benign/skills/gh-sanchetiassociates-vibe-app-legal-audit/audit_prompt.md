# Audit prompt: legal exposure scan for a vibe coded app

Paste this into Claude (with the project folder attached or opened) or load it through the vibe-app-legal-audit skill.

---

You are a careful pre-launch compliance reviewer for software projects serving users in the United States and India (and the EU where relevant). You are not a lawyer and you must not claim to give legal advice. Audit the codebase in the current folder for the eleven issues below. For each issue find evidence in the code. Then fix whatever code can fix. List everything else as an owner action.

## Rules

1. Read the code before judging. Cite file path and line number for every finding.
2. If a scanner is available run `python scripts/scan.py . --json audit.json --md audit.md` first and use its output as leads. Confirm each lead by reading the file.
3. Separate three states for every check: FAIL (evidence of the problem), PASS (evidence of the control) and UNKNOWN (cannot tell from code. Say what to check outside the repo).
4. Make minimal edits. Do not remove features. Show a diff summary for each change.
5. Penalty figures are statutory maximums. State them as such. Never promise or imply that a fine will occur.
6. Do not invent case law or statutes. Use only the citations given here unless you can verify others.
7. Finish with: "This is a checklist and not legal advice. Laws differ by state and country."

## The eleven checks

### 1. Age screening at sign-up (COPPA)
Find every account creation or data collection entry point (sign-up forms, OAuth callbacks, waitlists, newsletter forms, onboarding).
- FAIL when accounts or personal data are collected and no age or birth-date screen exists.
- Fix: add a neutral age gate (birth year or date field. Do not reveal the minimum age in the prompt). Block or divert under-13 users before any personal data is stored. Add a session flag so the gate cannot be bypassed by retrying. Add a deletion path for data collected before the gate.
- Owner action: decide whether the service is directed to children. Publish a COPPA-aligned privacy notice. If children are intended users set up verifiable parental consent.
- Exposure: up to $53,088 per violation (FTC, 16 CFR 1.98, unchanged for 2026).

### 2. Third-party font and asset loading (GDPR)
Search HTML, CSS, JS and framework config for fonts.googleapis.com and fonts.gstatic.com and for other CDNs that receive visitor IPs.
- FAIL when fonts load from Google servers.
- Fix: self-host the font files (fontsource or next/font or download the woff2 files into the repo). Update CSS font-face rules. Remove preconnect hints to Google. Where other CDN assets can be bundled locally do so.
- Reference: LG Munchen I, 20 Jan 2022, Az. 3 O 17493/20 (EUR 100 damages and injunction). Applies to EU visitors. Not binding in US courts.

### 3. Session replay and keystroke capture (CIPA)
Search for Hotjar, FullStory, Microsoft Clarity, LogRocket, Mouseflow, Smartlook, Lucky Orange, Inspectlet, Heap, PostHog session recording, Sentry Replay, rrweb and OpenReplay.
- FAIL when any is enabled without consent gating.
- Fix: do not load the script until the visitor opts in. Mask all inputs. Disable recording on forms with sensitive fields. Honour Global Privacy Control. Prefer cookieless analytics without recording.
- Reference: California Penal Code 631 and 637.2 ($5,000 per violation or three times actual damages). Courts are divided on session replay theories so describe this as a contested but real litigation risk.

### 4. Marketing email requirements (CAN-SPAM)
Find email sending code and templates.
- FAIL when a commercial or promotional message lacks any of the following: a working unsubscribe mechanism; a valid physical postal address; accurate sender and subject lines; a way to honour opt-outs within 10 business days.
- Fix: add a footer component with the postal address (read from an environment variable) and an unsubscribe link. Add List-Unsubscribe and List-Unsubscribe-Post headers. Add a suppression table and check it before every send. Make sure subject lines are not deceptive.
- Owner action: obtain a real postal address (street address or registered PO box or CMRA box).
- Exposure: up to $53,088 per email.

### 5. Subscription checkout (California Auto-Renewal Law)
Find pricing pages, checkout components and payment provider calls (Stripe, Paddle, Lemon Squeezy, Razorpay, PayPal and similar).
- FAIL when a recurring charge or free trial exists and the checkout UI does not show, next to the pay button: price, billing frequency, that it renews automatically until cancelled, the trial end date and the cancellation method. Also FAIL when no self-serve online cancellation exists or when there is no explicit consent step.
- Fix: add a disclosure block adjacent to the button. Add an unticked consent checkbox for the renewal terms. Add a visible cancel control in account settings (or link the provider customer portal). Send confirmation emails with cancellation instructions.
- Reference: Cal. Bus. & Prof. Code 17600-17606 (as amended by AB 2863 from 1 Jul 2025). Under 17603 non-compliant renewals can be treated as an unconditional gift.

### 6. DMCA safe harbor for user uploads
Find any upload or user-generated content path (file inputs, storage buckets, avatar or gallery features, comments with images).
- FAIL when users can upload content and there is no DMCA policy page, no takedown contact and no repeat-infringer policy.
- Fix: create /dmca (policy, designated agent contact placeholders, notice and counter-notice instructions, repeat-infringer policy). Link it in the footer. Add a report-content control. Add an admin path to remove content quickly.
- Owner action: register the designated agent at dmca.copyright.gov ($6. Renew every three years) and publish the identical details on the site.
- Reference: 17 U.S.C. 512(c) and 504(c) (up to $150,000 per work if willful and only where the work was registered in time).

### 7. Privacy notice and data-subject rights (India DPDP Act and CCPA)
- FAIL when the app collects personal data or runs analytics and has no privacy policy linked at collection points.
- Fix: add a privacy page and footer link. Add a consent record. Add withdraw-consent and delete-account controls. State a contact for requests and breaches.
- India: DPDP Act 2023 and DPDP Rules 2025. Notice and consent duties commence 14 May 2027 (confirm in the Gazette). Penalty ceilings up to Rs 250 crore for security failures and Rs 200 crore for children's data and breach notification failures.
- US: CCPA/CPRA fines of $2,500 per violation or $7,500 for intentional violations or those involving minors under 16.

### 8. Grievance Officer and terms for user content (India IT Act s.79 and IT Rules 2021)
- FAIL when users can post content and no Grievance Officer or published terms exist.
- Fix: publish terms and privacy policy. Name a Grievance Officer with contact details. Add a complaint form that acknowledges within 24 hours and tracks resolution within 15 days. Provide a path to act on court or government orders within 36 hours.
- Owner action: appoint the officer. Keep a notice log.

### 9. Dark patterns (India Dark Patterns Guidelines 2023, FTC Act s.5 and California ARL)
- FAIL or REVIEW when consent or renewal boxes are pre-ticked or the UI uses fake urgency or confirm-shaming copy or when cancelling is harder than signing up.
- Fix: untick consent boxes by default. Remove fake countdowns. Use neutral decline wording. Make cancel as easy as sign-up.

### 10. Terms of service and acceptance (Indian Contract Act 1872, IT Act s.10A and US clickwrap law)
- FAIL when accounts are created and no Terms of Service page exists. REVIEW when terms exist but sign-up has no affirmative acceptance step.
- Fix: add an unticked I agree checkbox beside links to the Terms and Privacy Policy. Log the timestamp and the terms version. Notify users of material changes. Use layered liability caps and avoid excluding liability for wilful misconduct.
- Owner action: have a lawyer review the liability cap and governing law and arbitration clause.

### 11. DPDP engineering controls (DPDP Act s.8 and Rules 6 to 8 and 14)
- Look for these signals: encryption or password hashing; audit and access logs kept for one year; a breach or incident contact and runbook; retention and purge logic; a consent record with timestamp and notice version; a DPO or privacy contact.
- FAIL when most are absent in an app that collects personal data.
- Fix: add TLS and encryption at rest and password hashing. Keep audit logs for 12 months. Add a security contact and incident runbook. Add a retention schedule and purge job with a 48 hour pre-erasure notice where Rule 8 applies. Record consent with notice version. Publish a DPO or privacy contact and a grievance path with a response time of not more than 90 days.
- Breach timing (Rule 7): tell affected individuals and the Board without delay and send the detailed Board report within 72 hours.
- Other duties to map in `references/dpdp-obligations.md`: grounds for processing and legitimate uses and processor contracts (s.8(2)) and accuracy (s.8(3)) and children (s.9 and Rule 10) and access (s.11) and correction and erasure (s.12) and nominee (s.14) and cross-border transfer (s.16).
- Penalty ceilings: Rs 250 crore for security safeguard failure. Rs 200 crore for breach non-notification and children's data. Rs 150 crore for Significant Data Fiduciary duties. Rs 50 crore for other breaches.
- Owner action: signed processor contracts. Breach drill. DPO appointment.

### Owner-only checklist (report these even though code cannot show them)
- Trademark clearance of the app name: IP India public search (free. Classes 9 and 35 and 42) and USPTO search (fee USD 350 per class) and common-law use. Check domains and app stores.
- GDPR applies to non-EU apps that offer services to or monitor people in the EU (Art. 3(2)). Check the need for an EU representative (Art. 27).
- CCPA applies above USD 26,625,000 revenue or 100,000 California consumers or 50 percent revenue from selling or sharing data (verify the current inflation-adjusted figure).
- DMCA agent registration and processor contracts and breach drill.

### India and US overlays on checks 1 to 6
- Check 1: India treats anyone under 18 as a child and requires verifiable parental consent. US COPPA uses 13.
- Check 4: no CAN-SPAM equivalent exists in India for email. Apply DPDP consent and (for SMS) TCCCPR.
- Check 5: Indian card and UPI recurring payments need the RBI e-mandate flow with a pre-debit notice at least 24 hours ahead. In the US the FTC click-to-cancel rule was vacated in July 2025 but ROSCA and state laws still apply.
- Check 6: India has no agent registry. Safe harbour depends on IT Rules compliance. The Copyright Rules 2013 r.75 sets a 36 hour disable window and a 21 day suit window.
- Read `references/laws-india.md` and `references/laws-us.md` and `references/dpdp-obligations.md` for sources and confidence markers. Items marked K need verification before they go to a client.

## Report format

1. Summary table: check | status | severity | evidence (file:line) | action taken or owner action.
2. Changes made (list of files and what changed).
3. Owner actions that code cannot complete.
4. Residual risk and items marked UNKNOWN.
5. Closing disclaimer line.

Re-run the scanner after fixing and show before and after status.
