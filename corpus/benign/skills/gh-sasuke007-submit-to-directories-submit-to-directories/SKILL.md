---
name: submit-to-directories
description: Submit a user's software product to relevant directories in this skill's catalog. Use when asked to list a product, work through directory submissions, or verify directory backlinks. Start with the product URL, inspect the site and logo, collect the submission email, then execute and track submissions.
metadata:
  version: 1.2.0
---

# Submit to directories

Use the catalog bundled beside this file to find suitable listings, submit the user's product, and record what actually happened. All paths below are relative to this `SKILL.md`. The catalog contains historical research from a prior campaign; its statuses describe that campaign, not the current user's product.

## Intake: finish this before any submission

1. **Ask for the product URL first.** If the user already gave it, use it without asking again. Follow redirects and store the canonical URL the site actually serves, preferring HTTPS when available. Do not start account creation or fill submission forms yet.
2. **Inspect the product site.** Open the rendered homepage and relevant About, Features, Pricing, and Contact pages. Extract the product name, what it does, target users, key features, pricing model, canonical URL, and any public founder/company details. Inspect page text, metadata, structured data, and visible UI; distinguish a verified fact from an inference. Draft a tagline, short and long description, and relevant tags in the product's own terms. Never invent features, customer names, metrics, integrations, or prices.
3. **Extract the logo.** Check the visible header logo first, then `Organization.logo` structured data, `og:image`, and favicon candidates. Prefer an actual brand logo over a social preview or generic favicon. Resolve the asset URL, download an uploadable PNG to the current run's `assets/` folder, and inspect that it belongs to this product. Convert an SVG to PNG when that is the best available logo; keep the SVG too. If the site is inaccessible, the logo is ambiguous, or an image cannot be downloaded or converted, ask the user for the missing description or logo file/URL. A favicon is an acceptable fallback only when it is visibly the product's mark and has enough resolution for the target form.
4. **Then ask which email to use** for directory accounts and listing contact fields. If the user already supplied one, confirm only if its intended use is unclear. Do not ask for a password. Use only that identity or an already signed-in session for the same identity; route email verification, OTP, CAPTCHA, or account mismatch to the user.
5. **Fill only remaining gaps.** Show the concise product profile you extracted and ask targeted questions for material unknowns or uncertain claims. At minimum, have a canonical URL, product name, accurate short and long descriptions, a tagline, relevant tags, usable logo, and the chosen email. Ask for screenshots, a demo, founder identity, or pricing details only when a chosen directory requires them and they are not visible. Do not hold up directories that do not require those optional assets. Save a local `profile.json` following `references/profile.schema.json` after the required fields are known.

The intake order matters: URL → site and logo → email → remaining required facts → submissions. Continue automatically once the required information is complete; a request to run submissions authorizes ordinary free listing forms. If a previous profile is present, verify that its URL matches the current product before using it. Keep contact information in local run files, never in the shared catalog or a shareable report.

## Select a queue for this product

For a new product, start with:

```bash
python3 scripts/list_directories.py --new-product --free --exclude-access paid,dead --format table
```

The source campaign marked many CAPTCHA and login entries `blocked` or `skipped`. Review them separately for a new product, then add only genuine matches to the same ledger:

```bash
python3 scripts/list_directories.py --status blocked,skipped --free --access captcha,login --no-default-excludes --format table
```

Use `--category`, `--min-dr`, `--dofollow`, `--no-badge`, `--access`, and `--limit` as useful filters. `--new-product` reconsiders the source campaign's `live`, `submitted`, and `already-listed` entries because another product may be eligible. Its default still excludes source `blocked` and `skipped` rows, so the second pass catches potentially useful human-blocked sites. Do not treat those source statuses as a verdict on the new product. For repeat work on the same product, use its own run ledger to exclude submitted/live domains and check the live directory for an existing listing before creating another. Never use the source campaign's listing URL as this product's listing URL.

Check each candidate's current submission page, free path, category fit, and requirements before acting. Catalog DR, free, dofollow, and access labels are historical clues, not current guarantees. Prefer relevant, editorial directories with a genuine free listing. Do not force an agent into an MCP registry, a local business into an unrelated AI directory, or a product into a false category. Skip paid-only, dead, and irrelevant sites. Keep relevant CAPTCHA entries in the candidate queue for human handoff. A backlink may help discovery or authority, but do not promise a DR increase.

Create `runs/<product-slug>/ledger.csv` from `references/ledger-template.csv` and add each selected, relevant candidate as `queued` before working through forms. This is the product's source of truth; never write its results back into the shared catalog.

