// Keep beside example.dart in a scratch Flutter project's test/ directory.
// Run: flutter analyze && flutter test test/example_test.dart
// Optional goldens (inspect new images before accepting them):
// flutter test --dart-define=RUN_GOLDENS=true --update-goldens test/example_test.dart
// flutter test --dart-define=RUN_GOLDENS=true test/example_test.dart
// Default widget-test fonts are Ahem blocks: useful for geometry, not typography.
// Load the project's bundled fonts before goldens when judging actual text.
// Pin Flutter and the host OS for golden comparisons. Copy only tests relevant
// to the changed behavior; these tests do not replace native screen-reader QA.
import 'dart:ui' show SemanticsAction, SemanticsActionEvent, Tristate;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

// EDIT FIRST when adopting: replace with your project's component import.
import 'example.dart';

const _label = 'Add to cart · \$3.10';
const _busyLabel = 'Adding to cart';
BrandButton _button({bool busy = false, VoidCallback? onPressed}) =>
    BrandButton(
      label: _label,
      busyLabel: _busyLabel,
      busy: busy,
      onPressed: onPressed,
    );

Widget _harness(
  Widget child, {
  Brightness brightness = Brightness.light,
  double textScale = 1,
  bool reducedMotion = false,
  TextDirection direction = TextDirection.ltr,
}) => MaterialApp(
  debugShowCheckedModeBanner: false,
  theme: buildTheme(brightness),
  home: Builder(
    builder: (context) => MediaQuery(
      data: MediaQuery.of(context).copyWith(
        textScaler: TextScaler.linear(textScale),
        disableAnimations: reducedMotion,
      ),
      child: Directionality(
        textDirection: direction,
        child: Scaffold(
          body: Center(
            child: Padding(padding: const EdgeInsets.all(16), child: child),
          ),
        ),
      ),
    ),
  ),
);

void _narrowPhone(WidgetTester tester) {
  tester.view.physicalSize = const Size(640, 1136);
  tester.view.devicePixelRatio = 2;
  addTearDown(tester.view.reset);
}

