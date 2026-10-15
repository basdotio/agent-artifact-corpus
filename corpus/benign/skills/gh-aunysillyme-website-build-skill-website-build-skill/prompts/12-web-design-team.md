ASK DATE prerequisite: follow playbooks/research-and-memory.md#ask-date-rule.
Researcher establishes it before intake or research; later roles read scope.md.
Never ask the user for the date or infer it from model knowledge. Apply the
same source, two-date, freshness, reuse, and blocked-gate rules to this stage.

Run option 2, Give me the team, using the human's recorded install choice.
TEAM: one command installs the seven workers' files; you open each session yourself and carry the handoffs between them. Researcher goes first.
Needs Claude Code, Codex, Hermes, Antigravity, or Grok Bot. Follow the setup line for that host.

Every agent runs its own research pass before it touches your site, so it works from what is
true as of the date of your ask, not from what its model happens to remember.

Researcher does the full sweep first. Every other role learns the saved library,
then tops up only its own domain. Research, then learn, then ingest, then execute.

SET UP
- Read roles/researcher.md first, then roles/coordinator.md, roles/designer.md,
  roles/graphics.md, roles/builder.md, roles/optimizer.md, roles/reviewer.md,
  and templates/handoff.yaml. Use each complete body, not these short summaries.
- The human opens Website Researcher first, then Website Coordinator,
  Website Designer, Website Graphics, Website Builder, Website Optimizer, and
  Website Reviewer as separate sessions, Bots, or terminals. Coordinator works
  only after the research gate. Use available session controls and complete role files.
- The human checks each session reference and obtains seven setup acknowledgements.
  These confirm receipt of instructions, not permission to start downstream work.
- A role label in one conversation is option 1. Record SOLO and use prompts/00-start.md
  if separate workers cannot be reached. A same-family team remains a team but
  cannot pass independent review. Respect host concurrency limits.
- Read the host adapter and receipt. The installer supplies role files and bundles;
  the human opens sessions, checks trust and tools, and supplies each worker's files.
  Pending discovery, trust, tools or independent review checks remain explicit limits.
- Supply the request, authorized workspace, source assets, and tools to Researcher.
  All other roles wait. Carry the complete packets using the manual setup below;
  actual host loading remains UNVERIFIED until tested.

RESEARCHER
- Own site-work/research/library/ and handoffs/researcher/; own both research resources.
- Run prompts/01-website-deep-research.md, with the inactive graphics original as
  provenance. Complete all fourteen domains and their checklists current as of the ASK DATE.
- Save the library before any other role works. Gate: the library exists on disk,
  every domain this project touches has a substantive file and checklist, and every
  acted-on claim has an opened source URL, a publication/update date or explicit unknown, and an access date on or after the ASK DATE. UNVERIFIED cannot pass a claim.
- Include README headlines, source/disagreement ledgers, user surprises, memory
  proposal/receipt, and earliest staleness/recheck markers. Proposal is not saved memory.
- Hand research-to-coordinator over only after the gate passes. Accept corrections
  from specialists, update canonical evidence, and invalidate affected old receipts.

COORDINATOR
- Start after Researcher's passing receipt; read the files and verify that gate.
- Learn the named library files and top up current host/worker capability questions.
- Own brief, capabilities, stage state, ownership, gate acceptance, and integration.
- Record routes, family evidence, tools, and ownership after research acceptance.
- Assign bounded handoffs and open every returned artifact before accepting a gate.
- Capture Reviewer's packet verbatim. Scope changes return to Researcher first.

DESIGNER
- After research, learn the library's design/UX, graphics/rights and accessibility
  files and checklists; top up only this brief's current design/browser questions.
- Own brand extraction, tokens, contrast, three mockups, and selection record.
- Obtain user confirmation of inferred rules and a named design before site code.

GRAPHICS
- After research, learn graphics/rights and experience/performance files; top up
  chosen-tool/tier rights, current destination sizes, safe zones, and asset licenses.
- Work with Designer; own assets, cards, icons, inspected exports and rights evidence.
- Deliver immutable revisions with measured dimensions and verified intended-use rights.

BUILDER
- After mockup selection, learn codebase/stack, accessibility/performance and
  security/delivery and language/coding research; top up chosen APIs, headers, and measurement rules.
