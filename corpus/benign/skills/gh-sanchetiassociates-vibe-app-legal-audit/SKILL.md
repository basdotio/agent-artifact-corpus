---
name: vibe-app-legal-audit
description: Audit a web or mobile app codebase (especially AI-generated "vibe coded" apps) for eleven common legal-exposure patterns before launch. Checks them against US, Indian and EU rules: age screening (COPPA and India DPDP), Google Fonts IP leakage (GDPR), session replay wiretap risk (California CIPA and other states), email footers (CAN-SPAM and Indian consent rules), auto-renewal checkout terms (California ARL and ROSCA and India dark-patterns and RBI e-mandate rules), upload liability (DMCA and Indian IT Act s.79 and Copyright Act), privacy notices, grievance officer, dark patterns, terms of service acceptance and DPDP engineering controls (security safeguards, breach notification, retention, children, processor contracts). Scans the code, reports findings with file and line evidence and applies the fixes that code can solve. Use when the user says audit my app, legal check, pre-launch compliance, vibe code risks, DPDP, COPPA, CAN-SPAM, DMCA, CIPA, IT Rules or Google Fonts GDPR. Not legal advice.
---

# Vibe App Legal Audit

A pre-launch triage skill. It finds eleven well-known sources of per-user and per-email statutory exposure in a codebase and fixes whatever code can fix. It is a checklist and not legal advice. Laws differ by state and country. Always tell the user to confirm material points with a qualified lawyer.

## Workflow

1. Locate the project root. Ask only if it is truly unclear. Note which jurisdictions the app serves (US states, India, EU). If the user does not say assume all three and say so in the report.
2. Run the scanner: `python scripts/scan.py <project_dir> --json audit.json --md audit.md`
   - Exit code 1 means at least one HIGH finding.
   - The scanner is regex based. Treat every hit as a lead and every PASS as unproven.
3. Verify each lead by reading the flagged files. Remove false positives. Look for what regex cannot see (build output, CMS settings, third-party dashboards, env-based scripts).
4. Fix what code can fix using `references/fix-templates.md`. Make small reviewable edits. Never delete user features.
5. Re-run the scanner and report before and after.
6. Produce the report in the format below. List the items that code cannot fix as owner actions.

For the full instruction set use `audit_prompt.md` in this folder.

## The eleven checks

Checks 1 to 6 are the core US-centred list. Checks 7 to 11 were added for India and for privacy-law and contract coverage.

| # | Risk | Law and exposure (verified 2 Oct 2026) | What code can fix | Owner action |
|---|------|------------------------------------------|-------------------|--------------|
| 1 | No age screen at sign-up | COPPA (15 U.S.C. 6501-6506; 16 CFR Part 312). Civil penalty up to $53,088 per violation. | Neutral age gate (collect birth year or date. Do not hint at the cut-off). Block under-13 or route to verifiable parental consent. Delete data of blocked users. | Decide whether the app is directed to children. Write the privacy notice. |
| 2 | Fonts or assets loaded from Google servers | GDPR Art. 82 and German BGB 823/1004. LG Munchen I, 20 Jan 2022, Az. 3 O 17493/20: EUR 100 damages and an injunction. A civil court ruling affecting EU visitors only. | Self-host fonts. Remove fonts.googleapis.com and fonts.gstatic.com. Use next/font or fontsource. | None. |
| 3 | Session replay or keystroke capture | California Penal Code 631 and 637.2: $5,000 per violation or three times actual damages. Courts are split. Some dismiss replay claims where data is not read in transit. | Disable replay by default. Load only after opt-in consent. Mask all inputs. Honour Global Privacy Control. | Vendor contract. Privacy notice wording. |
| 4 | Marketing email without unsubscribe or postal address | CAN-SPAM Act (15 U.S.C. 7701 et seq.; 16 CFR Part 316). Up to $53,088 per email. | Footer with postal address. One-click unsubscribe link. List-Unsubscribe and List-Unsubscribe-Post headers. Suppression list honoured within 10 business days. | Obtain a real postal address or PO box registered with USPS. |
| 5 | Subscription checkout hides renewal terms | California Auto-Renewal Law, Bus. & Prof. Code 17600-17606. AB 2863 amendments apply from 1 Jul 2025. Under 17603 goods or services supplied without compliant consent can be treated as an unconditional gift. | Show price, frequency and renewal wording next to the pay button. Separate consent checkbox. Self-serve cancel online. Reminder emails. | Review terms of service. Confirm refund policy. |
| 6 | User uploads with no DMCA agent | 17 U.S.C. 512(c)(2) safe harbor needs a registered designated agent. Statutory damages of $750 to $30,000 per work and up to $150,000 if willful (17 U.S.C. 504(c)). Registered works only. | DMCA policy page. Report-infringement form or address. Counter-notice flow. Repeat-infringer policy. | Register the agent at dmca.copyright.gov (fee $6. Renew every 3 years). |