void main() {
  if (const bool.fromEnvironment('RUN_GOLDENS')) {
    for (final brightness in Brightness.values) {
      for (final state in ['idle', 'busy', 'disabled']) {
        testWidgets('golden: $state (${brightness.name})', (tester) async {
          _narrowPhone(tester);
          await tester.pumpWidget(
            _harness(
              _button(
                busy: state == 'busy',
                onPressed: state == 'disabled' ? null : () {},
              ),
              brightness: brightness,
            ),
          );
          await tester.pump(const Duration(milliseconds: 200));
          await expectLater(
            find.byType(BrandButton),
            matchesGoldenFile(
              'goldens/brand_button_${state}_${brightness.name}.png',
            ),
          );
        });
      }
    }
  }

  testWidgets('tap targets, contrast and labels in both themes', (
    tester,
  ) async {
    final handle = tester.ensureSemantics();
    try {
      _narrowPhone(tester);
      for (final brightness in Brightness.values) {
        await tester.pumpWidget(
          _harness(_button(onPressed: () {}), brightness: brightness),
        );
        await tester.pumpAndSettle();
        await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
        await expectLater(tester, meetsGuideline(iOSTapTargetGuideline));
        await expectLater(tester, meetsGuideline(textContrastGuideline));
        await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
      }
    } finally {
      handle.dispose();
    }
  });

  for (final direction in TextDirection.values) {
    testWidgets('long localized label at 320dp, 2x, ${direction.name}', (
      tester,
    ) async {
      _narrowPhone(tester);
      const label = 'Lieferadresse für Alexandra Konstantinidis speichern';
      await tester.pumpWidget(
        _harness(
          BrandButton(
            label: label,
            busyLabel: 'Adresse wird gespeichert',
            busy: true,
            onPressed: () {},
          ),
          textScale: 2,
          direction: direction,
        ),
      );
      await tester.pump(const Duration(milliseconds: 200));
      expect(tester.takeException(), isNull);
      final textRect = tester.getRect(find.text(label));
      final buttonRect = tester.getRect(find.byType(BrandButton));
      expect(buttonRect.contains(textRect.topLeft), isTrue);
      expect(buttonRect.contains(textRect.bottomRight), isTrue);
    });
  }

  testWidgets('single localized semantics label and usable tap action', (
    tester,
  ) async {
    final handle = tester.ensureSemantics();
    try {
      var taps = 0;
      for (final state in ['idle', 'busy', 'disabled']) {
        await tester.pumpWidget(
          _harness(
            BrandButton(
              label: 'Speichern',
              busyLabel: 'Wird gespeichert',
              busy: state == 'busy',
              onPressed: state == 'disabled' ? null : () => taps++,
            ),
          ),
        );
        final node = tester.getSemantics(find.text('Speichern'));
        expect(node.label, state == 'busy' ? 'Wird gespeichert' : 'Speichern');
        expect(node.flagsCollection.isButton, isTrue);
        expect(
          node.flagsCollection.isEnabled,
          state == 'idle' ? Tristate.isTrue : Tristate.isFalse,
        );
        expect(
          node.getSemanticsData().hasAction(SemanticsAction.tap),
          state == 'idle',
        );
        if (state == 'idle') {
          tester.binding.performSemanticsAction(
            SemanticsActionEvent(
              type: SemanticsAction.tap,
              nodeId: node.id,
              viewId: tester.view.viewId,
            ),
          );
          expect(taps, 1);
        }
      }
    } finally {
      handle.dispose();
    }
  });

  testWidgets('busy keeps geometry and active contrast in both themes', (
    tester,
  ) async {
    for (final brightness in Brightness.values) {
      await tester.pumpWidget(
        _harness(_button(onPressed: () {}), brightness: brightness),
      );
      await tester.pumpAndSettle();
      final idle = tester.getSize(find.byType(BrandButton));
      await tester.pumpWidget(
        _harness(_button(busy: true, onPressed: () {}), brightness: brightness),
      );
      await tester.pump(const Duration(milliseconds: 200));
      expect(tester.getSize(find.byType(BrandButton)), idle);
      final style = tester
          .widget<FilledButton>(find.byType(FilledButton))
          .style!;
      final scheme = buildTheme(brightness).colorScheme;
      expect(
        style.backgroundColor!.resolve({WidgetState.disabled}),
        scheme.primary,
      );
      expect(
        style.foregroundColor!.resolve({WidgetState.disabled}),
        scheme.onPrimary,
      );
    }
  });

  testWidgets('reduced motion stops progress animation', (tester) async {
    final button = _button(busy: true, onPressed: () {});
    await tester.pumpWidget(_harness(button));
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    await tester.pumpWidget(_harness(button, reducedMotion: true));
    await tester.pumpAndSettle();
    expect(find.byType(CircularProgressIndicator), findsNothing);
    expect(find.byIcon(Icons.hourglass_empty), findsOneWidget);
    final style = tester.widget<FilledButton>(find.byType(FilledButton)).style!;
    expect(style.animationDuration, Duration.zero);
    expect(style.splashFactory, NoSplash.splashFactory);
    expect(tester.hasRunningAnimations, isFalse);
  });

  testWidgets(
    'pointer, Enter and Space activate; busy/disabled block repeats',
    (tester) async {
      var taps = 0;
      await tester.pumpWidget(_harness(_button(onPressed: () => taps++)));
      await tester.tap(find.text(_label));
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.pumpAndSettle();
      final style = tester
          .widget<FilledButton>(find.byType(FilledButton))
          .style!;
      expect(
        style.side!.resolve({WidgetState.focused})!.color,
        buildTheme(Brightness.light).colorScheme.onSurface,
      );
      await tester.sendKeyEvent(LogicalKeyboardKey.enter);
      await tester.sendKeyEvent(LogicalKeyboardKey.space);
      expect(taps, 3);
      for (final busy in [true, false]) {
        await tester.pumpWidget(
          _harness(_button(busy: busy, onPressed: busy ? () => taps++ : null)),
        );
        await tester.tap(find.text(_label));
        await tester.sendKeyEvent(LogicalKeyboardKey.enter);
        await tester.sendKeyEvent(LogicalKeyboardKey.space);
        expect(taps, 3);
      }
    },
  );

  test('tokens copy and interpolate spacing, shape and motion', () {
    const start = AppTokens.light;
    final end = start.copyWith(
      spacingSm: 12,
      spacingMd: 20,
      spacingLg: 32,
      radiusControl: 20,
      pressDuration: const Duration(milliseconds: 200),
    );
    final half = start.lerp(end, 0.5);
    expect(half.spacingSm, 10);
    expect(half.spacingMd, 18);
    expect(half.spacingLg, 28);
    expect(half.radiusControl, 15);
    expect(half.pressDuration, const Duration(milliseconds: 160));
    expect(start.copyWith().spacingMd, start.spacingMd);
    expect(start.lerp(end, 1).radiusControl, end.radiusControl);
    expect(start.lerp(null, 0.5), same(start));
  });
}
