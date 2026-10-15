---
name: Product lifecycle overview
description: >-
  When launching or migrating a software product end-to-end and you want the
  big-picture sequence that ties the individual skills together (naming, site,
  deploy, SEO, submission, analytics, release, growth).
---
# Product lifecycle overview

The end-to-end sequence for taking a software product from an idea to a launched, discoverable, growing product. Each stage below has its own focused skill; this is the map and the order. Do the stages roughly in sequence, but expect to loop back.

## Stages
1. **Brand naming** — pick a name that is brandable, available, and SEO-friendly (own, distinctive spelling). See the brand-naming skill.
2. **Scaffold or migrate the site** — stand up the marketing/product site from a shared template, or migrate an existing one onto it. See the scaffold-or-migrate-site skill.
3. **Domain & deploy** — wire up a (sub)domain, DNS, hosting, CI/CD, tag-based releases, and tokens. See the domain-and-deploy skill.
4. **Technical SEO** — titles, descriptions, canonical, a single H1, robots, sitemap, structured data, favicon/OG. Each site independent, no duplicate content. See the technical-seo skill.
5. **Search engine submission** — Google Search Console, Bing Webmaster, IndexNow. See the search-engine-submission skill.
6. **Web analytics** — GA4 + a session-analytics tool, unified under one property, verified live. See the web-analytics skill.
7. **Desktop app release** (if there's a desktop app) — icon, signing/notarization, releases, auto-update. See the desktop-app-release skill.
8. **Shared footer & product list** — one source of truth for cross-product links. See the shared-footer-product-list skill.
9. **Operations & growth** — ongoing engagement, account matrix, posting cadence. See the operations-growth skill.

## Principles that cut across every stage
- **Each site is independent:** its own content, titles, descriptions, and canonical URLs. Never let one site duplicate another; shared boilerplate is the enemy of indexing.
- **Brand consistency:** decide the brand/prefix rules once (e.g. a brand prefix in titles/structured-data/footer for SEO, short name in the header) and apply them the same way everywhere.
- **Reproducible releases:** production ships only on version tags, pushed to the right remote, never force-pushed.
- **No secrets in the repo or chat:** keep tokens in the host's env/secret store.
- **Verify live, not just locally:** after each deploy, check the real URL (title, H1, sitemap host, analytics firing).

## How to use
Work the relevant stage's skill for the task at hand. For a brand-new product, go top to bottom. For an existing product, jump to the stage that's missing.
