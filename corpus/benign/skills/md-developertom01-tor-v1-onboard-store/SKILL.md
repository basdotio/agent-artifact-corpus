---
name: onboard_store
description: Scaffold a new store in the multi-tenant e-commerce monorepo — creates app directory, store config, theme, landing page, Terraform infra, seed data, and CI integration. Use when adding a new hair business store.
---

# Onboard New Store

You are onboarding a new store into the tor monorepo — a multi-tenant e-commerce platform for hair businesses in Ghana. Your job is to scaffold the entire app directory, config files, Terraform infra, seed data, and CI integration so the store is ready to provision and deploy.

## Conversation Loop: Gather Before You Build

**DO NOT write a single file until you have every required field confirmed by the user.**

You must run a conversation loop with the user to collect all required information. The loop works like this:

1. **Check what's known.** Parse `$ARGUMENTS` and anything the user said in the initial message. Mark each required field as provided or missing.
2. **Ask for what's missing.** Group related missing fields into 2-3 questions max per turn — don't ask for everything in one wall of text, and don't ask one field at a time. Be conversational.
3. **Validate what you got.** After the user responds, check:
   - Is the slug lowercase with no spaces or special chars?
   - Does the domain look like a real domain (has a TLD)?
   - Are the color hex values valid? If the user gave a single primary color, generate the 50-900 scale and show it for confirmation.
   - Are there at least 2 product categories?
   - Do phone/email look real (not placeholder)?
4. **If anything is still missing or unclear, ask again.** Don't proceed. Don't fill in gaps yourself.
5. **Once you have everything, present a full summary** of all values and ask: "Does this all look correct? I'll start building once you confirm."
6. **Only after explicit confirmation ("yes", "looks good", "go ahead", etc.) do you move to Phase 2.**

If at any point the user says something vague like "just pick something" for a required field, push back: "I need this from you since it'll be customer-facing / used in production. What should it be?"

### Required fields (block until ALL are provided)

| Field | Why it matters |
|-------|---------------|
| **Store slug** | Used as `store_id` in the database, directory name, Doppler project name, Terraform resource names. Must be lowercase, no spaces, no special chars. Example: `hairfordays` |
| **Display name** | Shown in the UI, emails, metadata. Example: `Hair For Days` |
| **Domain** | Production domain. Must be a real domain the owner has purchased. Example: `hairfordays.com` |
| **Brief store description** | What the store sells, its vibe, target audience. Used to generate landing page copy, SEO metadata, and seed products. Example: "Premium braiding hair and crochet extensions for natural hair lovers in Ghana" |
| **Brand color palette** | Full 50-900 scale of hex values. Ask the user for their primary brand color and help them generate the scale if needed, but confirm the final values. The palette defines the entire look of the store. |
| **Contact phone** | Shown on site. Must be a real phone number. |
| **Contact email** | Shown on site. Must be a real email address. |
| **Contact location** | City/country shown on site. |
| **Product categories** | What the store sells (e.g., Wigs, Extensions, Accessories). Need name, slug, description, emoji for each. |
| **Admin email** | The email address for the first admin user account. |

### Optional fields (use defaults if not provided, but mention the defaults)

| Field | Default if not provided |
|-------|------------------------|
| Gold accent colors | `{ 400: '#d4a843', 500: '#c4982f', 600: '#a67c2e' }` (shared gold) |
| Hero gradient | Auto-generate from brand-900 → brand-700 → brand-500 |
| Currency | GHS (Ghana Cedis) |
| Region | `eu-west-2` (Supabase region) |
| Logo & favicon | Optional — see branding section below |

### Branding: logo and favicon

After collecting the required fields, ask the user about branding assets:

> "Do you have a logo and favicon for this store? If yes, place them in the repo and give me the paths. If you'd like to skip branding for now, just say so and we'll leave it out."

**If the user provides paths:**
1. Validate each path exists before proceeding.
2. If a path doesn't exist, tell the user exactly what's missing and ask them to fix it before continuing.
3. Once validated, process using local tools:

