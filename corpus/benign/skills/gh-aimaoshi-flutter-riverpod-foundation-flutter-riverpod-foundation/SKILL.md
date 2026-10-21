---
name: flutter-riverpod-foundation
description: >-
  Flutter Riverpod architecture conventions for dependency injection and state
  management, GoRouter shell navigation, AppBootstrap startup, typed storage,
  i18n, and Dio networking. Use when building or extending Flutter apps with
  Riverpod; not for GetX-based projects.
---

# Flutter Riverpod Foundation

Use the current repository as the source of truth. Preserve existing work and
do not copy legacy GetX business code into this project.

## Architecture

```text
lib/
├── app/                 # bootstrap, app shell, router, session
├── core/                # config, storage, network, errors, logging, utils
├── data/                # local/remote data sources and DTOs
├── domain/              # entities and repository contracts
├── features/            # feature UI and Notifiers
└── shared/              # reusable UI and i18n
```

- Use `flutter_riverpod` for dependency injection and state.
- Use `go_router` for navigation.
- Never add GetX, static service locators, or globally stored `BuildContext`.
- Keep server DTO uncertainty in `data/remote` and repositories; widgets do
  not consume raw server maps.
- `core` does not contain pages, feature controllers, or business models.
- `domain` is still empty; introduce it when a model is shared across features
  or needs a repository contract. A model used by a single feature lives next
  to that feature's provider.

## Startup and storage

- `AppBootstrap` initializes only startup dependencies and supplies Provider
  overrides. It does not own feature options, API calls, or mutable user data.
- `AppStorage` wraps `SharedPreferences` for small settings and flags only.
  Device and business collections need a feature-level local database.

## App shell and navigation

`SplashPage` sits at `/` and hands off to the main shell. The app must land on
the main interface, never on a standalone test page.

- The main interface is `features/main/main_shell_page.dart`, mounted with
  `StatefulShellRoute.indexedStack` so every tab keeps its own state and stack.
- One `StatefulShellBranch` per bottom-navigation tab, in tab order:
  `/home`, `/devices`, `/activity`, `/profile`.
- `MainShellPage` owns the `BottomNavigationBar` and switches tabs through
  `navigationShell.goBranch(index, initialLocation: index == currentIndex)`.
- Routes outside the shell (for example `/network-test`) push above the tab bar.
- Adding or reordering a tab means updating the branch list, the destinations,
  and the i18n labels in one change; both lists must stay in the same order.

## Feature layout

```text
features/<feature>/
├── <feature>_page.dart      # screen widget
└── <feature>_provider.dart  # feature model + Riverpod providers
```

- Keep feature data behind a provider even while it is static, so it can become
  asynchronous later without changing how the page reads it.
- Unimplemented tabs render `FeaturePlaceholder` with an i18n title and message
  instead of hand-rolled empty states.
- Feature-agnostic widgets live in `shared/ui/widgets/`.

## Assets

- Static images live under `assets/images/` and are registered in `pubspec.yaml`
  by folder.
- Reference them through the constants in `lib/assets.dart`; never inline an
  asset path inside a widget.
- Keep shipped assets small: downscale large source art for in-app use and keep
  the original file beside it rather than bundling full-resolution artwork.

## Internationalization

Place locale keys, translation maps, and `LocaleController` in `shared/i18n`.

- Every visible string gets a `LocaleKeys` entry and values in every locale.
- Widgets read strings through `context.tr(LocaleKeys.someKey)`.
- Key names stay snake_case and values keep the `demo_txt_` prefix.
- Nothing detects missing translations, so add each new key to all locale files
  in `shared/i18n/locales/` in the same change.
- The locale controller owns selection and persistence.
- Language option lists belong to i18n configuration, not pages or bootstrap.

## Networking

Use this flow:

```text
Widget → Notifier → Repository → RemoteDataSource → ApiClient → Dio
```

- `dioProvider` owns the Dio lifecycle; `ApiClient` never creates a global Dio.
- Default legacy request format is `Headers.formUrlEncodedContentType`; default
  response format is `ResponseType.json`.
- Use `postForm` for legacy endpoints and `postJson` only for explicit JSON
  contracts.
- `ApiResponse` supports both `{resultCode, data}` envelopes and root-level
  result objects.
- Do not hard-code, persist, or log test credentials, cookies, or tokens.
- Keep real service hostnames out of the repository. `network_config.dart`
  stores placeholder base URLs per environment; supply the real address when
  integrating instead of committing it.

### Logging

For each completed request, print exactly one log frame:

```text
请求url: ...
参数: ...
返回结果: ...
```

For failures, use the same frame with the exception as the result. Redact
passwords, `logincookie`, and all token fields.

## Layout

Use `context.layout`, not a global context singleton. Preserve these legacy
compatibility helpers when required:

```dart
context.layout.getScreenWidth();
context.layout.getScreenHeight();
context.layout.getAppBarHeight();
context.layout.getStatusBarHeight();
```

## Change checklist

1. Inspect the closest existing feature and keep layers separated.
2. Add or update focused tests for new parsing, storage, or UI behavior.
3. Add every new visible string to all locale files.
4. When a tab changes, update the shell destinations, the router branches, and
   the i18n labels together.
5. Run `dart format` only on changed Dart files.
6. Run `flutter test`.
7. Run `flutter analyze`; distinguish new errors from pre-existing lint info.
8. For Android-impacting changes, run `flutter build apk --debug`.
