ASK DATE prerequisite: follow playbooks/research-and-memory.md#ask-date-rule.
Researcher establishes it before intake or research; later roles read scope.md.
Never ask the user for the date or infer it from model knowledge. Apply the
same source, two-date, freshness, reuse, and blocked-gate rules to this stage.

Build the selected design using the smallest stack that meets the approved brief.
First verify that a named mockup was selected and that its brand rules are available.

CHOOSE
- Read playbooks/choose-stack.md and name each requirement driving the decision.
- Prefer static HTML for a small site with no repeated publishing workflow.
- Use data records plus templates for repeated pages and derived metadata.
- Choose a framework only when actual routing, server, integration, or application
  needs justify its cost. Most informational sites do not need a framework.
- Do not add a CMS, page builder, analytics product, or paid service without a requirement.
- Record alternatives, dependencies, host constraints, and the next-page editing path
  in site-work/stack.md. Verify current APIs before writing against them.

LEARN CODING PRACTICE
- Run [prompts/13-coding-research.md](13-coding-research.md) for the exact selected
  stack and versions after CHOOSE and before IMPLEMENT.
- Read back site-work/coding-standards.md and record the rules learned before writing
  code. Current sourced standards are required; unresolved research blocks coding.

IMPLEMENT
- Keep content, shared rendering, assets, and generated output separate.
- Make the next page a data change wherever pages share a structure.
- Validate data before rendering. Trusted authoring can still contain broken values.
- Use one explicit state function for dates, availability, badges, and actions.
- Omit links and embeds whose required identifiers are empty or invalid.
- Escape attribute values structurally; validate URL schemes separately.
- Serialize script-bound structured data with a safe JSON helper, not bare stringify.
- Use responsive image variants, measured dimensions, and the original fallback.
- Self-host licensed woff2 fonts. Load external embeds only after an accessible click.
- Preserve useful content without animation and with JavaScript unavailable.
- Derive sitemap, metadata, and discovery text from the same validated content source.

VERIFY
- Build from a clean environment using the documented command.
- Check generated HTML, not just source templates.
- Exercise empty IDs, quotes, ampersands, script-terminator text, long copy,
  missing optional assets, and date boundaries using synthetic records.
- Check the selected design at mobile and desktop sizes and preserve the evidence.
- Apply [checklists/code-quality.md](../checklists/code-quality.md) against
  site-work/coding-standards.md and record command output and code-review evidence.
- Do not deploy. Continue through experience, discovery, headers, and audit gates.

HANDOFF
Return source locations, the exact artifact built, checks run, known limitations,
and which stage owns each remaining issue. Never label unexecuted tests as passed.

EVIDENCE
Never report a measured, saved, installed, or deployed result without evidence.
Apply the stage route and named checks in manifest.json before handing off.