**Remove background** (`pip3 install rembg onnxruntime` if needed):
```python
from rembg import remove
from PIL import Image
import io
with open('{logo_path}', 'rb') as f:
    result = remove(f.read())
img = Image.open(io.BytesIO(result)).convert('RGBA')
img = img.crop(img.getbbox())
img.save('/tmp/{slug}_logo_nobg.png')
```

**Vectorize** (`brew install potrace librsvg` if needed):
```bash
python3 -c "
from PIL import Image
import numpy as np
img = Image.open('/tmp/{slug}_logo_nobg.png').convert('RGBA')
img = img.resize((img.width*3, img.height*3), Image.LANCZOS)
alpha = np.array(img)[:,:,3]
gray = Image.fromarray(np.array(img.convert('L')))
white_bg = Image.new('L', gray.size, 255)
white_bg.paste(gray, mask=Image.fromarray(alpha))
white_bg.save('/tmp/{slug}_trace.bmp')
"
potrace /tmp/{slug}_trace.bmp -s -o /tmp/{slug}_logo.svg --blacklevel 0.6 --alphamax 1.0 --opttolerance 0.2
```
Colorize SVG to match brand colors, save to `apps/{slug}/public/logo.svg`.

**Generate favicons** from the SVG:
```bash
rsvg-convert -w 180 -h 180 apps/{slug}/public/logo.svg -o /tmp/{slug}-180.png
rsvg-convert -w 48 -h 48   apps/{slug}/public/logo.svg -o /tmp/{slug}-48.png
rsvg-convert -w 32 -h 32   apps/{slug}/public/logo.svg -o /tmp/{slug}-32.png
rsvg-convert -w 16 -h 16   apps/{slug}/public/logo.svg -o /tmp/{slug}-16.png
```
Assemble `favicon.ico` (16/32/48px) + `icon.png` (32px) + `apple-touch-icon.png` (180px) into `apps/{slug}/src/app/` using Python Pillow's ICO assembler (see `edit_store` skill for the exact code). Set `logo: '/logo.svg'` in `store.config.ts`.

**If the user skips:** omit `logo` from `store.config.ts` entirely. Do not add a placeholder.

### Example conversation flow

```
Agent: "Let's set up your new store! I need a few things first.
        What's the store slug (lowercase, e.g. hairfordays), display name, and domain?"
User:  "curlqueen, Curl Queen GH, curlqueengh.com"
Agent: "Got it. What does Curl Queen GH sell? Give me a quick description
        and list the product categories (e.g., Wigs, Extensions, Accessories)."
User:  "natural hair products and curl-defining tools. Categories: Curl Creams, Styling Tools, Accessories"
Agent: "Nice. What's the brand color? Give me a hex code for the primary color
        and I'll generate the full 50-900 palette for you to review."
User:  "#7c3aed"
Agent: "Here's the palette I generated from #7c3aed:
        50: #f5f3ff, 100: #ede9fe, ..., 900: #4c1d95
        Does this look right?"
User:  "yes"
Agent: "Last bits — contact info (phone, email, location) and the admin email?"
User:  "+233 20 123 4567, hello@curlqueengh.com, Accra Ghana, admin@curlqueengh.com"
Agent: "Here's the full summary:
        - Slug: curlqueen
        - Display name: Curl Queen GH
        - Domain: curlqueengh.com
        - Description: natural hair products and curl-defining tools
        - Brand primary: #7c3aed (palette confirmed above)
        - Categories: Curl Creams, Styling Tools, Accessories
        - Contact: +233 20 123 4567 / hello@curlqueengh.com / Accra, Ghana
        - Admin: admin@curlqueengh.com
        - Gold accents: default (shared)
        Does this all look correct? I'll start building once you confirm."
User:  "yes go ahead"
Agent: [NOW begins Phase 2]
```

## What You CAN Be Creative With

### Landing page (`src/app/page.tsx`)

This is where you shine. Based on the store's name, categories, and description, craft a **compelling, conversion-focused landing page** that feels premium, modern, and aspirational.

Think like a creative director. The landing page is the store's first impression. It should make visitors want to buy.

**Every store's landing page must feel different.** Do NOT copy the layout or structure from existing stores. Each store has its own personality, and the page should reflect that.

#### Required visual quality bar

Every landing page MUST have:

