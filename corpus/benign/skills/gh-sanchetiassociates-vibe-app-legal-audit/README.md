# vibe-app-legal-audit

A free, open-source pre-launch legal-exposure scanner and Claude skill for web and mobile apps (especially AI-generated "vibe coded" apps). It scans a codebase for eleven patterns that create per-user or per-email statutory exposure under **US**, **Indian** and **EU** rules. Then it guides the fixes that code can solve.

> **This is a checklist and not legal advice.** Laws differ by state and country. See [DISCLAIMER.md](DISCLAIMER.md).

## What it checks

| # | Check | Main law |
|---|---|---|
| 1 | Sign-up with no age screen | COPPA (US). DPDP Act 2023 s.9 (India: under 18) |
| 2 | Fonts or assets loaded from third-party servers | GDPR Art. 82. LG Munchen I, 3 O 17493/20 |
| 3 | Session replay or keystroke capture without gated consent | California CIPA and other state wiretap laws |
| 4 | Marketing email without unsubscribe or postal address | CAN-SPAM (US). DPDP consent (India) |
| 5 | Subscription checkout without clear renewal terms | California ARL. ROSCA. India dark-patterns rules. RBI e-mandate |
| 6 | User uploads with no DMCA policy or agent | 17 U.S.C. 512. India IT Act s.79 and Copyright Rules 2013 |
| 7 | No privacy notice or data-rights path | DPDP Act and Rules 2025. CCPA/CPRA |
| 8 | No Grievance Officer for user-content platforms | India IT Rules 2021 |
| 9 | Dark patterns in the UI | India Dark Patterns Guidelines 2023. FTC Act s.5 |
| 10 | Accounts with no Terms of Service or no clear acceptance step | Indian Contract Act 1872. IT Act s.10A. US clickwrap case law |
| 11 | No visible DPDP engineering controls (security safeguards, breach path, retention, consent record, contact) | DPDP Act s.8. Rules 6, 7, 8 and 14 |

The scan report ends with an owner-only checklist for items code cannot show (trademark clearance, DMCA agent, processor contracts, GDPR and CCPA applicability).

Law summaries with confidence markers are in [references/laws-us.md](references/laws-us.md) and [references/laws-india.md](references/laws-india.md). A full map of DPDP duties beyond consent and privacy policy (processor contracts, accuracy, security safeguards, breach notification, retention, children, grievance and more) with the Rs 250 crore penalty mapping is in [references/dpdp-obligations.md](references/dpdp-obligations.md). Fix snippets are in [references/fix-templates.md](references/fix-templates.md).

## Quick start

```bash
git clone https://github.com/SanchetiAssociates/vibe-app-legal-audit.git
python vibe-app-legal-audit/scripts/scan.py /path/to/your/project --md audit.md --json audit.json
```

- Python 3.8 or later. No dependencies. It reads files only and makes no network calls.
- Exit code `1` means at least one HIGH finding. Exit code `0` means none.
- The scanner is regex based. Every hit is a lead that needs a human check. A PASS means nothing was found and not that the app is compliant.

## Use as a Claude skill

Copy this folder to `~/.claude/skills/vibe-app-legal-audit/` (Claude Code) or upload the folder as a skill in Claude settings. Then ask: "Audit this app for legal exposure". Claude runs the scanner, confirms each lead by reading the code, applies the code-level fixes and lists the owner actions that code cannot do (for example registering a DMCA agent).

The full instruction set is in [audit_prompt.md](audit_prompt.md). You can paste it into any assistant that can read your project.

## Use in GitHub Actions

```yaml
- uses: actions/checkout@v4
- uses: SanchetiAssociates/vibe-app-legal-audit@v1
  with:
    path: .
    fail-on-high: "true"
```

## Limits

- Heuristic detection. Expect false positives and false negatives.
- It cannot see third-party dashboards, CMS settings, build output or server config.
- Penalty figures in the references are statutory maximums and not typical outcomes.
- Law changes. Check dates in the reference files and verify items marked K on official portals.

## Contributing

Issues and pull requests are welcome. Good contributions: new detection patterns with a test fixture and corrections to the law references with a primary-source link. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT. See [LICENSE](LICENSE).
