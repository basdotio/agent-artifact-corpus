# Platform Pack: Android

Loaded when the repo root has `build.gradle`, `build.gradle.kts`, or
`AndroidManifest.xml`.

## Detection signals for core categories

Use these to decide whether a core category from `edge-case-checklist.md` actually
applies, and to phrase the test case in Android-accurate terms.

| Core category | Android-specific signal / phrasing |
|---|---|
| Permission denied | Check `AndroidManifest.xml` for `<uses-permission>` tags and runtime requests via `ActivityCompat.requestPermissions`/`registerForActivityResult`. Android has a distinct "deny + don't ask again" state; write it as a separate test case, not folded into a single generic denial case. |
| Background / foreground | Triggered via Home button, recent-apps switcher, or an app switch. Reference `Activity`/`Fragment`/`ViewModel` lifecycle callbacks (`onPause`, `onStop`, `onResume`) if visible in code. |
| App killed & relaunch | Take this more seriously than on iOS: Android's process death is more aggressive (low-memory devices, background limits), and a plain rotation can also destroy and recreate the hosting `Activity` unless configuration changes are handled explicitly. Write separate test cases for "system kills for memory" vs "configuration change recreates the Activity" - they exercise different code paths (`onSaveInstanceState`/`ViewModel` survival vs full re-init). |
| Rotation | Higher priority here than on iOS: default behavior is full `Activity` recreation unless `android:configChanges` is declared in the manifest. Treat as relevant for every screen unless `android:screenOrientation` locks it. |
| Session / auth expiry | If tokens are stored via Android Keystore or `EncryptedSharedPreferences`, consider whether the token can be invalidated externally (e.g. revoked on another device) separately from simple expiry. |

## Android-exclusive categories

These have no equivalent in the platform-neutral checklist and only apply on
Android.

| Category | Trigger condition |
|---|---|
| System back button / predictive back gesture | Screen overrides default back behavior (`onBackPressed`, `OnBackPressedCallback`, or a custom `NavController` back stack) |
| Battery optimization / Doze mode killing background work | Feature relies on background work (`WorkManager` job, foreground service) that OEM battery optimizers (Samsung, Xiaomi, etc.) may kill more aggressively than stock behavior |
| Deep link / intent handling | Feature is entered via an `intent-filter` (deep link, share sheet, notification tap) |
| OEM / API level fragmentation | Feature uses an API that behaves differently across manufacturers, or the app's `minSdkVersion` range spans several Android versions |
| Notification channel behavior | Feature sends notifications (channel importance settings, and the runtime notification permission on API 33+) |
| Multi-window / split-screen / resizable window | Feature's UI must remain usable when the window is resized or split |
| ANR (main thread blocked) | Feature does work on the main thread that could take longer than a few seconds (large parsing, synchronous I/O) |

Mark test cases from this section the same way as core checklist items:
`Source: inferred (checklist: <category name>)`.
