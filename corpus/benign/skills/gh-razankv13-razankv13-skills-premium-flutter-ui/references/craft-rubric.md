# Craft Rubric

Use this reference for premium Flutter UI critique, polish, and scoring.

## Contents

- Score
- Anti-Generic Detector
- Hierarchy
- Color And Dark Mode
- Visual Direction
- Typography
- Labels, Badges, And Microcopy Density
- Spacing, Shape, And Depth
- Imagery And Controls Over Media
- Motion
- State Quality
- Accessibility Thresholds
- Performance Red Flags

## Score

Use `review-calibration.md` for numerical ratings and P0/P1/P2 severity. It defines evidence requirements, fixed anchors, and a worked example. Target 8+ for production work and 9+ for requested premium polish.

Run the squint test: blur or unfocus the screen; what stands out first should be the highest-priority content. If it is not, hierarchy is wrong.

## Applying The Rubric

Separate defects from aesthetic preferences. Contrast failures, clipped content, lost state, and inaccessible controls require fixes. Palette, font family, surface treatment, imagery, and density depend on the product; a style preference alone is not a defect or a score deduction. The examples below are starting points, not a mandatory house style.

## Anti-Generic Detector

Signals to investigate, not automatic violations. Flag one only when it weakens hierarchy, usability, coherence, or the stated identity; explain the observed effect. Follow deliberate repo direction.

- Purple/blue/cyan gradient identity with no brand reason.
- Gradient text on headings, metrics, prices, or dashboard numbers.
- Decorative glass, blur, glow, or neon used everywhere (including content-on-glass and glass-on-glass).
- Cards inside cards.
- Same-size card grids with icon, heading, and short text repeated across the screen.
- Large rounded icons above every heading.
- Big hero number plus small label plus gradient accent line repeated across dashboards.
- Centered body copy and uniform spacing rhythm everywhere.
- Default Material cards, AppBars, buttons, and shadows with no product layer.
- Over-rounded cards with floating glow shadows.
- Bounce or elastic easing in utilitarian flows.
- Inter/Roboto/Arial/Open Sans as the entire identity rather than a considered type system.
- Surface colors chosen without checking contrast, grouping, and product context.
- Placeholder copy, fake names, lorem ipsum, fake AI art, or content that dodges real edge cases.
- Only happy-path screens.
- Photo tiles whose labels lose contrast or whose inconsistent imagery impairs scanning.
- Icon sets mixing filled and outlined, mixed stroke weights, or a different color per icon.
- ALL-CAPS oversized primary button.
- Heavy dark divider lines between every section.
- Navigation icons sitting bare on a hero image, readable only because this one image happens to be dark.

Guiding test: would someone believe this was generated from a vague "clean modern app" prompt? Yes → revise. Fix direction: the Identity Contract in SKILL.md — choose the three identity carriers deliberately; add a signature detail only when it serves the product. Familiar platform controls and restrained utility screens are valid outcomes.

## Hierarchy

Check hierarchy before color:

- One primary job per screen is obvious within a squint.
- Primary action is reachable by thumb and visually stronger than secondary actions.
- Secondary details support decision-making instead of competing with the main task.
- Dense operational screens avoid marketing hero composition.
- Repeated workflows optimize scanning and comparison over decoration.

## Color And Dark Mode

- Reserve strong color for meaningful emphasis. A 60-30-10 split can be a starting point, not a required ratio.
- Choose neutral or tinted surfaces to fit the brand and content. Pure white or black is valid when contrast and grouping work.
- Build palettes in HSL/HCT; rotate hue to hit contrast, do not only crank lightness.
- Define semantic colors (success/warning/error/info) as tokens; never rely on color alone for status, add icon, text, or shape.
- Verify text and meaningful controls against Accessibility Thresholds below; calculate against the actual composited background.

Dark mode specifics:

- Choose dark surfaces for readability and distinguishable layers. Near-black, tinted gray, and pure black are options; verify text comfort, contrast, and surface separation in the rendered result.
- Express elevation through surface tone, not shadow; shadows mostly disappear on dark. In M3, step up the `surfaceContainerLowest` → `surfaceContainerHighest` roles for higher layers. The M2 white-overlay ladder (`applyElevationOverlayColor`) is legacy; don't add it to M3 themes.
- Choose text colors and weights for readable contrast on the actual dark surfaces; off-white is an option, not a requirement.
- Adjust accent and semantic colors when they overpower dark surfaces; preserve recognizable status and verify contrast.
- Verify text against the applicable contrast threshold rather than targeting one preferred ratio. Follow the product's appearance settings and platform conventions.