- **Real background images from Unsplash** — not placeholder colors. Find, download, and upload them to Supabase Storage before writing any component code. See the image workflow below.
- **Parallax scrolling** on the hero and at least one other section — use framer-motion `useScroll` + `useTransform` in a `'use client'` component
- **Brand color overlay** on all background images — `bg-brand-900/75` (or similar opacity) so the store's color always reads through
- **Gradient vignettes** to blend image edges into sections — `bg-gradient-to-t from-brand-900 via-transparent to-transparent` etc.
- **`gold-text` class for gradient text** — NEVER use `bg-clip-text text-transparent gold-gradient` on a `block` element (it renders as a solid gold rectangle). Use the `.gold-text` CSS class defined in `globals.css` instead.
- **Staggered entrance animations** on all sections using `Animate` from `@tor/ui/Animate` or framer-motion `whileInView` with staggered delays
- **`backdrop-blur-sm`** on cards that sit over background images — gives a frosted glass feel
- **Rotating/crossfading images** in the hero if multiple images are available (auto-rotate every 5s with 1s CSS transition)

#### Image workflow — do this BEFORE writing components

Spawn **6 `find-upload-image` agents in a single message in parallel** — 3 images × 2 envs (local + dev). Each agent finds, downloads, validates, and uploads one image to one environment.

| Agent | description | filename | storage_path | env |
|-------|-------------|----------|-------------|-----|
| 1 | "{store vibe} image 1" | `{slug}-hero-1.jpg` | `assets/{slug}-hero-1.jpg` | `local` |
| 2 | "{store vibe} image 2" | `{slug}-hero-2.jpg` | `assets/{slug}-hero-2.jpg` | `local` |
| 3 | "{store vibe} image 3" | `{slug}-hero-3.jpg` | `assets/{slug}-hero-3.jpg` | `local` |
| 4 | "{store vibe} image 1" | `{slug}-hero-1.jpg` | `assets/{slug}-hero-1.jpg` | `dev` |
| 5 | "{store vibe} image 2" | `{slug}-hero-2.jpg` | `assets/{slug}-hero-2.jpg` | `dev` |
| 6 | "{store vibe} image 3" | `{slug}-hero-3.jpg` | `assets/{slug}-hero-3.jpg` | `dev` |

Wait for all 6 to return. Each agent returns a `storage_path` — collect all 3 confirmed paths before proceeding. If any agent failed to find or upload, retry with a refined description before moving on.

Once confirmed, **reference images via env var** in components — NEVER commit images to the repo or put them in `public/`:
```ts
const STORAGE = `${process.env.NEXT_PUBLIC_SUPABASE_URL}/storage/v1/object/public/products`
const images = [`${STORAGE}/assets/{slug}-hero-1.jpg`, ...]
```

Use `next/image` with `fill` + `object-cover` for background images — never `<img>` tags.

Do NOT skip this step and use Pinterest/Unsplash URLs directly in components — images must live in Supabase Storage.

**Uploading to Supabase Storage** — always use `doppler run` to inject credentials, never pull secrets locally:

```bash
# Write a reusable upload script at /tmp/upload-{slug}.js, then:
doppler run --project {slug} --config dev  -- node /tmp/upload-{slug}.js
doppler run --project {slug} --config prod -- node /tmp/upload-{slug}.js
```

The script reads `NEXT_PUBLIC_SUPABASE_URL` and `SUPABASE_SECRET_KEY` from env, creates the `products` bucket if needed (`POST /storage/v1/bucket`), then uploads each image with `x-upsert: true`.

#### Store-specific Navbar and Footer

Every store gets its own `Navbar.tsx` and `Footer.tsx` in `apps/{slug}/src/app/_components/`. These are NOT shared — they reflect each store's brand identity.

- **`layout.tsx` must import from local `_components/`**, not `@tor/ui`:
  ```tsx
  import Navbar from '@/app/_components/Navbar'
  import Footer from '@/app/_components/Footer'
  ```