## Submit and track

For each eligible directory, work sequentially:

1. Check the product's ledger and search the directory for an existing listing. If it exists, record its URL and verify it instead of resubmitting.
2. Open the current submission flow in a browser. Choose the free option and the closest truthful category. Use the selected email for accounts and contact fields. Fill everything possible before a CAPTCHA, login, email confirmation, OTP, or other user-only step. Record the exact blocker and pause that entry without losing its place; continue with independent entries.
3. Adapt copy from `references/variants.md` to the directory's audience and field limits. Use only facts supported by the site or user. Do not submit duplicate long descriptions across sites. A directory URL may use `utm_source=<directory-domain>&utm_medium=directory&utm_campaign=listings` when the field accepts query parameters; otherwise use the canonical URL.
4. Upload the extracted logo and any available, relevant screenshots. If a site requires assets or facts still missing, ask only for those and defer that site.
5. Submit once, read the confirmation, and update the ledger. Use `submitted` only with a receipt or clear confirmation; use `live` when the listing is visible. Use `needs_user` for any user-only step, including confirmation after a form submission, and `retry_later` for a temporary site failure. Record the last page URL, precise reason, one action the user needs to take, and whether a form was already sent. A filled form is not a successful submission.
6. Once a listing is live, inspect its outbound link to the product. `scripts/verify_backlink.sh <listing_url> <product-domain>` can provide an initial `dofollow`/`nofollow`/`not_found` result; check in the browser if the site renders links with JavaScript or redirects. Record the observed link, not a claim from the directory.

Do not buy listings or select paid add-ons without the user's decision. Do not solve CAPTCHAs, guess OTPs, or change the user's production site to satisfy a reciprocal badge; flag those as follow-ups. Stop a run after three consecutive hard failures and report the blockers. Avoid parallel form submissions and duplicate accounts.

## Human handoff and resumption

Keep every selected directory that is not confirmed `submitted` or `live` in the ledger. Never silently drop a `needs_user` or `retry_later` entry. After the autonomous pass, show the user all `needs_user` entries in a compact table with directory, reason, exact user step, and page link. Show `retry_later` and remaining `queued` counts separately. Then ask:

> We have not finished submitting to these directories for the reasons shown above. Do you want to continue? I can open each page in a shared browser. Please complete the one step listed for that directory, then tell me when it is done; I will resume the submission and check the result.

Suggest the browser handoff that matches the **agent/client being used**, not merely the language model name:

| Agent/client | Suggested shared browser |
|---|---|
| Claude Code or Claude Cowork | [Claude in Chrome](https://support.claude.com/en/articles/12012173-get-started-with-claude-in-chrome) browser extension |
| Codex in the ChatGPT desktop app | [ChatGPT browser extension](https://learn.chatgpt.com/docs/chrome-extension); connect the user's browser in Settings → Computer Use |
| Open-source or local agent | Download [Ego Lite](https://github.com/citrolabs/ego-lite) and install/use its `ego-browser` skill |

The ChatGPT browser extension requires the desktop app; Codex CLI or IDE users should switch to a supported desktop browser session for this handoff. If the agent/client is unclear, ask which one the user is using before recommending a tool. If the suggested browser is unavailable, keep the ledger and provide the page links for manual completion.

When the user chooses to continue, open **one** blocked page in that shared browser, at the saved URL and checkpoint. Tell them the exact step to perform there (for example, complete the CAPTCHA or enter the emailed code in the page). Let the user take control of that page. Do not ask them to paste passwords or one-time codes into chat. After they say the step is done, inspect the **same browser session**, finish only the remaining form steps, and check for a receipt or live listing. Update the ledger. If it remains blocked, record the new reason and keep it on the handoff list. Repeat for the next entry. If they decline or leave, preserve the queue for the next run. On a later run, load this ledger first and resume incomplete entries without creating duplicate listings.

## Report

Summarize submitted, live, verified followed links, verified nofollow links, `needs_user`, `retry_later`, and still `queued`. Include each touched directory's status and listing URL or receipt, plus the next useful candidates. Always include the unfinished human handoff list and each exact next step, even if the user does not continue now. Keep the chosen email, phone number, passwords, and tokens out of any shareable report. Keep the profile and run files local and uncommitted.

## Scope

This skill executes submissions; broader directory strategy is outside its scope. The bundled catalog works on its own. Never overwrite its historical research with another product's outcomes. Keep `profile.json` and `runs/` local; they contain product contact and campaign data.