## Visual Direction

Use the product brief and existing identity. When neither defines a direction, choose a restrained layout with one emphasis color, readable type, and clear grouping; state the assumption. For audience-specific starting points, read `product-modes.md` Visual Direction Presets.

Map the chosen direction to Flutter decisions: `TextTheme` for hierarchy, `ColorScheme` for emphasis/surfaces, component themes for shape, and motion tokens for feedback. Explain which content or user task each decision supports.

For requested translucent navigation, implement a bounded `BackdropFilter` + `ImageFilter.blur` with a contrast-tested surface tint and an opaque fallback. This is a blur treatment, not a claim of native Liquid Glass fidelity. Keep reading surfaces opaque and profile the effect before making performance claims. Use native/platform-specific material only after checking the project's installed SDK and integration support.

Material defaults and version-dependent capabilities: `flutter-delivery-contract.md` Theme And Tokens.

## Typography

- Use two core type voices at most: one display/heading voice and one body/label voice; one strong family is often enough. Build hierarchy with size, weight, color, and line height, not more fonts.
- Start with the product's readable body type scale; around 16 logical pixels can suit consumer content. Judge size, weight, density, and text scaling together rather than enforcing one size or heading ratio.
- Start body line height at 1.4–1.6 for reading content; use the project font metrics and content density to adjust it. Check multiline readability and scaling in the rendered result.
- Keep body text readable; avoid light/thin weights below 18px, they disappear at small sizes.
- Prefer left-aligned body copy for reading; centered body forces the eye to relocate each line.
- Use tabular numerals for aligned balances, prices, scores, and dashboard metrics.
- Honor text scaling; do not freeze text scale to make layout pass. A custom display font plus a system body font is a strong, native-feeling premium combination.

## Labels, Badges, And Microcopy Density

- Give each badge one fact. Start with a short label ("20% off"); retain the words required for meaning and localization. Remove icons or synonyms that repeat the same fact.
- When the brand uses uppercase labels, apply tracking appropriate to that font. Default action labels to sentence case; preserve a deliberate brand treatment when readability and hierarchy hold.
- Remove labels only when meaning stays clear. Preserve distinctions between unit price, total, fees, and quantities, plus accessible names for controls.
- Place relevant trust evidence near the decision it supports; a compact rating row near a product title is one option when genuine review data exists.
- Commit control text carries the outcome: "Add to cart · $6.20", quantity control shows its unit inside ("0.5 kg").

## Spacing, Shape, And Depth

- Use a constrained spacing scale, usually 4/8/12/16/24/32/48/64 (8pt grid). Start with too much whitespace, then remove.
- One horizontal margin token (commonly 16 or 24) that every edge snaps to. Elements drifting a few px left or right are not noticed consciously but the screen reads as less calm and less trustworthy.
- Spacing expresses relationships, not emptiness: too much space between related sections disconnects them. Tighten until sections read as one flow.
- Use fewer borders; separate with spacing, surface changes, or shadow only when useful. When a divider is needed it is the lightest line that still separates (low-alpha `outlineVariant`); heavy rules chop the page into blocks.
- Shadows are subtle, two-part, transparent-dark (not opaque gray); light comes from above.
- Shape scale communicates personality but stays disciplined.
- If everything floats, nothing has depth.
- Avoid nested surface frames unless the hierarchy genuinely requires containment.

## Imagery And Controls Over Media

Design for the image system, not the one image in the mockup. A screen holding product, user, or content photos must survive dark, bright, busy, and clean images; test with at least one of each.

- Controls drawn over imagery (back, share, favorite) sit on a subtle container — a tinted scrim or a semi-opaque surface pill with a thin outline. Never borrow contrast from the current photo.
- Image selection: the focal point is the subject, not props or hands; the image matches the unit sold or selected (an item sold by weight shows a pile, not one piece); natural, honest treatment for food, health, and trust-heavy products; consistent background, lighting, and crop across the catalog so a grid reads as one system.
- Category tiles: solid backgrounds with isolated imagery can unify an inconsistent catalog. Text lists or photo tiles may suit other content; compare scanability and verify contrast across representative images before choosing.
- Summaries can use thumbnails with "+N" when visual recognition helps. Keep text lists where names, quantities, or exact comparison matter; expose the full contents accessibly.
- Icons in a feature or benefit row share one style (all outlined or all filled), one stroke weight, and one or two colors used intentionally.

