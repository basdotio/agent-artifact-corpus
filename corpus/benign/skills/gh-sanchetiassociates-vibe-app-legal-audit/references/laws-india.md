# Indian law map for the audit (position as at 4 Oct 2026)

Confidence key: **V** = read from a fetched source this session. **K** = established statute known to the author but not re-fetched. Verify every **K** line on the official portal before quoting it to a client. The Gazette text is the only authoritative source.

## A. Digital Personal Data Protection Act 2023 and DPDP Rules 2025

| Item | Position | Conf. |
|---|---|---|
| Rules notified | 14 Nov 2025 (PIB press release 17 Nov 2025) | V |
| Phase 1 | Rules 1, 2 and 17-21 (definitions and the Data Protection Board) effective on publication | V |
| Phase 2 | Rule 4 (Consent Manager registration) effective 14 Nov 2026 | V |
| Phase 3 | Rules 3 and 5-16 and 22-23 (notice, consent, children, breach, security, erasure, cross-border) effective 14 May 2027 | V |
| Note | One source gives 13 Nov and 13 May as the dates. Confirm against the Gazette. No amendment shortening the period was found | V |
| Child | Under 18 years. Verifiable parental consent before processing (s.9 and Rule 10). Exemptions for classes such as healthcare and education services | V |
| Children: prohibited | Tracking or behavioural monitoring of children and targeted advertising directed at them | V |
| Notice | Separate, clear notice stating the specific purpose of collection | V |
| Breach | Intimate affected individuals without delay and report to the Board | V |
| Rights requests | Respond to access, correction and erasure requests within 90 days | V |
| Penalty ceilings | Security safeguards failure: Rs 250 crore. Breach non-notification: Rs 200 crore. Children's provisions: Rs 200 crore. Significant Data Fiduciary duties: Rs 150 crore. Data Principal duties: Rs 10,000. Other violations: Rs 50 crore | V |

Rule numbers confirmed on 4 Oct 2026: Rule 3 notice. Rule 4 Consent Managers. Rule 6 security safeguards. Rule 7 breach intimation. Rule 8 erasure and log retention. Rule 10 children. Rule 12 children exemptions (Fourth Schedule). Rule 13 Significant Data Fiduciaries. Rule 14 rights and grievance. Rule 15 cross-border transfer. Full duty-by-duty table: see `dpdp-obligations.md`.

Audit implications:
- Check 1 (age gate): India sets the threshold at 18 and not 13. A US-style neutral gate must block or route under-18 users to verifiable parental consent from 14 May 2027.
- Check 3 (session replay): replay and analytics scripts are processing of personal data. They need a purpose-specific notice and consent or another lawful ground.
- Check 4 (email): marketing email to an identifiable person needs consent under the Act. See section B for why India has no CAN-SPAM equivalent.
- New check 7: privacy notice, consent record, withdrawal path, erasure path and breach process.

## B. Marketing communications

| Item | Position | Conf. |
|---|---|---|
| Email spam | India has no standalone CAN-SPAM style statute for email. Section 66A of the IT Act was struck down in Shreya Singhal v Union of India (2015) | K |
| SMS and voice | TRAI Telecom Commercial Communications Customer Preference Regulations 2018 (TCCCPR) with a Feb 2025 amendment extending the spam complaint window from 3 to 7 days. Enforced through telecom access providers | V |
| TCCCPR and email | The PIB note does not say email is covered. Treat TCCCPR as SMS and voice only unless confirmed | V |
| Misleading advertising | Consumer Protection Act 2019. The CCPA can penalise misleading advertisements (s.21: up to Rs 10 lakh and up to Rs 50 lakh for repeat contraventions) | K |

Practical rule: if the audience includes India apply DPDP consent standards. If it includes the US also apply CAN-SPAM. The stricter control wins.

## C. Consumer protection and dark patterns (Check 5)

| Item | Position | Conf. |
|---|---|---|
| Statutes | Consumer Protection Act 2019. Consumer Protection (E-Commerce) Rules 2020. Guidelines for Prevention and Regulation of Dark Patterns 2023 | V |
| Dark patterns named in enforcement | Basket sneaking. Confirm shaming. Forced action. Interface interference. Trick questions | V |
| Full Annexure list | 13 patterns including subscription trap, drip pricing, false urgency, nagging, bait and switch, disguised advertisement, SaaS billing and rogue malware. Read the Annexure at doca.gov.in before relying on the list | K |
| Enforcement | CCPA release of 3 Jun 2026: Rs 5 lakh on PhysicsWallah (pre-selected donations and misleading free offers) and Rs 1 lakh on McAfee Software India (deceptive renewal interface) | V |
| Self-audit | CCPA advisory asked e-commerce platforms to self-audit for dark patterns within 3 months | V |
| RBI recurring payments | One-time e-mandate registration with additional factor authentication. Pre-debit notice at least 24 hours before each debit. No OTP up to Rs 15,000 after registration. Up to Rs 1 lakh for insurance, mutual fund and credit card bill categories. Customer can modify, pause or revoke at any time. A 2026 e-mandate framework was reported effective 1 May 2026. Confirm on rbi.org.in | V |