- Base the implementation on `apps/aseesthreads/src/app/_components/Navbar.tsx` and `Footer.tsx` — adapt colors, logo sizing, and structure to the new store's brand.
- Nav background should complement the hero — dark stores get `bg-brand-900`, light stores get `bg-white/95`.
- All text/icon colors must use `brand-*` and `gold-*` tokens, never hardcoded hex.
- The shared `packages/ui/Navbar.tsx` and `packages/ui/Footer.tsx` are the fallback for stores not yet customized — never modify them for store-specific styling.

#### Section architecture

Split the page into a server component (`page.tsx`) that fetches data, and `'use client'` components in `src/app/_components/` for animated sections. Rules:

- **Only make a component `'use client'`** if it genuinely needs `useScroll`, `useTransform`, or `useState` (e.g. image carousel, parallax hero). Otherwise use the server-renderable `Animate` wrapper from `@tor/ui/Animate`.
- **Hero** — always `'use client'` (needs `useScroll` for parallax + `useState` for image rotation)
- **CTA section** — `'use client'` if it has parallax scale effect
- **All other sections** (Categories, Values, Testimonials, Featured Products) — server components using `Animate`

#### Design variation guidelines

Vary these per store — never repeat the same layout:

- **Hero layout**: Full-height editorial stacked type, split with imagery, centered minimal, asymmetric floating elements
- **Section order**: Mix it up — not every store needs Hero → Categories → Products → Values → Testimonials → CTA
- **Visual rhythm**: Alternate dark (`bg-brand-900`) and light (`bg-white`, `bg-brand-50`) sections. Use image-backed sections for at least 3 of them.
- **Typography**: Luxury = large type + generous whitespace. Playful = tighter, more energetic
- **CTA style**: Gold gradient buttons, outlined, underlined text links, icon-led
- **Section headers**: Gold line + uppercase tracking, centered with subtitles, left-aligned large type — vary per store
- **Icons**: Use store-appropriate `lucide-react` icons. Never default to Truck/Shield/Star. `Crown`, `Gem`, `Heart`, `Zap`, `Sparkles`, `Flame`, `Award`, `Feather` are all available

#### Design constraints (non-negotiable)

- All colors must use theme tokens: `brand-50` through `brand-900`, `gold-400/500/600`. NEVER use literal color names (`text-pink-600`, `text-teal-500`) or hardcoded hex in JSX.
- Use `.hero-gradient`, `.gold-gradient`, `.glass-card` CSS classes for branded backgrounds
- Use `.gold-text` for gradient text — NOT `bg-clip-text text-transparent gold-gradient` on block elements
- Icons from `lucide-react` only
- `page.tsx` must be a server component. Featured products fetched via `getProducts()`.
- **Always include a Featured Products section** — use the `ProductCard` grid
- `FeaturedProductsSection` props must use `ProductWithMedia[]` from `@tor/lib/types` — not a loose `{ id: string; [key: string]: unknown }[]` interface (causes TypeScript errors that hang the dev compiler)
- Include JSON-LD structured data at the bottom of `page.tsx`

### Layout metadata (`src/app/layout.tsx`)

Generate compelling SEO metadata (title, description, keywords, OpenGraph, Twitter cards) based on the store's name, products, and location. Think about what someone in Ghana would search for.

### Seed products (`supabase/seeds/{slug}.json`)

Create a per-store JSON seed file at `supabase/seeds/{slug}.json`. CI runs `node scripts/seed-store.mjs {slug}` which reads this file and inserts via the Supabase REST API — no hardcoded UUIDs, fully idempotent (skips existing slugs).

The JSON file should contain:
- `display_name` and `domain` for the store row
- `products` array with 8-14 realistic products, each having: `name`, `slug`, `description`, `price`, `compare_at_price` (optional), `category`, `in_stock`, `stock_quantity`, `featured`, `image_url`

For `image_url`: use Unsplash URLs for seed data (these are product images, not hero images — they live in the DB not storage). Use the format `https://images.unsplash.com/photo-{id}?w=800&q=80`. Find real, relevant photo IDs.

Mark 4-5 products as `featured: true`.

Also add the store row to `supabase/seed.sql` so local `db:reset` includes it.

Reference `supabase/seeds/hairlukgud.json` or `supabase/seeds/hairfordays.json` for the exact format.

## Code Rules (enforce in all generated code)

