# Platform Edges

Use this reference when the change touches system bars, device shape, text direction, input
method, accessibility settings beyond text scale, dynamic color, remote images, or an M2 → M3
theme migration. APIs are checked against Flutter 3.47 stable (see the freshness rule in
`flutter-delivery-contract.md`).

## Contents

- System Bars And Edge-To-Edge
- Width Classes, Orientation, Foldables
- RTL And Directional Layout
- Keyboard, Switch, And Focus Access
- Accessibility Settings Beyond Text Scale
- Dynamic Color
- Remote Images
- Permission Denied
- M2 To M3 Migration

## System Bars And Edge-To-Edge

Flutter apps draw edge-to-edge by default (`SystemUiMode.edgeToEdge`), and Android 15+ enforces it
for apps targeting SDK 35. Content lies under the status and navigation bars unless you inset it.

- Inset content with `SafeArea` or `MediaQuery.paddingOf(context)`. Let backgrounds, hero images,
  and sheets extend under the bars. Only content and controls stay inside the insets.
- Set status-bar icon brightness per screen, based on what is actually behind the bar:
  `AppBar(systemOverlayStyle: …)` when an app bar exists, otherwise wrap the screen in
  `AnnotatedRegion<SystemUiOverlayStyle>`. A hero photo under the status bar gets a scrim behind
  the bar (see `screen-patterns.md` Controls Over Imagery), not icon colors picked for one photo.
- Edge-to-edge supplies transparent Android gesture navigation; `systemNavigationBarColor` does not control it under enforced edge-to-edge. That property applies only to older non-edge-to-edge configurations. Keep bottom actions above `MediaQuery.paddingOf(context).bottom`.
- Don't opt out of edge-to-edge to hide an inset bug. Fix the inset instead.

## Width Classes, Orientation, Foldables

- Breakpoints and navigation choice are defined once in `flutter-delivery-contract.md` Layout And
  Navigation. Landscape phones cross 600dp. Test the landscape path whenever the app doesn't lock
  orientation, not only tablets.
- Landscape with the keyboard open leaves roughly 150dp of height. Forms and sheets must scroll, and
  their sticky action bars may drop inline.
- Foldables: read `MediaQuery.displayFeaturesOf(context)`. Keep tap targets and text off a hinge
  (`DisplayFeatureType.hinge`). Two-pane layouts split along the feature, not the midpoint.
- Only lock orientation when the product requires it (camera, a game). Say so in the final note.

## RTL And Directional Layout

- Use `EdgeInsetsDirectional`, `AlignmentDirectional`, `PositionedDirectional`, and
  `BorderRadiusDirectional` wherever left and right differ. Use `start`/`end`, never `left`/`right`,
  for anything tied to reading order.
- Directional icons mirror. Framework icons like `Icons.arrow_back` already set
  `matchTextDirection: true`. Prefer `Icons.adaptive.arrow_back` for platform-correct back. Custom
  `IconData` and SVG chevrons need an explicit flip (`Transform.flip(flipX: isRtl)`). Don't mirror
  media controls, clocks, or logos.
- Format numbers, dates, and currency with the locale-aware formatter; preserve its bidi marks and placement. Isolate inherently LTR identifiers such as phone numbers when needed, rather than forcing every formatted amount to LTR.
- Verify with a test harness that wraps the subject in `Directionality(textDirection:
  TextDirection.rtl)` and checks for overflow and chevron direction.

## Keyboard, Switch, And Focus Access

Every custom interactive widget built on `GestureDetector` needs the same access a `ButtonStyleButton`
gets for free: focusable, activated by Enter/Space, and showing a visible focus indicator.

- Prefer a framework button: `example.dart` shows `FilledButton` retaining built-in focus and activation. For a necessary custom `GestureDetector` control, add `FocusableActionDetector` (or `Focus` + `Actions` + `Shortcuts`) with an `ActivateIntent` handler using the tap callback, and verify the effective semantics tap action.
- Draw a visible focus ring from a semantic color role (`primary`, `secondary`, or `onSurface`) that passes `craft-rubric.md` Accessibility Thresholds against adjacent colors. Match its width and offset to the control; the reference button uses a 2dp outer ring. Do not rely on a fill-color change alone.
- Traversal order follows visual order. Use `FocusTraversalGroup` + `OrderedTraversalPolicy` only
  when the layout order diverges from the reading order.
- When a flow opens a sheet or dialog, send focus into it, and return focus to the trigger on
  close. Modal routes do this by default, so don't break it with manual `requestFocus`.

