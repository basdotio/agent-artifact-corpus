# Review rules

Checked against the primary sources on **2026-10-03**. These are review prompts,
not automatic fixes. Apply model-specific guidance only to the named model and
workflow. A newer model does not make an instruction obsolete.

KEEP preserves content; REWRITE preserves its intended requirement; MOVE changes
its location; DELETE removes a demonstrated redundancy; ADD supplies a missing
requirement; HOLD records uncertainty without editing. Every edit needs a reviewed
diff. If applicability or the original purpose is unclear, choose HOLD.

| ID | Candidate | Action and condition | Source / scope |
| --- | --- | --- | --- |
| U01 | Updates after a fixed number of tool calls | HOLD, then consider DELETE after checking useful updates remain. Keep communication requirements. | [A02](sources.md#a02); Opus migration guidance says to try removal. |
| U02 | Generic encouragement to think carefully | HOLD, then consider DELETE if it serves no measured need. | [A01](sources.md#a01); Opus 5.5 chat system prompts, not every coding workflow. |
| U03 | Requests to reproduce internal reasoning | REWRITE toward concise rationale, assumptions, and evidence. Keep required explanations. | [A01](sources.md#a01); Opus 5.5 thinking-disabled migration. |
| U04 | Workarounds for disabled thinking | HOLD until the original workaround and model are known; DELETE only when obsolete. | [A01](sources.md#a01); Opus 5.5. |
| U05 | Reading every document before any edit | REWRITE as pointers tied to relevant tasks. KEEP required policy reads. | [O01](sources.md#o01); Astra guidance. |
| U06 | Routine recipes in general instructions | MOVE or REWRITE detail that applies to a narrower task. KEEP non-obvious recovery procedures. | [O01](sources.md#o01), [A03](sources.md#a03). |
| U07 | Skill descriptions matching entire domains | REWRITE with concrete triggers and exclusions. | [O02](sources.md#o02); skill selection guidance. |
| U08 | Vague testing reminders | REWRITE using verified commands and scope. KEEP mandatory checks; HOLD if commands are unknown. | [A04](sources.md#a04); repository instructions. |
| U09 | Repeated requirements | DELETE only a redundant, unprotected copy when every intended host still receives the rule. | [A03](sources.md#a03); confirm loading separately. |
| U10 | Approval, security, privacy, cost, identity, production, or destructive-action boundaries | KEEP verbatim, including scope and exceptions. HOLD conflicts for the owner. | Project invariant; provider simplification advice does not authorize weaker boundaries. |
| U11 | No observable completion condition | ADD concrete acceptance criteria and real stopping conditions. | [O01](sources.md#o01), [A01](sources.md#a01); long-running tasks. |
| U12 | Vague objections to generic visual design | REWRITE as concrete project preferences supported by examples. | [A01](sources.md#a01); Opus 5.5 frontend guidance. |
| U13 | Aggressive tool or skill trigger language | REWRITE only when it causes unnecessary invocation. KEEP protected requirements unchanged. | [A05](sources.md#a05); Opus 4.5/4.6 trigger guidance, not a ban on capitals. |
| U14 | Learned notes mixed with shared requirements | HOLD. A scoped reference may suit notes; never replace shared policy with personal auto-memory. | [A03](sources.md#a03), [A04](sources.md#a04); memory and policy differ. |

For all rules, preserve protected constraints and their surrounding scope.
Do not move or deduplicate them. KEEP exact commands, architecture facts, and
instructions that prevent a documented failure. Record that evidence when it
overrides a candidate pattern.

Moving text into an eagerly loaded import may improve organization without
reducing context. A proposed MOVE needs a verified destination, discovery path,
and loading behavior. Never infer these from a filename alone.

Fewer characters do not establish better task results. Report measured file
changes separately from host loading and behavior, and cite the source's actual
scope for each finding.
