# Severity & Priority Guide

## Severity — how bad is the impact?

| Level | When to use | Examples |
|---|---|---|
| **Critical (Blocker)** | System down, data loss/corruption, security breach, direct financial loss, or a core flow fully blocked for everyone | Transfer completed without MFA · Duplicate charges · App crashes on login · Personal data exposed to another user |
| **High (Major)** | A main feature does not work or gives wrong results and there is **no reasonable workaround** | Cannot export statement · Wrong interest calculation · Payment fails for a specific card brand |
| **Medium (Minor)** | Feature partly fails, there **is a workaround**, or it affects a secondary flow | Filter ignores one criterion · Error message is misleading · Need to refresh the page to see update |
| **Low (Trivial)** | Cosmetic or text issues with no functional impact | Misaligned button · Typo · Wrong icon color |

Tie-breakers:
- Security, money or personal data involved → start at **Critical** and only lower it with a clear reason.
- Workaround exists but is not something a real user would figure out → treat as **no workaround**.
- Affects only one platform/browser → severity stays the same; the scope goes in the description.

## Priority — how soon should it be fixed?
Priority is a business decision (usually the PO's). The skill only **suggests** it.

| | High usage / visible | Low usage / hidden |
|---|---|---|
| **Critical / High severity** | Highest | High |
| **Medium / Low severity** | Medium | Low |

Raise priority when: there is a release deadline, a regulatory/compliance risk, a key customer is affected, or it blocks testing of other features.