## Checks 7 to 11 and the India overlay

| # | Risk | Law | What code can fix | Owner action |
|---|------|-----|-------------------|--------------|
| 7 | No privacy notice or data-subject rights path | India DPDP Act 2023 and DPDP Rules 2025 (notice and consent duties apply from 14 May 2027). CCPA/CPRA in California ($2,500 or $7,500 per violation). | Privacy page linked in footer and at every collection point. Consent record. Withdraw-consent and delete-account controls. Breach contact. | Appoint a contact. Prepare breach response. Check whether CCPA or DPDP thresholds apply. |
| 8 | User-content platform with no Grievance Officer | India IT Act s.79 and IT Rules 2021 (Rule 3 due diligence). Copyright Rules 2013 r.75. | Publish terms and privacy policy. Name a Grievance Officer with contact details. Complaint form with 24 hour acknowledgement and 15 day resolution tracking. | Appoint a real person resident for service of notices. |
| 9 | Dark patterns | India Consumer Protection Act 2019 and Dark Patterns Guidelines 2023 (CCPA fined PhysicsWallah Rs 5 lakh and McAfee India Rs 1 lakh on 3 Jun 2026). FTC Act s.5. California ARL. | Remove pre-ticked consent boxes. Remove fake countdowns and confirm-shaming copy. Make cancel as easy as sign-up. | Review marketing copy. |
| 10 | No Terms of Service or no clear acceptance step | Indian Contract Act 1872. IT Act s.10A (electronic contracts valid). Browsewrap is weak and clickwrap is strong. CPA 2019 can void unfair terms. | Unticked I agree checkbox beside links to Terms and Privacy. Log timestamp and terms version. | Lawyer review of liability cap and governing law and arbitration. |
| 11 | No visible DPDP engineering controls | DPDP Act s.8 and Rules 6 to 8 and 14. Security safeguards failure up to Rs 250 crore. Breach non-notification up to Rs 200 crore. | Encryption and hashing. Audit logs kept one year. Breach contact and runbook. Retention and purge job. Consent log. DPO or privacy contact. | Processor contracts. Breach drill. DPO appointment. |

India overlay on checks 1 to 6:
- Check 1: India defines a child as under 18 and requires verifiable parental consent. It bans tracking and targeted advertising aimed at children.
- Check 4: India has no CAN-SPAM equivalent for email. DPDP consent governs marketing to identifiable people. TCCCPR governs SMS and voice.
- Check 5: for Indian cards and UPI the RBI e-mandate framework needs one-time authentication and a pre-debit notice at least 24 hours before each debit.
- Check 6: India has no agent registry. Safe harbour turns on IT Rules compliance and prompt action on court or government orders.

DPDP duties beyond consent and privacy policy (the "other 20 points"): grounds for processing (s.4) and legitimate uses (s.7) and processor contracts (s.8(2)) and accuracy (s.8(3)) and security safeguards (s.8(5) and Rule 6) and breach notification (s.8(6) and Rule 7: individuals and the Board without delay and a detailed Board report within 72 hours) and erasure and retention (s.8(7) and Rule 8: 48 hours notice and one year log retention) and children (s.9 and Rule 10) and access (s.11) and correction and erasure (s.12) and grievance (s.13 and Rule 14: not more than 90 days) and nominee (s.14) and cross-border transfer (s.16) and Significant Data Fiduciary duties (s.10 and Rule 13). Map in `references/dpdp-obligations.md`.

Owner-only checklist (code cannot show these): trademark clearance (IP India free public search Classes 9 and 35 and 42. USPTO fee USD 350 per class). DMCA agent. Processor contracts. Breach drill. GDPR Article 3(2) and Article 27 representative. CCPA thresholds (USD 26,625,000 revenue or 100,000 consumers or 50 percent revenue from selling or sharing).

Full tables with confidence markers are in `references/laws-india.md` and `references/laws-us.md`. Read them before quoting any figure to a client.