- After Choose and before Build, run prompts/13-coding-research.md and read
  site-work/coding-standards.md; apply checklists/code-quality.md to the implementation.
- Own stack choice, implementation, performance, headers, build evidence and release.
- Integrate Graphics and Optimizer outputs without editing their original sources.
- Prepare the immutable candidate/audit brief; reproduce findings and test fixes.

OPTIMIZER
- With and after Builder, learn search/answers and measurement research; top up
  current schema support, crawler/citation behavior, llms.txt and indexing APIs.
- Own SEO/AEO inputs, schema, sitemap, llms.txt, answer-first content and validation.
- Hand discovery inputs to Builder, then validate the rendered candidate.
- Claim neither indexing, received analytics nor schema validity without evidence.

REVIEWER
- Last before ship, use a different model family or return INTERNAL, gate BLOCKED.
- Learn the relevant library and top up current attack, accessibility and scanner facts.
- Review the fixed candidate read-only; return findings and research without edits.
- Check code against site-work/coding-standards.md and checklists/code-quality.md.
- Return reproducible evidence or an explicit scoped no-findings result.
- Apply checklists/ship.md ASK DATE checks to library and top-ups; reject undated,
  stale-access and stamped-but-unrevalidated claims as findings.

EVERY HANDOFF
Include stage, status, input_revision, artifact_revision, producer_role,
producer_model_family, artifacts, checks, limitations, next_owner,
changed_assumptions, and framing_reset. Use explicit empty lists where appropriate.
Attach actual files or complete contents; an inaccessible path is not a handoff.
Each writer saves site-work/handoffs/<role>/<stage>-<revision>.yaml. Reviewer returns
its receipt for Coordinator to capture at site-work/review/<revision>/handoff.yaml.
Every downstream role reads its WHAT YOU MUST LEARN library filenames first and
saves a learning/checklist receipt before execution. Its WHAT YOU MUST RESEARCH
is a domain top-up; flag stale/wrong claims back to Researcher and pause affected work.
Coordinator alone accepts gates in site-work/status.md; authors keep their receipts.
Changed inputs invalidate affected evidence. Failed gates stop dependent work.
If group messages cannot carry images, attach directly to each receiving worker.
Complete one independent review round; verify reproduced fixes through the harness.
Use playbooks/research-and-memory.md's degradation table for missing capabilities.
In SOLO do the Researcher's complete job first, save and reopen the library before
any design, and leave research BLOCKED if current search or disk persistence fails.
Finish each stage with its next concrete action and accountable owner.

EVIDENCE
Never report a measured, saved, installed, or deployed result without evidence.
Apply checklists/research.md before downstream dispatch and checklists/ship.md before release.

PORTABLE MANUAL SETUP
Use this setup for TEAM on every host. You open each session and carry every handoff.
Host loading, file access, tool enforcement and different-family availability remain
UNVERIFIED until the actual host/session checks succeed.
A missing host adapter does not authorize inventing a native file format or import API.

1. Open the host's verified worker/session creation surface, if available.
2. Create Researcher first, then Coordinator, Designer, Graphics, Builder, Optimizer,
   and Reviewer. Paste each full roles/<role>.md body, not this prompt's summary.
3. Supply SKILL.md, manifest.json and every linked resource as readable files or full
   labeled text. Give Researcher the inactive graphics archive for provenance only.
4. Get each worker's setup acknowledgement: received role, actual route, model family
   with evidence, tools, inaccessible files, and owned paths. Keep downstream work pending.
5. Give Reviewer a read-only candidate packet or verified read-only session. Broad
   inherited tools do not become restricted because role prose says read-only.
6. Deliver a bounded setup message to each session yourself. Relay addressed packets
   and attachments, and verify each receiving worker can open them.
7. Give the user's actual request, authorized workspace, assets and constraints to
   Researcher alone. It establishes ASK DATE and completes the library and gate first.
8. Relay its complete passing receipt and readable library to Coordinator. Coordinator
   reopens them before accepting research and releasing design/graphics assignments.

Preserve seven acknowledgements separately from research and work-readiness receipts.
A text-only group requires direct image attachments to each receiving visual reviewer.
Inaccessible files or routes keep the relevant handoff BLOCKED.
Completed file installation means the files are available; session setup is the human's next step.
No separate workers means SOLO; no independent family means independent review BLOCKED.
Never invent a platform capability to fill a setup gap.

