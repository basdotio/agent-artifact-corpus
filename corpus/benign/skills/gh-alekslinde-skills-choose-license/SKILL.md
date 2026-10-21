---
name: choose-license
description: Choose the right licence for a project, or for each part of it, by auditing the repository first and then asking the owner only what the code cannot answer. Use when someone asks which licence to use, wants to change or split a project's licence, is about to publish something (npm, PyPI, app store, browser store, hosted service), or asks whether their current licensing is right.
---

# Choose a licence

Work in four phases, in order: **audit, ask, recommend, apply**. Never change a
file before the owner approves the recommendation.

This gives general information about open-source licensing, not legal advice.
Say so once, in the recommendation, not on every message. If money, an employer
or a client is involved, say a lawyer should review it.

## Phase 1: Audit

Read the repository before asking anything. Every fact you can find yourself is
a question you don't have to ask. Report what you found as one short table
before the first question.

Find:

1. **Current licensing.** `LICENSE*`, `COPYING*`, `NOTICE`, `REUSE.toml`,
   `LICENSES/`, SPDX headers, the `license` field in every package manifest
   (`package.json`, `pyproject.toml`, `Cargo.toml`, `*.gemspec` and the like), and what `CONTRIBUTING.md` says contributors agree to (CLA, DCO, or
   nothing). Note disagreements between them.
2. **Parts that ship separately.** Each thing that reaches someone on its own:
   a published package, a hosted web app or API, a mobile or desktop app, a
   browser extension, a CLI binary, a container image, a worker or function,
   docs or a dataset. Find them from manifests, workspace config, build and
   publish scripts, CI workflows, and store-listing files. For each, note how
   it ships (registry, app store, browser store, hosting, download) and who
   receives it.
3. **Third-party material inside the repo or its builds.** Vendored code,
   generated files built from outside data, fonts, icons, models, datasets,
   copied snippets with their own headers. Each brings its own licence and
   possibly attribution duties. Check what bundlers inline into shipped
   artifacts, not just what is committed.
4. **Dependency licences.** List direct runtime dependencies whose licence is
   copyleft (GPL, AGPL, LGPL, MPL, EPL) or unusual (no licence, custom,
   non-commercial). These constrain what the project itself may be.
   Permissive dependencies only need their notices kept.
5. **Who holds the copyright.** `git shortlog -sne` over the full history (fetch
   more if the clone is shallow, and say if you couldn't). Note bots and AI
   co-authors separately. If almost all of it is one person, relicensing is
   easy; many outside contributors without a CLA make it hard.
6. **What is already published.** Package versions on registries, tags, GitHub
   Releases, store versions. Anything released under a licence stays available
   under it; say this before the owner plans around taking it back.
7. **Brand assets.** The project name, logos, icons, store artwork. These
   usually need a trademark note, not a code licence.
8. **Non-code content.** Docs, research, translations, data files, interface
   copy. Software licences fit these badly.

## Phase 2: Ask

Ask only what the audit left open. Use the AskUserQuestion tool when it is
available: at most four questions per call, two to four options each, the
recommended option first and labelled "(Recommended)", and a description on
every option saying what choosing it means in practice. Without it, ask in
plain text, numbered.

Ask the most consequential questions first; later answers often make other
questions moot.

Before asking, explain any term the owner may not know (copyleft, SPDX, DCO,
CLA, REUSE) in a sentence. If they ask what something means, answer plainly
before continuing.

The question bank is below. Skip any question the audit already answered, and
adapt wording to what you found ("Your npm package..." rather than "Any
packages...").

### Goals (always ask, per part when parts differ)

- What should others be able to do with this part?
  - Use it anywhere, including in closed products (permissive)
  - Use it anywhere, but share changes to *these files* (weak copyleft)
  - Use it, but anything built on it must be open under the same terms
    (strong copyleft)
  - Read it and contribute, but not use it commercially or compete with it
    (source-available; not open source)
- Do you want one licence for everything, or different licences for parts
  with different audiences? Offer the split when the audit found parts with
  different consumers, for example a library others embed and an app you host.

### Network use (ask when a part runs as a hosted service)

- If someone runs a modified copy as a public service, should they have to
  publish their changes? Yes means AGPL; plain GPL does not require it.

### Money and control (ask when there is any commercial intent)

- Do you plan to sell it, offer a paid hosted version, or sell exceptions to
  the licence (dual licensing)? Dual licensing needs a CLA from contributors.
- Are you trying to stop a cloud provider or competitor from hosting it?
  Strong copyleft (AGPL) keeps it open; source-available licences (BUSL, FSL,
  PolyForm) forbid it but are not open source and some communities will not
  contribute.

### Distribution channels (ask only those the audit found)

- Apple App Store or Mac App Store: GPL and AGPL are widely considered
  incompatible with Apple's terms once others hold copyright in the code.
  Prefer MPL-2.0 or permissive for anything shipped there.
- Browser extension stores, package registries: no licence restriction, but
  the shipped package must carry its licence and third-party notices.

### Ecosystem (ask when a part is a library)

- Who will embed this library? Most npm, PyPI and Cargo libraries are MIT or
  Apache-2.0; copyleft libraries see much less adoption in closed products.
- Do patents matter? Apache-2.0 includes an explicit patent grant and patent
  retaliation; MIT does not.

### Contributors (ask when outside contributions are expected)

- How should contributions be licensed?
  - DCO sign-off (`git commit -s`): contributors certify they may submit the
    code under the project licence. Light; they keep copyright.
  - CLA: contributors grant you broad rights, often including relicensing.
    Needed for dual licensing; deters some contributors.
  - Nothing: inbound equals outbound by convention. Weakest record.

### Content, brand, history

- Non-code content: CC BY 4.0 (reuse with credit), CC BY-SA 4.0 (and
  derivatives stay open), or CC0 (no conditions). Or the same licence as the
  code.
- Brand: should the name and logo be reserved, so forks must rebrand?
- Copyright holder: which name, or which legal entity, goes on the copyright
  line? Ask whether any of the code was written for an employer or client,
  since they may own it.
- Earlier releases: confirm the owner understands they keep their old licence.

## Phase 3: Recommend

Present one table, one row per part:

| Part | Licence (SPDX id) | Why | Constraints it creates |
| --- | --- | --- | --- |

Then, briefly:

- **Compatibility check.** Confirm every part can legally contain what it
  bundles, and every dependency's licence allows the chosen one. Use
  `references/licenses.md` for the common pairs. Flag any conflict as a
  blocker, not a footnote.
- **What changes for others.** Who gains or loses rights compared with today.
- **What stays the same.** Earlier releases keep their licence.
- **The not-legal-advice line.**

Ask for approval. Adjust and re-present if the owner changes anything.

## Phase 4: Apply (only after approval)

Follow `references/implementation.md`. In short: full licence texts in
`LICENSES/`, a `REUSE.toml` map, SPDX headers on source files, matching
manifest `license` fields, a `NOTICE` with third-party credits, licence files
shipped inside each built artifact, README and CONTRIBUTING sections, a
trademark note if wanted, and a check in CI. Verify with `reuse lint` and the
project's own tests before committing.
