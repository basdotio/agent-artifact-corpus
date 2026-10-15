# Flutter Delivery Contract

Use this reference before implementing premium Flutter mobile UI.

## Contents

- Existing Repo Contract
- Greenfield Contract
- Asset Sources
- Theme And Tokens
- Layout And Navigation
- Components
- Motion And Haptics
- Localization
- Accessibility
- Performance
- Validation
- Package Decision Rules
- Package Shortlist

## Existing Repo Contract

In an existing app:

- Read project instructions and nearest feature conventions first.
- Reuse current route, state, DI, theme, localization, icon, asset, and test patterns.
- Do not introduce a competing design system.
- Change the smallest layer that satisfies the request.
- Preserve behavior unless the user asks for UX or flow changes.
- Add packages only when the existing stack cannot reasonably cover repeated needs.

## Greenfield Contract

For a new Flutter mobile UI, produce only what the task needs. A full premium bundle can include:

- `ThemeData` with light and dark schemes.
- A small token layer with color roles, spacing, radius, type, motion, and elevation.
- `ThemeExtension` for non-Material product tokens.
- Reusable components for repeated controls: button, card, field, list row, empty state, sheet/banner.
- Full screens or flows with real content and all core states.
- ARB localization stubs when user-facing strings are introduced.
- Widget tests for core components and one focused flow/integration test when the path is important.
- Short rationale for visual decisions and validation commands.

Skip unused scaffolding. A one-screen task does not need a full starter kit, auth, billing, analytics, or CI.

## Asset Sources

Reuse the approved project asset library. For new imagery, icons, or fonts, use owned or appropriately licensed assets, record their source and usage basis, and retain required attribution. Keep demo content privacy-safe.

## Theme And Tokens

- Material 3 is the default since Flutter 3.16; don't set `useMaterial3: false` in new code. An M2 repo migrating: `platform-edges.md` M2 To M3 Migration.
- Build on `ColorScheme`, `TextTheme`, component themes, and `ThemeExtension`.
- Use semantic token names: action, surface, muted text, success, warning, danger, info.
- Define light and dark variants from the same brand direction.
- Keep radii, spacing, shadows, and motion as scales rather than arbitrary widget literals.
- Use project context extensions when they already exist.

Flutter specifics:

