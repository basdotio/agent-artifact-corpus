// Reference implementation: the smallest useful token layer + one branded
// component built on it. Adapt names and values to the target product —
// never paste the palette as-is (that would recreate the generic-default
// problem this skill exists to prevent).
//
// Shows, in order:
//   1. A ThemeExtension holding non-Material product tokens (with lerp,
//      so theme changes animate).
//   2. A context extension so call sites read `context.tokens.spacingMd`,
//      not `Theme.of(context).extension<AppTokens>()!`.
//   3. Wiring tokens into ThemeData for light and dark from one brand
//      direction.
//   4. One branded button with loading / disabled / pressed / focused states,
//      keyboard-activatable, styled through tokens — zero raw
//      literals at the call site.

import 'package:flutter/material.dart';

import 'dart:ui' show lerpDouble;

import 'package:flutter/foundation.dart' show lerpDuration;

// ---------------------------------------------------------------------------
// 1. Token layer. Everything non-Material lives here: brand radii, spacing,
// motion. Keep only tokens this component uses; add shared product tokens
// when another implemented control needs them.
// ---------------------------------------------------------------------------
@immutable
class AppTokens extends ThemeExtension<AppTokens> {
  const AppTokens({
    required this.spacingSm,
    required this.spacingMd,
    required this.spacingLg,
    required this.radiusControl,
    required this.pressDuration,
  });

  final double spacingSm;
  final double spacingMd;
  final double spacingLg;
  final double radiusControl; // buttons, fields
  final Duration pressDuration; // micro-interaction, ~100-200ms

  // Geometry and press timing stay consistent across brightness modes.
  // ColorScheme owns this component's light/dark colors below.
  static const light = AppTokens(
    spacingSm: 8,
    spacingMd: 16,
    spacingLg: 24,
    radiusControl: 10,
    pressDuration: Duration(milliseconds: 120),
  );

  static const dark = light;

  @override
  AppTokens copyWith({
    double? spacingSm,
    double? spacingMd,
    double? spacingLg,
    double? radiusControl,
    Duration? pressDuration,
  }) => AppTokens(
    spacingSm: spacingSm ?? this.spacingSm,
    spacingMd: spacingMd ?? this.spacingMd,
    spacingLg: spacingLg ?? this.spacingLg,
    radiusControl: radiusControl ?? this.radiusControl,
    pressDuration: pressDuration ?? this.pressDuration,
  );

  @override
  AppTokens lerp(AppTokens? other, double t) {
    if (other == null) return this;
    return AppTokens(
      spacingSm: lerpDouble(spacingSm, other.spacingSm, t)!,
      spacingMd: lerpDouble(spacingMd, other.spacingMd, t)!,
      spacingLg: lerpDouble(spacingLg, other.spacingLg, t)!,
      radiusControl: lerpDouble(radiusControl, other.radiusControl, t)!,
      pressDuration: lerpDuration(pressDuration, other.pressDuration, t),
    );
  }
}

// ---------------------------------------------------------------------------
// 2. Access sugar. Call sites should read like design vocabulary.
// ---------------------------------------------------------------------------
extension AppTokensX on BuildContext {
  AppTokens get tokens => Theme.of(this).extension<AppTokens>()!;
  ColorScheme get colorScheme => Theme.of(this).colorScheme;
}

// ---------------------------------------------------------------------------
// 3. Theme wiring. Seed gives harmony; overriding primary keeps the exact
// brand color instead of the seed's tonal drift. Choose the seed from
// the product brief; purple is valid when it is the intended brand.
// ---------------------------------------------------------------------------
ThemeData buildTheme(Brightness brightness) {
  const brand = Color(0xFF0E5A4A); // the product's actual brand color
  final scheme = ColorScheme.fromSeed(
    seedColor: brand,
    brightness: brightness,
  ).copyWith(primary: brightness == Brightness.light ? brand : null);

  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    extensions: [
      brightness == Brightness.light ? AppTokens.light : AppTokens.dark,
    ],
  );
}

// ---------------------------------------------------------------------------
// 4. A branded FilledButton retains framework semantics and input behavior.
// Localize both labels at the call site. Keep the visible label unchanged while
// busy; the reserved progress slot prevents idle/busy layout shifts.
// ---------------------------------------------------------------------------
class BrandButton extends StatelessWidget {
  const BrandButton({
    super.key,
    required this.label,
    required this.busyLabel,
    required this.onPressed,
    this.busy = false,
  });

  final String label;
  final String busyLabel;
  final VoidCallback? onPressed;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final scheme = context.colorScheme;
    final reducedMotion = MediaQuery.disableAnimationsOf(context);
    // Use the medium spacing token for the progress glyph's size in this example.
    final progressSize = t.spacingMd;
    // The 48px minimum is the accessibility floor; 2px focus/progress strokes
    // are fixed affordance widths for this sample, not new brand tokens.
    return FilledButton(
      onPressed: busy ? null : onPressed,
      style:
          FilledButton.styleFrom(
            backgroundColor: scheme.primary,
            foregroundColor: scheme.onPrimary,
            disabledBackgroundColor: busy ? scheme.primary : null,
            disabledForegroundColor: busy ? scheme.onPrimary : null,
            minimumSize: const Size(48, 48),
            visualDensity: VisualDensity.standard,
            padding: EdgeInsets.symmetric(
              horizontal: t.spacingLg,
              vertical: t.spacingSm,
            ),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(t.radiusControl),
            ),
            animationDuration: reducedMotion ? Duration.zero : t.pressDuration,
            splashFactory: reducedMotion ? NoSplash.splashFactory : null,
          ).copyWith(
            side: WidgetStateProperty.resolveWith(
              (states) => BorderSide(
                color: states.contains(WidgetState.focused)
                    ? scheme.onSurface
                    : Colors.transparent,
                width: 2,
                strokeAlign: BorderSide.strokeAlignOutside,
              ),
            ),
          ),
      // Exclude only child content. FilledButton owns the button role, enabled
      // state and tap action outside this node; replacing them would lose access.
      child: Semantics(
        label: busy ? busyLabel : label,
        excludeSemantics: true,
        child: Stack(
          alignment: Alignment.center,
          children: [
            Padding(
              padding: EdgeInsets.symmetric(
                horizontal: progressSize + t.spacingSm,
              ),
              child: Text(label, textAlign: TextAlign.center),
            ),
            if (busy)
              PositionedDirectional(
                start: 0,
                child: SizedBox.square(
                  dimension: progressSize,
                  child: reducedMotion
                      ? Icon(Icons.hourglass_empty, size: progressSize)
                      : CircularProgressIndicator(
                          strokeWidth: 2,
                          color: scheme.onPrimary,
                        ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
