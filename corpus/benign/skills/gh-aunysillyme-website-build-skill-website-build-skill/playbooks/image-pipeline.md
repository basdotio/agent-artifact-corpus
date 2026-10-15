# Deliver images for their actual slots

Date rule: [establish ASK DATE and revalidate claims](research-and-memory.md#ask-date-rule).
Source status: external facts and example commands are UNVERIFIED until checked for the chosen version and engagement.
Record opened URLs, source dates or unknown, actual access dates, and supporting evidence.

Question: how do images remain useful and sharp within the route's loading budget?

## Inventory before transforming

Record source identity, rights evidence, intrinsic dimensions, image role, focal point,
crop intent, background/transparency, decorative status, and alt-text intent.
Preserve authorized originals and required notices under Graphics ownership.
Strip unnecessary sensitive metadata from public exports without altering the original.
Unknown rights block release of that asset.

## Choose transformations

Measure layout slots at representative widths and display densities.
Generate AVIF and WebP candidates using the selected supported sharp version.
Retain a browser-usable original-format fallback for the same composition.
Do not ship an unsuitable source format as the fallback solely because it is original.
Record a conversion when the master is a design file rather than a web image.
Compare compression by inspecting edges, small text, gradients, and the intended crop.
Quality and width settings are choices to measure, never universal defaults.

## Define a deterministic pipeline

```text
input: original bytes + crop + widths + quality settings + encoder version
process: validate -> orient -> crop -> resize -> encode -> inspect
output: content-keyed variants + actual dimensions + byte sizes + manifest
invalidate: any input bytes, settings, crop, or encoder version changes
```

Use a documented TypeScript build script with sharp as a declared build dependency.
Read current API documentation before implementing format options.
Reject enlargements that cannot meet the approved visual requirement.
Rebuild from source rather than recompressing already compressed derivatives.

## Connect markup to layout

Use picture sources for AVIF and WebP with an img fallback.
Set srcset widths from actual exports and sizes from the rendered CSS slots.
Set width and height from the real file and reserve the matching aspect ratio.
Do not claim dimensions from a requested export setting without inspecting the result.
Give meaningful images task-relevant alternatives; use empty alternatives for decoration.

## Protect the first screen

Identify the likely LCP image from the real route and a measurement trace.
Make the important image discoverable in initial HTML and avoid lazy loading it.
Lazy load appropriate below-fold images and test behavior with JavaScript unavailable.
Avoid preloading every image; verify that a critical preload matches the selected resource.

## Verify and hand off

Inspect desktop/mobile crops and representative density combinations in a browser.
Record the selected resource, actual dimensions, byte size, request timing, and visual result.
Compare the route budget before and after the pipeline change.
Measure each social card independently and pass its actual dimensions to Optimizer.
Graphics hands an immutable export revision and rights ledger to Builder.
Apply checklists/brand-and-mockups.md BM07 and checklists/performance-seo.md PS03.

## Failure modes and sources

- Mismatched sizes: the browser fetches a large variant for a narrow slot.
- Crop loss: the focal subject disappears on mobile.
- False dimensions: one social-card size is copied across unequal files.
- Nondeterminism: unchanged originals churn names and invalidate caches.

Open https://sharp.pixelplumbing.com/ and the selected browser image guidance.
Record the exact API version, actual source access, and inspected export results.
