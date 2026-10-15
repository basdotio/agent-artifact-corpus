# DPDP Act 2023 and Rules 2025: developer obligations map (position as at 4 Oct 2026)

This file goes beyond the basics (consent, privacy policy, delete on request). It lists the other duties that carry the large penalties. Section numbers refer to the Act. Rule numbers refer to the DPDP Rules 2025 notified on 14 Nov 2025.

Confidence key: **V** = read from a fetched source on 4 Oct 2026 (Act text mirror or rule-by-rule page). **K** = known to the author but not re-read. The Gazette is the only authoritative text. Check it before quoting a client.

Commencement: Rule 4 (Consent Managers) from 14 Nov 2026. Rules 3 and 5 to 16 and 22 to 23 from 14 May 2027. See `laws-india.md`.

## A. Obligations table

| # | Obligation | Provision | What it requires | Engineering action | Penalty ceiling | Conf. |
|---|---|---|---|---|---|---|
| 1 | Grounds for processing | s.4 | Process only for a lawful purpose with consent or under a certain legitimate use | Record the lawful ground for each data field and purpose | Rs 50 crore (residual) | V |
| 2 | Notice | s.5. Rule 3 | Standalone notice in plain language with an itemised list of data and the specific purpose and a link to withdraw consent and exercise rights and complain to the Board. Available in the 22 Schedule VIII languages on request | Notice screen shown before the consent control. Link to the withdrawal page. Language switch | Rs 50 crore | V |
| 3 | Valid consent | s.6. Rule 3 | Free and specific and informed and unconditional and unambiguous with a clear affirmative act. Withdrawal as easy as giving. Stop processing within a reasonable time after withdrawal | Unticked boxes. One purpose per consent. Consent log with timestamp and notice version. One-click withdraw. Job that stops processing | Rs 50 crore | V |
| 4 | Certain legitimate uses | s.7 | Voluntary provision for a specified purpose. State benefits and functions. Legal obligation. Court orders. Medical emergency. Public health. Disaster response. Employment safeguards | Do not stretch s.7(a) beyond the stated purpose. Keep a note of the clause relied on | Rs 50 crore | V |
| 5 | Fiduciary accountability | s.8(1) | The fiduciary is responsible for all processing including by processors. Contracts cannot shift liability | Vendor register. Do not rely on the processor contract as a shield | Rs 50 crore | V |
| 6 | Data processor contract | s.8(2). Rule 6 | A valid contract must exist before a processor handles data. It must carry the Rule 6 security terms | Signed DPA with every analytics or email or hosting or AI vendor. List sub-processors | Rs 250 crore if linked to safeguard failure | V |
| 7 | Data accuracy | s.8(3) | Ensure completeness and accuracy and consistency when data is used to decide about the person or shared with another fiduciary | Validation on input. Correction flow. Do not feed stale data to automated decisions | Rs 50 crore | V |
| 8 | Technical and organisational measures | s.8(4) | Appropriate measures to observe the Act | Privacy by design review in the release checklist. Role-based access. Data minimisation | Rs 50 crore | V |
| 9 | Reasonable security safeguards | s.8(5). Rule 6 | Encryption or masking or tokens. Access control. Logs and monitoring to detect unauthorised access. Retain logs and data for one year. Backups and continuity. Processor contract terms | TLS and encryption at rest. Hash passwords. Least privilege. Audit log kept 12 months. Tested backups | **Rs 250 crore** | V |
| 10 | Breach notification | s.8(6). Rule 7 | Tell each affected person without delay. Tell the Board without delay. Detailed report to the Board within 72 hours (extendable if the Board allows) | Incident runbook. Contact list. Template for the person and the Board. Breach register | Rs 200 crore | V |
| 11 | Erasure and retention | s.8(7). Rule 8 | Erase when consent is withdrawn or the purpose ends unless a law requires retention. Make processors erase too | Retention schedule per data class. Scheduled purge job. Delete cascades to vendors | Rs 50 crore | V |
| 12 | Pre-erasure notice | Rule 8. Third Schedule | For listed large platforms (e-commerce 2 crore or more users. Online gaming 50 lakh or more. Social media 2 crore or more) erase after 3 years of inactivity with at least 48 hours notice | Inactivity tracker and warning email 48 hours before purge | Rs 50 crore | V |
| 13 | Log retention | Rule 8(3) | Keep personal data and traffic data and processing logs for at least one year for the Seventh Schedule purposes unless another law requires longer | Do not purge audit logs before 12 months even if the user deletes the account | Rs 50 crore | V |
| 14 | Contact of the DPO or answering person | s.8(9). Rule 14 | Publish business contact details of the DPO or a person who can answer questions | Contact block in the privacy page and the app | Rs 50 crore | V |
| 15 | Grievance redressal | s.8(10). s.13. Rule 14 | Effective mechanism. Publish the response time (not more than 90 days). Exhaust internal remedy before the Board | Grievance form with ticket id and timer | Rs 50 crore | V |
| 16 | Children's data | s.9. Rule 10 | Verifiable parental consent before processing a child's data (under 18). No tracking or behavioural monitoring or targeted ads aimed at children. No detrimental processing | Age gate at 18 for India. Parent verification through reliable held details or DigiLocker or an authorised virtual token. Switch off ad SDKs for minors | **Rs 200 crore** | V |
| 17 | Children exemptions | Rule 12. Fourth Schedule | Exemptions for clinical care and education bodies and crèches and school transport and child safety location and email-only accounts for stated purposes only | Document the exemption relied on | n/a | V |
| 18 | Significant Data Fiduciary duties | s.10. Rule 13 | Resident DPO. Independent auditor. Annual DPIA and audit with report to the Board. Algorithmic due diligence. Data localisation if notified | Only if designated. Plan DPIA calendar | Rs 150 crore | V |
| 19 | Right to access | s.11 | Give a summary of personal data processed and the identities of others it was shared with | Account page with data export and sharing summary | Rs 50 crore | V |
| 20 | Correction and erasure | s.12 | Correct or complete or update on request. Erase unless retention is needed for the purpose or law | Edit profile and delete account flows | Rs 50 crore | V |
| 21 | Right to nominate | s.14. Rule 14 | Principal may nominate another person to act on death or incapacity | Nominee field and process in terms | Rs 50 crore | V |
| 22 | Duties of the Data Principal | s.15 | No impersonation. No false grievances. Give only verifiable information | Add to terms. Verify identity before acting on requests | Rs 10,000 on the principal | V |
| 23 | Cross-border transfer | s.16. Rule 15 | Allowed except to countries the Government restricts by notification. Stronger sectoral rules prevail | Map flows to US analytics and fonts and AI APIs. Watch for a negative list | Rs 50 crore | V |
| 24 | Consent Managers | s.6(7). Rule 4 | Registered India-incorporated entity that manages consent for principals | Optional integration. Rule 4 from 14 Nov 2026 | Rs 50 crore | V |
| 25 | Exemptions | s.17 | Several carve-outs (legal claims and courts and offences and foreign-resident contracts and mergers and IBC defaulter assessment). s.17(3) lets the Government exempt classes including startups from ss.5 and 8(3) and 8(7) and 10 and 11 | Do not assume a startup exemption. Check the notification status before relying on it | n/a | V for text. K for current notification status |

