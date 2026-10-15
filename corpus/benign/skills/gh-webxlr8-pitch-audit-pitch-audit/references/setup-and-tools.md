# Setup and tool reference

Load this when setting up a machine or a company profile, or when you need a tool's options.

## Machine setup
`python3 scripts/doctor.py` checks everything and prints the exact install command for anything missing.
- Required: Python 3.9+ (`pip install -r requirements.txt`, about 40 MB) and Google Chrome (or Playwright's Chromium with `PITCH_BROWSER=chromium`).
- Speed tests, one of:
  - `PSI_API_KEY`: Google's free PageSpeed Insights API. Nothing to install; runs on Google's servers.
  - Node.js, for local Lighthouse (`npx lighthouse@13`). Needed for localhost/demo sites.
- Optional extras:
  - poppler: adds a third PDF engine to the viewer check.
  - macOS `swiftc`: adds the Apple PDFKit check, compiled once and then cached.
  - `UNSPLASH_ACCESS_KEY` / `PEXELS_API_KEY`: photo search.
- `Dockerfile`: everything preinstalled.

## Company setup (`/pitch-audit setup <your-company-url>`)
Run when `pitch-profile/company.yaml` is missing, or the user wants to change their company.
1. `python3 scripts/setup_profile.py <url> [--assets <brand-folder>]`. It reads the homepage plus up to 8 key pages and writes:
   - `company.yaml`: name, contact, booking link, social, accent colour, fonts, logo
   - `brand/`: the logo rendered alone; a light version is made if only a dark logo exists
   - `_sources/*.txt`: page text
   - `setup-report.md`: what was found and what is missing
   Official brand files: pass `--assets`, or copy them into `pitch-profile/brand/` and point `company.yaml` at them.
2. Draft from `_sources/`:
   - `catalog.yaml`: each real offer with id, name, type (service or product), capabilities, promise, includes and first_step. Add a price only if public, guarantees only if stated, and a logo for products.
   - `mapping.yaml`: capability → offer, `fit_rules` (industry keywords) and `guidance`.
   - `proof.yaml`: stats, client names and case studies. Each `result` stays null until the user confirms a real number.
3. Show the user a short summary. They confirm the offers, prices and proof. Never use claims they haven't confirmed.
4. `python3 scripts/profile_check.py` must exit 0.

## Tools
| Script | Use |
|---|---|
| `prepare.py <url> clients/<slug>` | **Start here.** Runs audit + prospect assets in parallel, then filmstrip, score, background. About 1 min. |
| `audit.py <url> --out clients/<slug> [--speed auto\|psi\|local\|off]` | Site audit. Mobile and desktop speed tests run in parallel. Exit 2 = unreachable or parked: confirm the URL. Flags a bad certificate on the bare domain, and checks whether AI assistants (ChatGPT search, Perplexity, Claude) may read the site, via robots.txt and firewall. |
| `score.py clients/<slug>` / `--explain` | 8-category score; findings mapped to your offers |
| `prospect_assets.py clients/<slug>` | Their logo (`client.logo`, `client.logo_on_dark`), their photos (`images/prospect-photo-N.jpg` + contact sheet), page-load filmstrip (`images/filmstrip.json` → `finding.filmstrip`) |
| `evidence.py clients/<slug> <url> --name x` | Proof screenshot, 1000×700. Modes: `--cert-warning`, `--text "..."`, `--selector`, `--clip x,y,w,h`, `--mobile`, `--stack a.png b.png`. Prints an `image` snippet; fill in its `alt`. |
| `fetch_image.py clients/<slug> <url> --name cover` / `--search "query"` | Free Unsplash/Pexels photo, only when they have no usable photos. Credits go to `images/CREDITS.md`. |
| `backgrounds.py clients/<slug>` | Generated on-brand topographic texture |
| `build.py clients/<slug> [--style style-2] [--hq]` | Lint → render → WCAG → viewer checks → the one PDF to send. Default output is 1920 px pages (about 1.5 MB); `--hq` gives 2560 px for print. |
| `batch.py leads.csv --audit` / `--rank` | Lead lists |
| `lint_deck.py`, `a11y_check.py`, `compat_check.py` | Run by `build.py`; usable alone |

## What build.py checks
- **Lint**:
  - Deck structure and the word budget per slide.
  - Every number traced to a source (audit, scores, manual facts, research or profile; mockups exempt). A traced number proves it exists, not that it is the right metric, so still check meaning.
  - Stock phrases, em dashes, Title Case headlines and a repeated headline formula.
- **WCAG 2.2 AA**: measured on the real pixels behind every text line; graphics at 3:1.
- **Viewer compatibility**:
  - Every page must be one flat image (any OS). Soft masks and transparency are what WhatsApp and Apple PDFKit mis-draw.
  - Every page is rendered in PDFKit (macOS), PDFium and poppler (if installed), and diffed against the design.

The PDF is flattened because Chrome exports CSS masks, filters and blur as soft masks and image tiles, which Apple and Android viewers drop. Never send a vector "print to PDF" export.
