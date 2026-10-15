# Platform Pack: Flutter

Loaded when the repo root has a `pubspec.yaml` that contains `flutter:`. A Flutter
project also contains `ios/` and `android/` folders; do not treat it as a native iOS
or Android project. One Flutter codebase ships to both iOS and Android, so unless a
test case is specifically about one platform's native behavior, write it once and
mark it as covering both.

## Detection signals for core categories

| Core category | Flutter-specific signal / phrasing |
|---|---|
| Permission denied | Check `pubspec.yaml` for `permission_handler` and the native manifests it still relies on (`Info.plist` keys, `AndroidManifest.xml` `<uses-permission>`). The permission dialog is still the native OS dialog on each platform. |
| Background / foreground | Reference `AppLifecycleState` (`resumed`, `paused`, `inactive`, `detached`) from `WidgetsBindingObserver`. |
| App killed & relaunch | State held in memory is lost; check restore from `SharedPreferences`, secure storage, or a local DB. On Android the process is killed more aggressively (see the Android pack). |
| Rotation | A rebuild, not a full restart, but check that state survives it and that layout adapts (`LayoutBuilder`, `MediaQuery`). |
| Empty / loading state | Flutter apps are `Future`/`Stream` heavy: check the loading, empty, error, and data states of every `FutureBuilder`/`StreamBuilder`. |
| Boundary / invalid input | Form fields use `TextFormField` validators; check they run and block subm/save. |
| Network failure / server error | `http`/`dio` calls: check timeout, offline, and non-2xx handling surface a user-visible state. |

## Flutter-specific categories

| Category | Trigger condition |
|---|---|
| Widget state across rebuild | A `StatefulWidget` or a state-management solution (Provider, Riverpod, Bloc) holds state that must survive a rebuild or navigation |
| Platform channel behavior | The feature uses a `MethodChannel`/plugin to call native code, so it can differ between iOS and Android |
| Per-platform divergence | The feature uses `Platform.isIOS`/`isAndroid` or `Theme.of(context).platform` branches, so each branch needs its own case |
| Navigation / deep link | The feature uses named routes, `go_router`, or handles an incoming deep link |
| Text scaling / accessibility | The feature shows text; check it survives large `textScaleFactor` and exposes semantics labels |

## Level test note

Flutter has three native test levels. Map them onto the shared taxonomy so the core
list doesn't grow:

- `flutter_test` unit test (pure Dart, no widgets) → `unit`
- `flutter_test` widget test (one widget/screen, no device) → `ui-single-screen`
- `integration_test` (full app on a device/emulator) → `e2e-multi-screen`

Snapshot/golden tests (`matchesGoldenFile`) → `snapshot`.

Mark test cases from the categories above the same way as core checklist items:
`Source: inferred (checklist: <category name>)`.
