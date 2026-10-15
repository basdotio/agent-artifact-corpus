# Serve licensed fonts from the site

Date rule: [establish ASK DATE and revalidate claims](research-and-memory.md#ask-date-rule).
Source status: external facts and example commands are UNVERIFIED until checked for the chosen version and engagement.
Record opened URLs, source dates or unknown, actual access dates, and supporting evidence.

Question: how can the chosen type remain legible without a third-party font request?

## Verify the exact rights

Identify font family, version, source file, and license text.
Check web embedding, redistribution, and proposed subsetting separately.
Preserve required notices with the authorized woff2 files.
A screenshot or a public font download is not evidence of those rights.
Unknown rights keep the font out of the release; use an approved fallback for drafts.

## Map type roles to files

List body, heading, UI, and emphasis roles with used weights and styles.
Include only faces the selected design actually needs.
Test required language glyphs before subsetting; do not remove content's characters.
Confirm the fallback has usable shapes, metrics, and coverage.
Do not rely on synthetic weight or style when the approved design needs a real face.

## Define loading behavior

```css
@font-face {
  font-family: 'Project Sans';
  src: url('/assets/fonts/project-sans-regular.woff2') format('woff2');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}
body { font-family: 'Project Sans', system-ui, sans-serif; }
```

This is a file naming and loading example, not a supplied or licensed font.
Choose display behavior for the content and test the fallback-to-loaded transition.
Use metric overrides only after measuring the actual fallback and loaded face.
Preload only critical faces with correct type and cross-origin fetch behavior.
Confirm the preload and CSS reference resolve to the same resource.

## Verify failure and delivery

Block font requests and complete the primary journey using fallbacks.
Inspect all font requests and redirects; keep them on approved first-party origins.
Use font-src 'self' in the site's tailored CSP and test the enforced response.
Record layout shift, line wrapping, missing glyphs, and weight/style selection.
Check long copy and translated content when applicable.
Apply checklists/performance-seo.md PS03 and checklists/brand-and-mockups.md BM07.

## Failure modes and sources

- License mismatch: desktop use is mistaken for web redistribution permission.
- Hidden external load: imported CSS contacts a font provider.
- Duplicate transfer: a mismatched preload fetches a face twice.
- Fragile layout: loaded type hides a broken fallback.

Open the font's actual license and current font loading documentation at
https://developer.mozilla.org/en-US/docs/Web/CSS/@font-face before implementation.
No third-party font binaries ship with this skill.
