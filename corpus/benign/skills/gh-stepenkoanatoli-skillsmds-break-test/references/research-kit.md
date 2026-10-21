# Research-Kit in a break test

How the kit was actually used on 2026-10-03 to close the facts the probes could not observe, with the parts that cost time written down so they cost it once. The kit's own `README.md` and the `research-first` skill it installs are the reference for anything not covered here.

## When the kit is not deployed

`doctor` looked for `~/.agents/research-kit` and found nothing: the session container had only the user's checkout. Running from the checkout for the session, without installing anything on the machine:

```sh
export RESEARCH_KIT_HOME=/path/to/Research-Kit/research-kit   # the kit folder inside the checkout
export RESEARCH_KIT_TRANSPORT=http-keyless                      # free; no key on this machine
node "$RESEARCH_KIT_HOME/bin/doctor.mjs"                        # from the repository root
```

`doctor` then warns that the commit and edit gates are not installed and that no install state is recorded. Those warnings go in the report; they do not stop a collection. Say in the report that the kit ran from a checkout.

Read the whole verdict. At MoonAliza's root, `doctor` raised one *critical* that had nothing to do with the research: `tests/fixtures/github-tls/leaf.key matches private-key-block`, a test TLS key for a loopback fake. That is a finding for the break-test report (a decision for the owner), found only because the kit was run.

## Scaffold, map, contract

```sh
P=docs/research/$(date +%F)-break-test-external-facts
node "$RESEARCH_KIT_HOME/bin/new-project.mjs" "$P" --topic "Facts the break test could not observe: ..." --kit "$RESEARCH_KIT_HOME"
cd "$P"
node "$RESEARCH_KIT_HOME/bin/decompose.mjs" --dry-run     # writes research/MAP.md; keyless, so spends nothing either way
```

The nine universal map rows are about data sources; for documentation facts most are `DISMISSED` with a reason (no auth, no quota, no cost, public pages) and a few are `COVERED` by the unknowns. Add one topic row per tool (`S-1 npm's install-script policy`, `S-2 esbuild's postinstall`, `S-3 engine-strict`).

One unknown per fact a cause or recommendation rests on, phrased so a page can close it: "When package.json has `allowScripts`, what does npm 11 do with a dependency's install script the field does not name: run, skip, or ask?" Four unknowns closed this run.

## Plan: name the owner's page, and its plain-text form

Name pages directly in `plan.json`; no search is needed for documented tools. A `prior.mjs` note of what you expect must be registered **before** the first collection or not at all; the first run forgot it, which is a loss of honesty evidence, not of facts.

Client-rendered documentation sites return a title and no body to a keyless fetch. docs.npmjs.com did: three captures of 47 to 62 characters, which `preflight` flags as `raw-thin`. The page that owns the fact is then the documentation's **source file in the tool's repository at the exact version tag**:

| Rendered page | Source that captures as text |
|---|---|
| docs.npmjs.com/cli/v11/commands/npm-install-scripts | raw.githubusercontent.com/npm/cli/v11.19.0/docs/lib/content/commands/npm-install-scripts.md |
| docs.npmjs.com/cli/v11/using-npm/config (generated) | raw.githubusercontent.com/npm/cli/v11.19.0/workspaces/config/lib/definitions/definitions.js |
| a GitHub `blob` page (403 to a plain client) | the same path on raw.githubusercontent.com |

Pin the tag to the version the project actually runs (here npm 11.19.0, the npm bundled with the pinned Node 24.21.0). The `latest` branch's changelog described npm 12 and stopped at 11.12.1; the 11.x facts were on `release/v11`.

Keep the thin captures: rewrite their `Finding` to say the page is client-rendered and not cited, and point at the source row. Deleting rows hides how the collection went.

## Review, gate, brief

- A `[quote: ...]` must occur in the capture **on one line**. A sentence that wraps across two comment lines in a source file fails `citations/quote-not-found`; quote the part that sits on one line.
- `preflight` warnings seen with a keyless collection and documentation sources: `transport-not-metered` on every row (expected without a key), `corroboration/one-voice` when an unknown's rows all come from one host (two files of the same repository are two readings of one source), `raw-thin` for the client-rendered captures. Warnings pass under the `pluralist` policy; say in the report that the corpus is keyless.
- `brief.mjs` drafts the handoff; its *Contradictions* and *Decision* sections are yours. The one contradiction this run: documentation at the 11.19.0 tag says scripts are "blocked by default" while the changelogs call the 11.x policy "opt-in" and date default-deny to 12.0.0. Resolved by reading both as: in 11.x the field's presence switches the policy on. Write what was **not** observed too (an npm 11 install without the field).

## Commit

The ledger is a dotfile and must travel with the corpus:

```sh
git add docs/research/<project>/ && git add -f docs/research/<project>/research/raw/.fetches.jsonl
git commit -m "research: <topic>"
```

Commit the corpus before the report commit that cites its `E-nn` rows.

## Exit codes

`PASS` 0 (checked, correct), `FAIL`/`REOPEN` 1 (checked, wrong), `INCOMPLETE` 2 (could not be checked), `BLOCKED` 3 (refused to start). Read the code, not the prose; `INCOMPLETE` is not a pass.