- **Avoid `useEffect` for event-driven logic.** Handle mouse events, clicks, keyboard, focus/blur directly in event handler props. `useEffect` is only for true side-effects: data fetching on mount, syncing with an external system, or cleanup.
- **Never use native `<select>`.** Always use the custom `Select` component from `@tor/ui`. If the component lacks a needed feature, extend the shared component.
- **`FeaturedProductsSection` must use `ProductWithMedia[]`** from `@tor/lib/types` — not a generic interface. Loose types cause TypeScript errors that make the dev server hang on every recompile.
- **Gold gradient text must use `.gold-text` CSS class** — not `bg-clip-text text-transparent gold-gradient` on `block` elements. That renders as a solid gold rectangle in the browser.
- **Images go in Supabase Storage, not `public/`** — reference via `NEXT_PUBLIC_SUPABASE_URL` env var so they work locally and in production without code changes.

## What You MUST NOT Change

These are shared across all stores. Do not modify them:

- `packages/lib/*` — Server actions, Supabase clients, utilities
- `packages/ui/*` — Shared UI components
- `packages/pages/*` — Shared page templates (injected into all apps)
- `packages/store/index.ts` — StoreConfig type definitions
- `packages/store/context.tsx` — StoreProvider context
- `supabase/migrations/*` — Database schema (shared by all stores)
- `scripts/*` — Build and injection scripts
- `terraform/modules/*` — Shared Terraform modules
- `terraform/shared/*` — Shared Supabase infra
- `.github/workflows/*` — CI workflows (except adding the store to input options)
- Any files in other stores' `apps/` directories

## Execution Plan

Follow this order. Use the todo list to track progress.

### Phase 1: Gather Information

Follow the **Conversation Loop** described above. Do not proceed to Phase 2 until the user has confirmed the full summary.

### Phase 2: Find and upload hero images FIRST

Before spawning build agents, spawn **6 `find-upload-image` agents in a single message in parallel** (3 images × local + dev). Craft 3 distinct visual descriptions based on the store's products and vibe — e.g. "Black woman wearing a lace-front wig, editorial fashion, warm studio lighting, Ghana".

Wait for all 6 to return. Collect the 3 confirmed `storage_path` values. If any failed, retry with a refined description. Do NOT proceed to Phase 2.5 until all 3 images are confirmed uploaded to at least `local`.

**Do NOT delete the `/tmp/{slug}-hero-{n}.jpg` files** — they are reused in Phase 5 for the prod upload.

### Phase 2.5: UI Planning

Spawn a single **`ui_ux_agent`** with the full store config and confirmed image storage paths:

```
slug={slug}
display_name={display_name}
description={description}
brand_colors={50-900 scale}
gold_colors={400/500/600}
categories={list}
tagline={tagline}
contact_location={city, country}
hero_images={storage paths of the 3 confirmed images}
```

Wait for it to return before proceeding. It will create `agent_work/{slug}.ui_plan.md`.

The plan is the design authority for all UI work that follows. Do not proceed to Phase 3 if the agent failed to produce the plan.

### Phase 3: Build in parallel

**Spawn all 4 agents in a single message simultaneously.** Pass the full confirmed store config AND the confirmed Supabase Storage image paths to each agent.

| Agent | File | Covers |
|-------|------|--------|
| **Agent A** | `onboard_store-app` | App directory, store.config.ts, globals.css, layout.tsx, page.tsx, supabase config, symlinks, env, branding assets |
| **Agent B** | `onboard_store-terraform` | terraform/stores/{slug}/ — doppler, dev, prod, **vercel, resend** terragrunt.hcl |
| **Agent C** | `onboard_store-seed` | supabase/seeds/{slug}.json, init/{slug}.yaml, supabase/seed.sql |
| **Agent D** | `onboard_store-ci` | CI workflow update, apps/{slug}/CLAUDE.md, apps/{slug}/AGENTS.md |

Wait for all 4 to return before proceeding.

### Phase 3.5: UI Build + QA loop

Run `ui_builder` then `ui_qa` in a fix-and-retry loop, capped at **10 iterations**.