## Motion

Motion exists to communicate:

- Pressed, selected, loading, saving, success, error, reveal, navigation, or completion.
- Micro-interactions: about 100-200ms.
- View transitions: about 300-500ms.
- Staggers: about 50-100ms when guiding attention.

Easing direction matters: entering elements use ease-out (arrive fast, settle); exiting elements use ease-in (start slow, leave fast); elements that change while staying on screen use ease-in-out. Customize the curve to the element's weight rather than the default ease. Establish 2-3 reusable curves and reuse them. Spring physics (stiffness + damping) suits gesture-driven, re-targetable motion; lower damping for hero overshoot, higher for utilitarian calm.

Use restrained easing in utilitarian flows. Reduced-motion behavior and its Flutter accessor are defined in `platform-edges.md` Accessibility Settings Beyond Text Scale. Pair haptics with key actions when the platform and task call for tactile feedback.

## State Quality

Premium UI is visible off the happy path:

- Loading state preserves layout and avoids jumpy spinners; prefer skeletons that match final layout dimensions over a generic spinner.
- Empty state explains what happened and the next useful action. Three useful kinds: informational, action-focused (guide and point to the first action), and celebratory ("all caught up"). Treat empties as onboarding, not 404s.
- Error state is specific, plain-language, recoverable, and not color-only ("that email looks off, did you mean gmail.com?"). Offer retry/undo.
- Disabled state explains or implies why action is unavailable.
- Success state confirms without blocking flow unnecessarily. Use optimistic UI only for recoverable changes with explicit pending/failure feedback and rollback or reconciliation; show confirmed success only after authoritative completion for payments, permissions, or irreversible actions.
- Destructive and money/security actions have confirmation, undo, or recovery where appropriate.
- Search pre-query state (recents, popular, suggestions) and lifecycle-stage home variants (new / returning / power) are states too; cover them like loading and empty. Structure and rules: `screen-patterns.md`; flow rules: `mobile-ux` playbooks.

## Accessibility Thresholds

This section owns contrast, target-size, and text-scale thresholds. Other references apply these checks to their layouts. Block release-level claims when:

- Tap targets are below 48x48 dp on Android-style surfaces or 44x44 pt on iOS-style surfaces.
- Text contrast is below 4.5:1 for normal text or 3:1 for large text (18pt / 24 logical px regular, or 14pt / ~18.7 logical px bold). Meaningful icons, focus indicators, and control boundaries need 3:1 against adjacent colors; decorative separators and inactive controls are not subject to that non-text threshold.
- Custom controls lack `Semantics` labels, roles, values, or hints.
- Text scale 2.0 causes overflow on narrow phones.
- Focus or screen-reader order differs from visual order in a confusing way.
- Important animation fails the reduced-motion contract in `platform-edges.md` Accessibility Settings Beyond Text Scale.
- Custom controls cannot be focused and activated from a keyboard, or have no visible focus indicator.
- Layout breaks or directional icons point the wrong way in RTL.

Verify with Flutter's Guideline API in widget tests (`androidTapTargetGuideline`, `iOSTapTargetGuideline`, `textContrastGuideline`, `labeledTapTargetGuideline`) plus a manual screen-reader pass.

## Performance Red Flags

Frame budget is 16.67ms at 60fps and 8.33ms at 120fps; exceeding it drops frames.

- Eager long lists instead of lazy builders (`ListView.builder`, slivers); set fixed extents where possible.
- Heavy computation or parsing in `build`; move it out of build and cache results. Use `compute()` for measured CPU-bound work with sendable inputs/results.
- Oversized images loaded for thumbnails; apply `flutter-delivery-contract.md` Image Decode Sizing.
- Rebuilding full screens for small state changes; missing `const` constructors.
- Expensive effects without `RepaintBoundary` around the animated subtree (use sparingly, it costs memory).
- Multiple animation runtimes added for ornamental use.
- Custom fragment shaders that are not simple. Impeller precompiles its shaders; it does not eliminate all raster or runtime jank. Verify renderer/platform support against the SDK in use; keep shaders cheap.

Profile in profile mode on a physical device before claiming smoothness.