## Calibration notes (do not skip)

- Penalty figures are statutory maxima and not typical outcomes. Say so.
- The FTC announced no inflation adjustment for 2026. The 2025 amount of $53,088 remains in force (Federal Register, 15 Sep 2026).
- COPPA applies to operators of child-directed services and to operators with actual knowledge that they collect data from under-13 users. An age gate is mitigation and not immunity.
- The Munich ruling binds no US court. It matters if the app serves EU visitors.
- CIPA session replay theories are contested. Some courts require interception in transit.
- Rule 7 breach timing: individuals and the Board are told without delay and the detailed Board report is due within 72 hours. One secondary guide wrongly gives 72 hours for individuals. Use the rule text.
- DPDP s.17(3) lets the Government exempt startups from some duties but do not assume an exemption exists without a notification.
- DMCA statutory damages need timely copyright registration by the rightsholder. The safe harbor protects the platform only if all 512 conditions are met (agent, takedown process, repeat-infringer policy, no actual knowledge).

## Output format

Return a table of findings (check, status, severity, file and line evidence, fix applied or owner action) followed by sections: What was changed. What the owner must still do. Residual risk. End with the line: "This is a checklist and not legal advice. Laws differ by state and country."

## Sources

- FTC, 2025 civil penalty adjustment: https://www.ftc.gov/news-events/news/press-releases/2025/02/ftc-publishes-inflation-adjusted-civil-penalty-amounts-2025
- Federal Register, no 2026 adjustment: https://www.federalregister.gov/documents/2026/09/15/2026-18853/civil-penalty-inflation-adjustments
- FTC CAN-SPAM guide: https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business
- California B&P 17602: https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=BPC&sectionNum=17602
- California B&P 17603: https://california.public.law/codes/business_and_professions_code_section_17603
- Copyright Office DMCA directory FAQ: https://www.copyright.gov/dmca-directory/faq.html
- LG Munchen I, 3 O 17493/20: https://www.activemind.legal/guides/ruling-google-fonts/
- CIPA, Penal Code 637.2: https://www.recordinglaw.com/us-laws/federal-recording-laws/cipa-california-invasion-of-privacy-act/
- PIB, DPDP Rules 2025 notified: https://www.pib.gov.in/PressReleasePage.aspx?PRID=2190655&reg=48&lang=2
- CCPA India, dark patterns action (3 Jun 2026): https://www.pib.gov.in/PressReleasePage.aspx?PRID=2268302&reg=3&lang=1
- CCPA India guidelines: https://doca.gov.in/ccpa/guidelins.php
- TRAI, TCCCPR 2018: https://www.pib.gov.in/PressReleasePage.aspx?PRID=2153527&reg=48&lang=2
- Intermediary liability, Indian copyright: https://www.khuranaandkhurana.com/intermediary-liability-for-copyright-infringement
- Copyright Rules 2013 notice and takedown: https://spicyip.com/2013/04/guest-post-look-at-new-notice-and.html
- FTC negative option rulemaking status: https://www.gibsondunn.com/ftc-restarts-negative-option-rulemaking-after-eighth-circuit-vacatur-enforcement-under-rosca-continues/
- COPPA Rule amendments: https://www.mayerbrown.com/en/insights/publications/2025/04/ftc-announces-significant-amendments-to-coppa
- DPDP Rules text: https://www.dpdpa.com/dpdparules/rule6.html (and rule3 rule7 rule8 rule10 rule13 rule14)
- DPDP Act sections: https://www.dpdpact2023.com/chapter-2
- DPDP penalty schedule: https://dcomply.in/dpdp-penalty
- IP India public search: https://legalsuvidha.com/blog/ip-india-public-search
- USPTO fee 2026: https://usip.law/how-much-does-a-trademark-cost-2026-breakdown/
- Clickwrap in India: https://www.mondaq.com/india/contracts-and-commercial-law/1670160/clickwrap-browsewrap-and-negotiated-saas-contracts-enforceability-in-india
- CCPA 2026 thresholds: https://secureprivacy.ai/blog/ccpa-requirements-2026-complete-compliance-guide
- GDPR Art. 3: https://gdpr-info.eu/art-3-gdpr/
- State website-tracking litigation 2026: https://btlaw.com/en/insights/alerts/2026/cipa-ecpa-website-tracking-privacy-litigation-in-2026