**Iteration 1:**
1. Spawn `ui_builder`: `slug={slug} plan=agent_work/{slug}.ui_plan.md`
2. Wait for it to return.
3. Spawn `ui_qa`: `slug={slug} plan=agent_work/{slug}.ui_plan.md`
4. Wait for it to return.

**Loop (iterations 2–10):**
1. If `ui_qa` returns `Status: PASS` → done. Report:
   ```
   ✅ UI QA passed ({slug}) — all sections match the plan.
   ```
2. If `ui_qa` returns `Status: ISSUES FOUND`:
   - Capture the full QA report text.
   - Spawn `ui_builder` again, passing the report as feedback:
     `slug={slug} plan=agent_work/{slug}.ui_plan.md qa_report={full report text}`
   - The builder reads the report and fixes only the flagged issues — it does not rebuild from scratch.
   - Wait for it to return, then spawn `ui_qa` again.
   - Repeat.
3. If still failing after 10 total iterations → stop, report all remaining issues to the user, and proceed anyway (do not block the rest of the pipeline on cosmetic issues).

### Phase 3.6: Visual QA (requires live dev server)

Once `ui_qa` passes (or after iteration cap), run visual verification with `ux_verify_qa`.

**Start the dev server in the background:**
```bash
cd apps/{slug} && npm run dev &
# Wait ~15s for Next.js to compile, then proceed
```

**Spawn `ux_verify_qa`:**
```
slug={slug}
url=http://localhost:3000
plan=agent_work/{slug}.ui_plan.md
```

Wait for it to return.

**If `Status: PASS`** → report:
```
✅ Visual QA passed ({slug}) — rendered output matches the plan.
```

**If `Status: ISSUES FOUND`**:
- For each visual issue, check if it's caused by a code problem (wrong class, missing token, broken import) or a data/env problem (missing image in storage, missing env var).
- Code problems: spawn `ui_builder` with the visual QA report as feedback, then re-run `ux_verify_qa`. Cap at **3 iterations** — visual issues are often env-dependent.
- Data/env problems: note them for the user and proceed (do not block the pipeline).

**If the dev server fails to start** (port conflict, build error): skip this phase, note it to the user, and proceed to Phase 4. Visual QA can be re-run manually later.

### Phase 4: Infra QA — plan, fix, repeat

Run Terraform plans against all infra targets to catch config errors before CI. Use a fix-and-retry loop capped at **10 iterations per wave**.

#### Wave 1 — vercel, resend, doppler (parallel, no prerequisites)

Spawn **3 `infra_qa` agents in a single message in parallel**:

| Agent | arguments |
|-------|-----------|
| QA-vercel | `store={slug} target=vercel env=dev` |
| QA-resend | `store={slug} target=resend env=dev` |
| QA-doppler | `store={slug} target=doppler env=dev` |

Wait for all 3. Then loop (max 10 iterations):

1. Collect all `FAIL` reports (ignore `PASS` and `BLOCKED`).
2. If no `FAIL` results → Wave 1 passes. Proceed to Wave 2.
3. For each `FAIL`, read the file identified in the report and apply the fix described.
4. Re-spawn only the `infra_qa` agents that previously failed (in parallel if multiple).
5. Repeat from step 1.
6. If still failing after 10 iterations → stop, report all remaining failures to the user, and do not proceed to Wave 2.

#### Wave 2 — dev and prod (parallel, requires vercel project to be applied)

**Before spawning Wave 2 agents**: run `task tg:vercel APP={slug} ENV=dev` to ensure the Vercel project exists, so the `data.vercel_project` lookup in the plan succeeds.

Spawn **2 `infra_qa` agents in a single message in parallel**:

| Agent | arguments |
|-------|-----------|
| QA-dev | `store={slug} target=dev env=dev` |
| QA-prod | `store={slug} target=prod env=prod` |

Wait for both. Then loop (max 10 iterations) using the same fix-and-retry logic as Wave 1:

1. Collect `FAIL` reports. `BLOCKED` results mean a prerequisite apply hasn't run — note them but don't treat as fixable code errors.
2. If no `FAIL` → Wave 2 passes. Proceed to Phase 5.
3. Fix the file(s) identified in each `FAIL` report.
4. Re-spawn failed agents in parallel.
5. Repeat. Stop at 10 iterations and report any remaining failures.