- Choose a product-appropriate `seedColor`; `ColorScheme.fromSeed` requires it and has no default seed. Override generated roles only when the product needs it, then verify contrast. `dynamicSchemeVariant` controls palette generation (for example, `DynamicSchemeVariant.fidelity` more closely follows the seed); `contrastLevel` ranges from -1.0 to 1.0, with 0.0 normal. Reach for `flex_seed_scheme` (`SeedColorScheme.fromSeeds`) only when primary, secondary, and tertiary need separate seeds. See the [constructor contract](https://api.flutter.dev/flutter/material/ColorScheme/ColorScheme.fromSeed.html).
- Use the M3 surface roles (`surfaceContainerLowest` through `surfaceContainerHighest`); the old `background`/`onBackground`/`surfaceVariant` roles are deprecated.
- Put anything non-Material (brand radii, custom color roles, spacing, gradients, semantic elevations) in a `ThemeExtension`. Each extension is immutable with `copyWith` and `lerp`; implementing `lerp` enables animated theme transitions. Access via `Theme.of(context).extension<T>()`.
- When using `google_fonts`, null the hard-coded M2 text colors so the `ColorScheme` drives color in an M3 theme; otherwise text picks up wrong light-mode colors. Bundle fonts as assets before release for deterministic rendering.
- M3 Expressive (spring motion, shape morphing, emphasized type) is not first-party in the Flutter SDK; treat its look as custom motion/shape/tokens, not a built-in switch. This is the one definition; other files point here.

## Layout And Navigation

- Decide layout on available window size, never device type.
- Use `LayoutBuilder` for local widget constraints.
- Use `MediaQuery.sizeOf(context)` for window-level decisions (not `MediaQuery.of`, which over-rebuilds).
- Material navigation breakpoints: `NavigationBar` under 600dp, `NavigationRail` 600-840dp, `NavigationDrawer` when expanded.
- Use `SafeArea` and keyboard-aware padding where content can collide with system UI. Edge-to-edge, status-bar icon brightness, orientation, and foldables: `platform-edges.md`.
- Use `Expanded`, `Flexible`, `Spacer`, `ConstrainedBox`, `AspectRatio`, slivers, and lazy builders instead of fixed positioning.
- Use bottom navigation for broad mobile destinations.
- Use sheets for secondary tasks and snackbars for lightweight confirmations (with undo where it fits), not for critical errors.
- Use platform-adaptive controls and `.adaptive()` constructors (`Switch.adaptive`, `AlertDialog.adaptive`, `showAdaptiveDialog`) for pickers, switches, dialogs, and input conventions when it matters.
- For routing with deep links, prefer `go_router`; named routes are no longer the recommended default.

## Components

Create wrappers only for repeated, business-critical controls. Good wrappers:

- Expose semantic props, not every raw style knob.
- Include loading, disabled, pressed, focus, and selected states where relevant.
- Use theme tokens internally.
- Keep text localization-friendly.
- Preserve native accessibility roles and focus behavior.

Do not wrap every framework widget "for later".

## Motion And Haptics

- Prefer built-in Flutter animation primitives first.
- Use motion tokens for duration and curve.
- Keep motion subtle and tied to state changes. Durations and easing direction: `craft-rubric.md` Motion.
- Pair haptics with high-value selection, success, or completion when platform conventions support it.
- Apply `platform-edges.md` Accessibility Settings Beyond Text Scale for reduced-motion behavior and the accessor; reuse a project wrapper if it preserves that contract.

Packages are options, not defaults; add only for repeated value:

- `flutter_animate`: chainable, controller-free micro-animations; effects are immutable, reuse a shared effect list.
- `skeletonizer`: turns the existing widget tree into a shimmer/pulse skeleton, no duplicate placeholder layout to maintain. Prefer over the older `shimmer` package.
- `gap`: `Gap(16)` along the parent axis; or const `SizedBox` constants on the 8pt grid.
- `HapticFeedback` (built-in) first; `gaimon` adds richer iOS-quality semantic haptics and custom patterns.
- Rive vs Lottie: Rive for interactive, stateful, GPU-rendered micro-interactions; Lottie for playback-only / After Effects pipelines. Do not add either runtime for a single icon.
- `cached_network_image` with BlurHash/LQIP for progressive image loading; `fl_chart` for data viz.

## Localization

- Do not hardcode user-facing strings in production widgets when the repo has localization.
- Use `flutter_localizations` + `intl`, ARB files, and generated localizations when the app follows Flutter's standard path. `slang` is an option for type-safe generation from JSON/YAML/CSV/ARB.
- Add translator context for ambiguous labels.
- Use plural/select formatting for counts and user-specific text; use locale-aware date/number/currency formatting.
- Test longer strings (German-length) when layout is dense. RTL directional layout and icon mirroring: `platform-edges.md` RTL And Directional Layout.

## Accessibility

- Add `Semantics` for custom controls and icon-only actions (`MergeSemantics` to group, `ExcludeSemantics` for decorative).
- Apply the contrast, target-size, text-scale, and input requirements in `craft-rubric.md` Accessibility Thresholds. Enlarge small icons' hit areas without changing their visual size.
- Preserve focus order and screen-reader order. Custom controls built on `GestureDetector` also need keyboard focus and Enter/Space activation (`platform-edges.md` Keyboard, Switch, And Focus Access).
- Do not rely on color alone.
- Read scaling with `MediaQuery.textScalerOf`; apply `craft-rubric.md` Accessibility Thresholds to the affected layout.
- Apply the reduced-motion contract in `platform-edges.md` Accessibility Settings Beyond Text Scale.

## Performance

- Use `const` constructors where possible; const widgets are reused, not rebuilt.
- Use `ListView.builder`, slivers, pagination-friendly models, and fixed extents when appropriate; tune `cacheExtent`.
- Apply Image Decode Sizing below to thumbnails and other bounded raster images.
- Keep CPU work out of `build`; cache results and use `compute()` for measured CPU-bound work with sendable data. Let the image provider/codec manage image decoding. A post-frame callback postpones work but does not move it off the UI isolate.
- Add `RepaintBoundary` only around genuinely expensive animated or painted subtrees.
- Avoid unnecessary `saveLayer`/`Clip.antiAliasWithSaveLayer` and deep transparent layers.
- Profile rich animation or media-heavy screens in profile mode on a physical device (DevTools Performance: UI thread vs raster thread) before claiming smoothness. Renderer availability and limitations follow the SDK/platform; consult Flutter's Impeller documentation before performance claims.

### Image Decode Sizing

For bounded raster images, request a decode size in physical pixels: rendered logical dimension × device pixel ratio, rounded up. Supply `cacheWidth`/`cacheHeight` to framework images or `memCacheWidth`/`memCacheHeight` to `CachedNetworkImage`. Preserve the source aspect ratio; when it differs from a `BoxFit.cover` target, size the decode to cover the target without stretching. SVGs have no raster decode-size parameter.

## Validation

Choose the smallest checks that prove the change:

- `flutter analyze` or repo equivalent for broad syntax/static issues.
- Focused widget tests for components and states.
- Golden or screenshot tests when visual structure changes.
- Accessibility guideline tests (`androidTapTargetGuideline`, `textContrastGuideline`, etc.) or manual screen-reader checks for custom controls.
- Profile-mode performance check for rich motion, media, charts, or long lists.
- `patrol` when a flow needs native dialog/permission interaction beyond `integration_test`; `widgetbook` for isolated component review and visual regression when the project uses it.

Report exact skipped checks and why.

### Run the bundled example

In a disposable Flutter project, place `example.dart` and `example_test.dart` together under `test/` (copy from this skill's `references/`). The example needs only `flutter` and `flutter_test`. Run `flutter analyze` and `flutter test test/example_test.dart`. Production adoption replaces the marked import and passes localized `label` and `busyLabel`.

Goldens are opt-in: first run `flutter test --dart-define=RUN_GOLDENS=true --update-goldens test/example_test.dart`, inspect the six images, then run without `--update-goldens`. Newly generated goldens alone prove no visual quality. Default widget-test fonts are Ahem blocks; use the project's bundled-font loader for typography inspection. Keep Flutter and the host OS fixed when comparing them.

Tests must inspect `tester.getSemantics(...)`, including the effective label, role, enabled state, and tap action. Checking only a `Semantics` widget's properties can miss merged duplicate labels. A content-only `Semantics(excludeSemantics: true)` inside a framework button replaces descendants while preserving the framework's outer activation semantics.

Evidence boundaries: analyzer and widget tests prove only the checked code/layout/semantics behaviors. Rendered inspection checks appearance. VoiceOver/TalkBack checks actual announcements and traversal. Profile mode on a physical device supports smoothness claims; widget tests do not.

API sources (check the installed SDK for version differences): [FilledButton](https://api.flutter.dev/flutter/material/FilledButton-class.html), [Semantics exclusion](https://api.flutter.dev/flutter/widgets/Semantics/excludeSemantics.html), [ThemeExtension](https://api.flutter.dev/flutter/material/ThemeExtension-class.html), [PopScope](https://api.flutter.dev/flutter/widgets/PopScope-class.html), [modal sheets](https://api.flutter.dev/flutter/material/showModalBottomSheet.html), [Impeller](https://docs.flutter.dev/perf/impeller). The 3.47.5 source counterparts are `packages/flutter/lib/src/material/button_style_button.dart`, `packages/flutter/lib/src/material/bottom_sheet.dart`, and `packages/flutter/lib/src/widgets/pop_scope.dart`, relative to the Flutter SDK root.

## Package Decision Rules

The package ladder lives in SKILL.md Package Rules. If a new package affects licensing, bundle size, store review, native permissions, or app startup, call that out in the final note. Confirm current versions on pub.dev before pinning; UI/motion packages move fast.

Freshness rule: any version-dependent claim in these references (SDK defaults, deprecations, "package X is preferred", M3 Expressive status) reflects the state when written. SDK examples verified: 2026-09-28 against Flutter 3.47.5 stable; package status last checked: 2026-09-25; if today is more than 6 months later, re-check every named API and package before relying on it. Before asserting one to a user or pinning a decision on it, verify against the current Flutter release notes or pub.dev — the ecosystem moves faster than this file.

## Package Shortlist

Reach for these only when justified, not by default. Each was checked on pub.dev on 2026-09-25: published, not discontinued. `flutter_platform_widgets` is discontinued, so don't add it. Use the framework `.adaptive()` constructors instead.

- Theming: `flex_seed_scheme`, `google_fonts` (bundle before release).
- Motion: `flutter_animate`, `animations`, Rive, Lottie.
- Loading: `skeletonizer`.
- Spacing: `gap`.
- Haptics: `gaimon`.
- Images/charts: `cached_network_image`, `fl_chart`.
- Routing: `go_router`.
- Review/test: `widgetbook`, `patrol`.