## Accessibility Settings Beyond Text Scale

| Setting | Read with | What the UI does |
|-|-|-|
| Reduce motion | `MediaQuery.disableAnimationsOf(context)` | Remove spatial motion and repeating animation; use instant state changes, or a brief non-spatial fade when the product access contract permits it. Keep progress understandable with a static indicator and localized status text. |
| Bold text (iOS) | `MediaQuery.boldTextOf(context)` | Flutter `Text` applies this setting to its effective style; verify layout and explicitly styled spans. Handle the setting manually for `RichText`/custom text rendering that bypasses `Text`. |
| High contrast | `MediaQuery.highContrastOf(context)` | Provide a higher-contrast scheme through `MaterialApp.highContrastTheme`/`highContrastDarkTheme`; when deriving it with `ColorScheme.fromSeed`, retain the product seed and set `contrastLevel: 1.0`. Verify essential boundaries as well as text. |
| Screen reader | `MediaQuery.accessibleNavigationOf(context)` | Auto-dismissing snackbars and timeouts become persistent, or get longer durations. |

`disableAnimationsOf` is the one reduced-motion accessor. Use it everywhere; the older
`MediaQuery.of(context).disableAnimations` rebuilds on every MediaQuery change.

## Dynamic Color

Android 12+ wallpaper color (Material You) is a product choice. It isn't a default.

- A brand-led product keeps its brand scheme. Wallpaper color would erase the identity carriers
  (SKILL.md Identity Contract).
- For a utility or personal-tool product that opts in, use `dynamic_color` (`DynamicColorBuilder`)
  with the brand scheme as the fallback. Harmonize semantic colors (`Color.harmonizeWith`) so
  success and danger stay recognizable. Keep the `ThemeExtension` tokens that aren't color
  (radius, spacing, motion) unchanged.
- iOS has no wallpaper palette, so the brand fallback is what iOS users see. Design it first.

## Remote Images

- Every `Image.network` / `CachedNetworkImage` gets a loading placeholder at final size (a
  skeleton or BlurHash) and an `errorBuilder` / `errorWidget`. The error state is a neutral
  tinted block with an icon at the same size. Layout doesn't jump, and there's no broken-image
  glyph.
- Apply `flutter-delivery-contract.md` Image Decode Sizing to the placeholder and final raster image bounds.
- For framework `Image`, use `semanticLabel` for content and `excludeFromSemantics: true` for decoration. For `CachedNetworkImage`, use a `Semantics(image: true, label: ...)` or `ExcludeSemantics` wrapper; it does not expose those Image parameters.

## Permission Denied

When to ask, and how to explain it before the OS prompt, is `mobile-ux` territory. This skill
builds the screen state for after a denial, which every camera, location, photo, contacts, and
notification feature needs.

- Render the denial as an in-place state of the feature, not a dialog and not a blank screen. It
  names what's unavailable, what the permission unlocks ("Scan receipts with your camera"), and one
  primary action.
- Drive the action from the permission type and platform status returned by the installed plugin. Ask again only when requestable; for permanently denied access offer settings and re-check on `AppLifecycleState.resumed`. Restricted access may not be user-changeable: explain the restriction and retain a fallback. Check notification, location, and photo-specific states rather than treating every iOS denial identically.
- Keep a fallback path visible when one exists (manual address entry, choose from files).
- iOS limited photo access is a partial grant. Show the selected photos plus a "Manage selection"
  control, not a denial.

## M2 To M3 Migration

For an existing M2 repo moving to M3, or an M3 repo still carrying M2 remnants:

1. Replace deprecated roles: `background` → `surface`, `onBackground` → `onSurface`,
   `surfaceVariant` → `surfaceContainerHighest`.
2. Adopt M3 counterparts where behavior matches: `BottomNavigationBar` → `NavigationBar`, `ToggleButtons` → `SegmentedButton`. `ElevatedButton` already supports M3; retain it when elevation fits the hierarchy, and choose `FilledButton` when a filled, unelevated action fits the product.
   `FilledButton`, `ToggleButtons` → `SegmentedButton`.
3. Elevation: M3 separates layers with the `surfaceContainer*` tones, not the M2 white overlay.
   Remove `applyElevationOverlayColor` and custom overlay math.
4. Typography: M3 names (`displayLarge`… `labelSmall`). Map every custom `TextStyle` to one role.
5. Migrate one layer per change (Revision Mode in `product-modes.md`), and update goldens with it.
   Report any screen left on M2 styling.