#### After both waves pass

Report a summary to the user:
```
✅ Infra QA passed ({slug})
  vercel  → PASS (N to add)
  resend  → PASS (N to add)
  doppler → PASS (N to add)
  dev     → PASS (N to add)
  prod    → PASS (N to add)
```

### Phase 5: Verify + upload prod images

Once all agents complete:
- Run `task inject` — copies proxy.ts and all shared pages into the app
- Run a build (`npx next build` inside the app dir) to catch TypeScript errors before the user tries to dev
- Confirm the supabase/migrations symlink is correct
- **Upload hero images to prod**: spawn **3 `find-upload-image` agents in a single message in parallel**, one per image, each with `env: "prod"`. The `/tmp/{slug}-hero-{n}.jpg` files from Phase 2 are still on disk — pass the same `filename` and `storage_path` as before. The agents will skip the find/download step since the file already exists and go straight to upload.
  - If any agent reports prod credentials missing or upload failed, note it for the user: "⚠️ Prod hero images not uploaded — run `task tg:all APP={slug} ENV=prod` to provision, then re-run the upload agents."
  - If all 3 return success, confirm.
- List all created files for the user to review

## Reference Files

When you need to understand the exact format or structure, read these files:

- **StoreConfig type**: `packages/store/index.ts`
- **Example store config**: `apps/hairlukgud/src/store.config.ts` or `apps/hairfordays/src/store.config.ts`
- **Example globals.css**: `apps/hairlukgud/src/app/globals.css`
- **Example layout.tsx**: `apps/hairlukgud/src/app/layout.tsx`
- **Example page.tsx**: `apps/aseesthreads/src/app/page.tsx` (best reference — server component composing client sections)
- **Example hero component**: `apps/aseesthreads/src/app/_components/HeroSection.tsx` (parallax + image carousel)
- **Example values component**: `apps/aseesthreads/src/app/_components/ValuesSection.tsx` (image background + overlay)
- **Example CTA component**: `apps/aseesthreads/src/app/_components/CtaSection.tsx` (parallax scale + image)
- **Example config.toml**: `apps/hairlukgud/supabase/config.toml` and `apps/hairfordays/supabase/config.toml`
- **Example terragrunt**: `terraform/stores/hairfordays/prod/terragrunt.hcl`
- **Example init yaml**: `init/hairlukgud.yaml`
- **Seed data**: `supabase/seeds/hairlukgud.json` or `supabase/seeds/aseesthreads.json`
- **Seed script**: `scripts/seed-store.mjs`
- **Provisioning workflow**: `.github/workflows/provision-store-init.yml`
- **Full onboarding guide**: `docs/onboard-new-store.md`

## Important Patterns

- **Colors are NEVER hardcoded** in shared code or JSX. Always use `brand-*` and `gold-*` Tailwind tokens. The only place hex values appear is in `store.config.ts`, `globals.css` `@theme inline`, and the CSS utility classes (`.hero-gradient`, `.gold-gradient`).
- **Page injection**: Shared pages from `packages/pages/` are copied into `src/app/` at dev/build time. The `.injected` manifest and `.gitignore` are auto-generated. Don't manually create files that would conflict with injected paths.
- **Supabase migrations are shared**: All stores use the same schema via symlinked `migrations/` dir. Never create store-specific migrations.
- **Store isolation is via `store_id`**: Every table query filters by `store_id`. The value comes from `NEXT_PUBLIC_STORE_ID` env var at runtime via `getStoreId()` from `@tor/lib/store-id`.
- **Next.js 16**: This is NOT standard Next.js. Check `node_modules/next/dist/docs/` before using any API you're unsure about.
- **`NEXT_PUBLIC_*` env vars are inlined at build time** by Next.js — changing them requires a redeploy.
- **Gold colors are shared** across all stores (same warm gold accent). Only brand colors differ.
- **`proxy.ts` not `middleware.ts`**: Next.js 16 renamed middleware to proxy. Each app has `src/proxy.ts` that re-exports the function from `@tor/lib/proxy` with a static `config` matcher.