Audit implications: pre-ticked boxes, hidden renewal terms, hard-to-find cancel paths and fake urgency are all red flags. For Indian cards and UPI the provider must support the RBI e-mandate flow and pre-debit alerts.

## D. User uploads and copyright (Check 6)

| Item | Position | Conf. |
|---|---|---|
| Liability baseline | Copyright Act 1957 s.51(a)(ii): no liability where the person was not aware and had no reasonable ground to believe the communication would infringe | V |
| Intermediary safe harbour | IT Act 2000 s.79. Lost if the intermediary fails to remove content expeditiously after actual knowledge or a government or court notification (s.79(3)) | V |
| Actual knowledge | Specific knowledge of identified content. General awareness is not enough. MySpace Inc v Super Cassettes Industries Ltd (Del HC 2016) | V |
| Takedown on orders | Shreya Singhal v Union of India (2015): removal duty arises on court order or government notice and not on private complaint alone | V |
| Copyright Rules 2013 r.75 | Complaint with work identity, proof of ownership, statement of infringement and location. Intermediary may disable access within 36 hours if satisfied the copy infringes. Complainant must sue within 21 days or access may be restored | V |
| IT Rules 2021 duties | Publish rules, privacy policy and user agreement. Appoint a named Grievance Officer with published contact details. Acknowledge complaints within 24 hours and resolve within 15 days. Act on court or government orders within 36 hours. Preserve records for 180 days. Non-compliance forfeits s.79 protection | V |
| Rule numbering | The source cites rule 3(1)(b)-(c) and 3(1)(d). The grievance mechanism is commonly cited as rule 3(2). Check the exact rule numbers in the current consolidated text | V |
| Remedies | Civil remedies (s.55) and criminal penalties for infringement (s.63) under the Copyright Act | K |
| Damages | India has no US-style statutory damages schedule and no agent registry like the US Copyright Office directory | K |

Audit implications: a US DMCA page is helpful but not enough for Indian users. Add a named Grievance Officer with email and postal address and publish terms and a privacy policy. Keep a log of notices.

## E. Other Indian provisions to cite carefully

- IT Act 2000 ss.43 and 66 (unauthorised access and computer-related offences). DPDP s.44(2) is meant to omit s.43A. Check the commencement notification for s.44. **K**
- Cross-border transfer under DPDP s.16: allowed except to countries the Government restricts by notification. Relevant to fonts and analytics sent to US servers. **K**
- No Indian court decision equivalent to the Munich Google Fonts ruling was found. An IP address can be personal data under DPDP where the person is identifiable in relation to it. This is the author's reading and needs professional confirmation. **K**
- GST: invoices for subscriptions must carry the correct HSN or SAC code and GSTIN. This sits outside the scanner checks but matters for any checkout.

## F. Terms of service and clickwrap (Check 10)

| Item | Position | Conf. |
|---|---|---|
| Statutes | Indian Contract Act 1872 (free and informed consent). IT Act 2000 s.10A (contracts formed electronically are valid). Indian Evidence Act 1872 s.65B (electronic records) | V |
| Clickwrap | Highly enforceable when terms are reachable at the click and the I agree action is clearly linked and the system logs identity and timestamp and device. Give conspicuous notice of auto-renewal and jurisdiction | V |
| Browsewrap | Footer-only links carry high risk with consumers. Courts may find no consensus ad idem | V |
| Unfair terms | No general unfair-contract statute but the Consumer Protection Act 2019 lets forums set aside unfair contract terms in consumer deals. Courts apply unconscionability to standard forms (Central Inland Water Transport Corporation v Brojo Nath Ganguly 1986) | V |
| Drafting | Limit unilateral variation to non-material changes. Use layered liability caps. Do not exclude liability for wilful misconduct. Arbitration and jurisdiction clauses need clear written consent and should not be one-sided | V |

Audit implication: every sign-up needs an unticked I agree checkbox or an equivalent affirmative step next to links to the Terms and Privacy Policy. Store acceptance with a timestamp and the terms version.

## G. Trademark clearance (owner action)

| Item | Position | Conf. |
|---|---|---|
| Statute | Trade Marks Act 1999. Registered marks get statutory infringement remedies. Unregistered marks are protected through passing off | K |
| Search tool | IP India public search at ipindiaonline.gov.in is free. Modes: wordmark and phonetic and Vienna code and applicant name | V |
| Classes for apps | Search Class 9 (software) and Class 35 (business services) and Class 42 (technology services) | V |
| Reading results | Registered and Advertised before Acceptance are high risk. Objected needs monitoring. Abandoned or Expired are lower risk but check for refiling | V |
| Action | Run phonetic and wordmark searches before naming. File in the classes you use. Also check domain and app stores and company names at mca.gov.in | V for search steps. K for filing advice |

## H. Official portals

- https://www.meity.gov.in (DPDP Act and Rules)
- https://doca.gov.in/ccpa/guidelins.php (CCPA guidelines)
- https://www.rbi.org.in (e-mandate circulars)
- https://trai.gov.in (TCCCPR)
- https://copyright.gov.in (Copyright Rules 2013)
- https://www.mca.gov.in (company law matters)
