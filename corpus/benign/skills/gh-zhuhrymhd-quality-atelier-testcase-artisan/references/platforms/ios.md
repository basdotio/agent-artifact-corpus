# Platform Pack: iOS

Loaded when the repo root has `*.xcodeproj`, `*.xcworkspace`, or `Package.swift`.

## Detection signals for core categories

Use these to decide whether a core category from `edge-case-checklist.md` actually
applies, and to phrase the test case in iOS-accurate terms.

| Core category | iOS-specific signal / phrasing |
|---|---|
| Permission denied | Check `Info.plist` for usage description keys (`NSCameraUsageDescription`, `NSLocationWhenInUseUsageDescription`, etc.). Steps should reference the system permission alert/sheet, not a custom in-app dialog. |
| Background / foreground | Triggered via the app switcher (background) or Home gesture/button. Reference `scenePhase` / `UIApplicationDelegate` lifecycle if visible in code. |
| App killed & relaunch | iOS can kill a backgrounded app at any time under memory pressure; this is not just "the user force-quit it". Steps should cover both cases if the docs distinguish them. |
| Rotation | Only relevant if the app doesn't lock orientation in its Info.plist / scene configuration. |
| Session / auth expiry | If Keychain is used for token storage, consider whether the token can be invalidated externally (e.g. revoked on another device) separately from simple expiry. |

## iOS-exclusive categories

These have no equivalent in the platform-neutral checklist and only apply on iOS.

| Category | Trigger condition |
|---|---|
| Dynamic Type | Feature displays user-facing text |
| VoiceOver custom actions | Screen has a custom gesture or a non-standard control (not a plain button/label) |
| Widget / Live Activity | Feature has a corresponding widget extension or Live Activity in the project |
| Push notification handling | Feature triggers or reacts to a push notification (check for `UNUserNotificationCenter` usage or an entitlement for push) |
| Low Power Mode | Feature does background work, location tracking, or animation-heavy UI that iOS may throttle |

Mark test cases from this section the same way as core checklist items:
`Source: inferred (checklist: <category name>)`.