## B. Penalty schedule (s.33 and Schedule)

| Breach | Maximum |
|---|---|
| Failure to keep reasonable security safeguards (s.8(5)) | Rs 250 crore |
| Failure to notify a breach (s.8(6)) | Rs 200 crore |
| Breach of children's obligations (s.9) | Rs 200 crore |
| Breach of Significant Data Fiduciary duties (s.10) | Rs 150 crore |
| Breach of any other provision of the Act or Rules | Rs 50 crore |
| Breach of Data Principal duties (s.15) | Rs 10,000 |
| Breach of a voluntary undertaking (s.32) | Up to the amount for the underlying breach |

The Board weighs nature and gravity and duration and impact and gain and repetition and mitigation (s.33(2)). Appeals go to TDSAT within 60 days. These are ceilings and not typical outcomes. All V.

## C. Source discrepancies to know about

- One secondary guide (Seclore) says affected individuals must be told within 72 hours. The rule text (dpdpa.com Rule 7 page) says individuals are told without delay. Only the detailed Board report has the 72 hour limit. Use the rule text.
- A secondary guide says erasure notice is within 48 hours after erasure starts. Rule 8 says the notice comes at least 48 hours before the erasure date.
- Phase-in dates differ between guides (13 or 14 Nov and May). Use the Gazette.

## D. Sources

- Act sections 4 to 10: https://www.dpdpact2023.com/chapter-2
- Act sections 11 to 15: https://www.dpdpact2023.com/chapter-3
- Act sections 16 and 17: https://www.dpdpact2023.com/chapter-4
- Section 8 sub-sections: https://www.dpdpa.com/dpdpa2023/chapter-2/section8.html
- Rule 3: https://www.dpdpa.com/dpdparules/rule3.html
- Rule 6: https://www.dpdpa.com/dpdparules/rule6.html
- Rule 7: https://www.dpdpa.com/dpdparules/rule7.html
- Rule 8: https://www.dpdpa.com/dpdparules/rule8.html
- Rule 10: https://www.dpdpa.com/dpdparules/rule10.html
- Rule 13: https://www.dpdpa.com/dpdparules/rule13.html
- Rule 14: https://www.dpdpa.com/dpdparules/rule14.html
- Rule-by-rule overview: https://ruleexpert.com/guides/dpdp-rules-2025/
- Third Schedule thresholds: https://www.miniorange.com/blog/data-retention-policy-dpdp-act/
- Penalty schedule: https://dcomply.in/dpdp-penalty
- Official: https://www.meity.gov.in and https://www.pib.gov.in/PressReleasePage.aspx?PRID=2190655&reg=48&lang=2
