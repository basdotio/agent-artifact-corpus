# Project design contract

Read for every new product and before any redesign of an existing frontend. Record the actual decisions in the project's own approved design document; these are choices to resolve, not a universal visual theme.

## 1. Product and brand inputs

| Decision | Record | Failure to avoid |
| --- | --- | --- |
| Audience and task | Who needs to decide or act, at which step, with which hesitation | Reusing a dashboard layout on a retail checkout |
| Brand promise | Three concrete traits, three traits to avoid, tone and trust obligations | Calling everything “premium” without visible criteria |
| Product branches | Physical, digital, configurable, subscription; relevant roles | Showing shipping on a digital-only order |
| Real inputs | Product, price, stock, location, delivery, permissions, metrics and their source | Filling blank content with invented counts |
| Supported conditions | Languages, direction, currencies, theme modes, zoom, consent, region | Cropping translated text or misformatting money |
| Non-negotiable behavior | Routes and existing controls; approval boundaries | Redesigning an action into a different transaction |

## 2. Shared system; one theme source

For a new product, define **one global CSS theme file** that owns all theme-dependent semantic tokens (start from `assets/templates/theme-tokens.css`; in a framework project put the roles where the framework reads its theme, see [framework-mapping.md](framework-mapping.md)). All page styles and components read those tokens. CSS modules or local styles may handle arrangement, but must not hide a second palette or duplicate a theme's colors, shadows, radii, or motion timings. An existing product receives a route-and-style audit and owner approval before theme restructuring.

Keep a concise, versioned project design contract (`assets/templates/design-contract.md`) in the frontend repository so future AI coding sessions share the same approved brand decisions. Include token roles, spacing/type scale, icon/media IDs, component variants, content tone, supported themes/locales, page exceptions, and the owner-approved change scope. Read it before generating a new page; update it only for a genuinely approved change. It is a project file, not a change to any assistant's global instructions or memory, and not model training. Preparing a separate training dataset or training a model is a later, distinct project requiring explicit data, rights, and scope decisions.

Maintain token roles for: canvas/surface/elevated surface; foreground/subtle text/inverted text; brand/accent/on-brand; border/divider; link/focus; success/warning/danger/info with appropriate foreground; overlay; illustration tints; chart series with redundant pattern or marker; spacing steps; container/reading widths; font family/size/line height/weight; radius; elevation; **layers** (one ordered z-index scale: base < raised < sticky < dropdown < drawer < modal < toast < tooltip, so overlapping elements never fight and nobody invents 9999); motion duration/easing. Use role names rather than hue names in components. Theme changes update the whole site, including footer, overlays, toasts, charts, product states, and admin screens. Check contrast in each supported theme and when a photograph sits behind text.

**Dark theme:** raise surfaces by making them lighter (canvas < surface < raised) rather than with stronger shadows; lighten the brand colour until its on-brand text passes; give logos and images a dark-safe variant or a neutral backing. Never produce dark mode by inverting colours.

**Token and layout example, not a universal value prescription:** a coherent space rhythm might use 4, 8, 12, 16, 24, 32, 48, and 64 CSS px. Choose what belongs to the brand and density; map components to roles such as `space-control`, `space-card`, `space-section`, and `space-page` rather than sprinkling a raw number across pages. Name corresponding density variants if the admin workspace needs tighter information. A type scale has roles such as display, page heading, section heading, card heading, body, supporting and data label; set line-height and max line length with each role. Prices and tabular metrics may need tabular figures, while long product titles need wrapping. Load at most two font families and only the weights in use, with `font-display: swap`, and preload the main text font. Links inside running text are underlined, because colour alone does not identify them.

**Breakpoint principle:** derive transitions from where the content stops fitting, not from a fixed device taxonomy. Verify small/large phones, portrait and landscape tablets, narrow/wide desktop, short viewports, browser zoom up to at least 200%, large text, and long or right-to-left translations if supported. Keep meaningful source order when the visual columns collapse. An offscreen mobile drawer must not steal focus when closed.

## 3. Consistency without repeating decoration

A shared layout should give pages the same navigation landmarks, content alignment, section rhythm, button hierarchy, filter/sort/view/column controls where applicable, icon family, notices, and status language. The amount of imagery and information density may vary with the customer's task. Do not force every fact into a card. Persistent, noncritical information should appear only if useful; its visible X and compact options menu have distinct Close, Minimize, Remind me in a week, and Never show again semantics. A new project's browser-local preference can remember minimization until reopening and a one-week reminder until expiry; store only the preference, not sensitive content. A time-critical, financial, safety or legal fact stays visible in an appropriate form.

The default card hierarchy is identity/media → title → decision information → primary action; remove fields that have no real data. Related cards align important rows without chopping off useful text to reach artificial equal heights. Section titles describe a task or a verified collection; duplicate products across shelves only when the repetition serves a distinct, explicit task.

Use one icon set's optical size, stroke, cap, corner treatment and meaning across pages. If the existing set is imperfect, document an alternative and obtain owner approval before replacing it. A wordmark, proof badge, provider logo, product image or font requires its own rights and usage check. Do not use color, animation, or icon shape alone to communicate a critical state.

## 4. Asset register and reuse

For **each** asset record `id; purpose; creator/owner and use rights; pages/components; master source; display format and dimensions; crop-safe region; light/dark and locale variants; alt text or decorative status; fallback; review date`. Give a shared asset one canonical identity and deduplicate byte-identical files. Do not force the same picture onto unrelated products: consistency lives in the visual grammar and asset rules.

| Family | Minimum task-specific decision | Fallback |
| --- | --- | --- |
| Identity | Wordmark, symbol, favicon and contrast variants | Accessible text brand name |
| UI icons | Search, navigation, cart, account, view, filter, sort, alert, action, delivery/access | Visible text labels; avoid font-glyph mystery icons |
| Product media | Hero, alternate angle, context, scale, detail, variant proof, optional video poster | Honest neutral media state, never a different variant's picture |
| Category/editorial | Consistent subject, lighting, composition and crop region | HTML heading and text remain available |
| Choice aids | Size/fit, shade, compatibility, dimensions, comparison, setup | Concise text decision support |
| Transaction and state | Loading, empty, pending, failed, confirmed, restricted | Meaningful title, explanation and next action |
| Admin | Data series, legends, status marks, document previews, source labels | Explicit no-data or stale-data state |
| Trust | Only verified delivery, returns, payment and support claims | Plain verified policy text without invented seal |
| Content and localization | Date, plural, currency, legal text, help illustrations | Correct locale string and no cut-off key data |

Use appropriate responsive formats and sizes; avoid transferring the full-resolution master into every card. Do not place essential text inside a decorative bitmap. Reserve media aspect ratio during loading; maintain accessible alternatives for functional images. Video requires a useful poster, visible controls when interactive, and no automatically played narration.

## 5. Interaction grammar

Choose a small family of motions by role: immediate feedback, state transition, panel transition, optional explanatory illustration, each bound to a theme duration role. Keep success tied to actual success. The rules for triggers, loops, tall cards, reduced motion and performance live in [motion-core.md](motion-core.md); record chosen motions with `assets/templates/motion-record.md`.

For color and interaction, verify the relevant accessibility requirements on the actual screen: text contrast, non-text contrast, focus visibility, target size or sufficient spacing, status text, meaningful order, resize/reflow, keyboard and assistive technology. Record exceptions with the actual component and condition, not a generic “accessible” label.
