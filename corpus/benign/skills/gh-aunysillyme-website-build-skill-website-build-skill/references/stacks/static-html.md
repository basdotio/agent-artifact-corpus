# Static HTML recipe

Date rule: [ASK DATE and source evidence](../../playbooks/research-and-memory.md#ask-date-rule).
Use this recipe only after accepted research and a named visual mockup selection.
Example commands and host/runtime support are UNVERIFIED until executed or sourced
for the chosen project. Save actual results; never claim this recipe was deployed.

Use for a small information site without repeated publishing or application state.

## File responsibilities

```text
site/
  index.html              Main audience/action page.
  visit/index.html        Deliberate second route when the brief needs it.
  assets/styles.css       Approved tokens, layout, states, responsive rules.
  assets/site.js          Optional interaction only.
  assets/images/          Approved measured exports with required notices.
  assets/fonts/           Licensed woff2 and license notices if used.
  robots.txt              Owner-approved crawl policy.
  sitemap.xml             Intended canonical public routes.
  llms.txt                Truthful navigation map.
  404.html                Useful error and recovery page.
  SITE_OPERATIONS.md      Complete operational handoff, excluded from upload if private.
```

Choose the selected host's static header configuration separately.
Keep source and output identical only while this remains a genuine no-build site.
Deployment uses an explicit file allowlist, not every file in the workspace.

## Preview and check

From the approved site directory, a local preview example is:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Open the local root and every intended route in a browser.
This preview does not prove production redirects, custom error handling, HTTPS, or headers.
Inspect those separately on the authorized host preview and final release.
There is no package installation or build command required by this recipe.
Record any added tool as a project-specific dependency with a reason.

## Verify the contract

- Build: run checklists/build.md against source and browser DOM, including missing optional IDs.
- Accessibility: complete keyboard/error journeys and computed contrast checks.
- Performance: retain the declared cold mobile series and all reports.
- Discovery: inspect initial HTML, canonicals, internal links, route map and metadata parity.
- Security: inspect actual host headers, enforced-policy behavior, and scanner evidence.
- Release: apply checklists/ship.md to the exact uploaded files and independent review.

## Add the next page

A unique second page can be authored directly with the same approved styles.
When repeated structure or metadata requires recurring copy/edit work, revisit the
scripted-static recipe before duplicating a growing set of pages.
Record how shared navigation and discovery files remain consistent in the interim.

## When to move to a bigger stack

Browser JavaScript cannot safely store server secrets or enforce private authorization.
Use a separately justified endpoint or reconsider the framework branch for server state.
Scheduled changes require a real editing/release trigger; static files do not self-update.
Move validated content into records before repetition creates divergent page state.

## Research starting points

Read the selected host's static routing/headers documentation and the current HTML standard.
Inspect a real no-build repository at an identified revision and check its license.
Use playbooks/choose-stack.md for the recorded decision and rejected alternatives.
