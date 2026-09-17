---
name: flutter-expert
description: "Expert-level Flutter mobile development assistant for building production-grade cross-platform apps. Use this skill whenever the user mentions Flutter, Dart, mobile app development, cross-platform apps, widgets, BLoC, Riverpod, Provider, GoRouter, platform channels, or any iOS/Android app work — even if they just say 'build me an app' or 'mobile app'. Covers architecture decisions, state management selection, widget composition, native integrations, animations, testing, performance optimization, and deployment. Always use this skill for any Flutter-adjacent task including debugging build errors, upgrading dependencies, fixing platform-specific issues, or reviewing Flutter code."
---

# Flutter Expert — Claude Code CLI Skill

Build production-grade Flutter applications through systematic, opinionated decision-making. This skill encodes real-world patterns from shipping Flutter apps — not textbook theory.

---

## Phase 0: Orientation (Run First, Every Time)

Before writing ANY Flutter code, run these diagnostics:

```bash
# 1. Check Flutter environment
flutter doctor -v

# 2. Detect project state
if [ -f "pubspec.yaml" ]; then
  echo "=== EXISTING PROJECT ==="
  cat pubspec.yaml | head -40
  flutter pub deps --style=compact 2>/dev/null | head -30
  find lib -name "*.dart" | head -20
  echo "--- Architecture detection ---"
  ls -la lib/
  ls -la lib/src/ 2>/dev/null || echo "No lib/src/"
  ls -la lib/features/ 2>/dev/null || echo "No feature dirs"
  ls -la lib/core/ 2>/dev/null || echo "No core dir"
else
  echo "=== NO PROJECT — will scaffold ==="
fi
```

Interpret results before proceeding. Identify: Flutter version, null safety status, existing architecture, state management in use, target platforms.

---

## Phase 1: Architecture Decision Tree

Use this decision tree to select architecture. Don't ask the user to pick — recommend based on project scope.

**Project Sizing:**
- **Small** (1-5 screens, no auth, simple state) → Minimal structure + Provider/Riverpod
- **Medium** (5-15 screens, auth, API, local storage) → Feature-first + Riverpod 2.0 + GoRouter
- **Large** (15+ screens, complex flows, offline, multi-team) → Clean Architecture + BLoC + auto_route

**Read `references/architecture-patterns.md` for full scaffold commands and templates per size.**

### Scaffold Command (Medium — Most Common)

```bash
# Generate feature-first structure
mkdir -p lib/{core/{constants,errors,network,theme,utils,widgets},features,routing}
mkdir -p lib/core/network

# Create the app entry point
cat > lib/main.dart << 'DART'
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'routing/app_router.dart';
import 'core/theme/app_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: App()));
}

class App extends ConsumerWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: 'App',
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      routerConfig: router,
      debugShowCheckedModeBanner: false,
    );
  }
}
DART
```

### Feature Module Template

Every feature gets this structure — no exceptions:

```
lib/features/<feature_name>/
├── data/
│   ├── datasources/       # Remote + local data sources
│   ├── models/            # Data transfer objects (fromJson/toJson)
│   └── repositories/      # Repository implementations
├── domain/
│   ├── entities/          # Pure Dart classes (no deps)
│   ├── repositories/      # Abstract repository interfaces
│   └── usecases/          # Single-responsibility business logic
└── presentation/
    ├── providers/         # Riverpod providers (or BLoC cubits)
    ├── screens/           # Full-page widgets
    └── widgets/           # Feature-specific reusable widgets
```

Generate a feature with:
```bash
FEATURE="auth"
for dir in data/datasources data/models data/repositories domain/entities domain/repositories domain/usecases presentation/providers presentation/screens presentation/widgets; do
  mkdir -p "lib/features/$FEATURE/$dir"
done
```

---

## Phase 2: State Management Selection

**Decision matrix — use this, don't deliberate:**

| Signal in project | Choose | Why |
|---|---|---|
| Simple form/toggle state in one widget | `setState` | Overhead of provider is wasted |
| Shared state across 2-5 widgets | `Riverpod 2.0` | Compile-safe, testable, minimal boilerplate |
| Complex async flows (auth, pagination, real-time) | `Riverpod 2.0 + AsyncNotifier` | Built-in loading/error states |
| Event-driven architecture, strict separation | `flutter_bloc` | When team mandates BLoC or project already uses it |
| Legacy project already using Provider | `Provider` | Don't migrate unless rewriting |

**Read `references/state-management.md` for implementation templates for each approach.**

### Riverpod Quick-Start (Default Choice)

```yaml
# pubspec.yaml additions
dependencies:
  flutter_riverpod: ^2.5.1
  riverpod_annotation: ^2.3.5

dev_dependencies:
  riverpod_generator: ^2.4.0
  build_runner: ^2.4.8
  riverpod_lint: ^2.3.10
```

```bash
# After adding deps
flutter pub get
dart run build_runner build --delete-conflicting-outputs
```

---

## Phase 3: Implementation Workflow

Follow this sequence for every feature. Do NOT skip steps.

### Step 1: Domain Layer (entities + repository interface)
Write pure Dart first. No Flutter imports. No dependencies. This is your contract.

### Step 2: Data Layer (models + datasources + repository impl)
Implement the contract. Handle serialization, network errors, caching.

### Step 3: Presentation Layer (providers/cubits → screens → widgets)
Wire state to UI. Every screen gets a dedicated provider/cubit.

### Step 4: Routing Integration
Register the screen in the router. Handle deep links and guards.

### Step 5: Tests
Write tests in this order: unit (domain) → unit (data) → widget → integration.

**Read `references/code-templates.md` for copy-paste templates for each step.**

---

## Phase 4: Critical Patterns (Enforce Always)

### Error Handling — Never Catch Generic Exceptions

```dart
// ❌ NEVER
try { await api.fetch(); } catch (e) { print(e); }

// ✅ ALWAYS — typed failure handling
sealed class Failure {
  const Failure(this.message);
  final String message;
}
class NetworkFailure extends Failure { const NetworkFailure(super.message); }
class CacheFailure extends Failure { const CacheFailure(super.message); }
class ServerFailure extends Failure { const ServerFailure(super.message); }
```

### Network Layer — Use Dio with Interceptors

```yaml
dependencies:
  dio: ^5.4.1
  connectivity_plus: ^6.0.3
```

```dart
// lib/core/network/api_client.dart
import 'package:dio/dio.dart';

class ApiClient {
  late final Dio _dio;

  ApiClient({required String baseUrl, String? token}) {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 15),
      headers: {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      },
    ));
    _dio.interceptors.addAll([
      LogInterceptor(requestBody: true, responseBody: true),
      _retryInterceptor(),
    ]);
  }

  Interceptor _retryInterceptor() => InterceptorsWrapper(
    onError: (error, handler) async {
      if (error.response?.statusCode == 401) {
        // Token refresh logic here
      }
      handler.next(error);
    },
  );

  Future<Response<T>> get<T>(String path, {Map<String, dynamic>? params}) =>
      _dio.get<T>(path, queryParameters: params);

  Future<Response<T>> post<T>(String path, {dynamic data}) =>
      _dio.post<T>(path, data: data);
}
```

### Navigation — GoRouter with Guards

```yaml
dependencies:
  go_router: ^14.2.0
```

**Read `references/code-templates.md` § Navigation for the full router setup with auth guards, shell routes, and deep linking.**

### Performance Rules (Non-Negotiable)

1. **const everything** — Every stateless widget constructor must be `const`
2. **RepaintBoundary** — Wrap animated/frequently-rebuilding widgets
3. **ListView.builder** — Never use `ListView(children: [...])` for dynamic lists
4. **Image.network** must use `cacheWidth`/`cacheHeight` or `cached_network_image`
5. **Avoid `BuildContext` across async gaps** — Check `mounted` before using context after await
6. **Keys** — Use `ValueKey` on list items that reorder; `GlobalKey` only when absolutely necessary
7. **Isolates** — JSON parsing > 1MB or image processing → `compute()` or `Isolate.run()`

---

## Phase 5: Quality Gates

Run these checks before marking ANY task complete:

```bash
# 1. Static analysis (must pass with zero issues)
dart analyze --fatal-infos

# 2. Format check
dart format --set-exit-if-changed .

# 3. Tests
flutter test --coverage

# 4. Build verification (both platforms)
flutter build apk --debug 2>&1 | tail -5
flutter build ios --debug --no-codesign 2>&1 | tail -5  # macOS only

# 5. Unused deps / code
dart pub deps --style=compact
```

**Read `references/quality-gates.md` for the full CI pipeline config, custom lint rules, and pre-commit hooks.**

---

## Phase 6: Platform-Specific Handling

### iOS Gotchas
- `Info.plist` permissions — ALWAYS add `NSCameraUsageDescription`, `NSPhotoLibraryUsageDescription`, etc. with human-readable strings
- `Podfile` minimum target: `platform :ios, '13.0'` (Flutter 3.22+)
- CocoaPods issues: `cd ios && pod deintegrate && pod install --repo-update`

### Android Gotchas
- `minSdkVersion 23` minimum for most modern packages
- `compileSdkVersion 34` for latest Material You
- Namespace in `android/app/build.gradle`: `namespace "com.example.app"`
- Multidex: enable if method count > 64K
- ProGuard rules for release builds with `shrinkResources true`

### Common Build Fixes
```bash
# Nuclear option — clean everything
flutter clean && rm -rf pubspec.lock .dart_tool build ios/Pods ios/Podfile.lock
flutter pub get
cd ios && pod install --repo-update && cd ..
```

---

## Debugging Quick-Reference

| Symptom | Fix |
|---|---|
| `setState() called after dispose()` | Check `mounted` before `setState` |
| Widget rebuild storms | Add `const`, check provider scoping |
| "Looking up deactivated widget's ancestor" | Don't use context after async without mount check |
| Jank on scroll | Profile with `flutter run --profile`, add RepaintBoundary |
| "Connection refused" on Android emulator | Use `10.0.2.2` not `localhost` |
| iOS build "module not found" | `cd ios && pod install --repo-update` |
| Gradle build failure | Check `android/gradle/wrapper/gradle-wrapper.properties` version |
| "type 'Null' is not a subtype" | Null safety violation — trace the nullable chain |

---

## Package Recommendations (Battle-Tested)

**Core stack (install by default for medium+ projects):**
```yaml
dependencies:
  flutter_riverpod: ^2.5.1      # State management
  go_router: ^14.2.0            # Navigation
  dio: ^5.4.1                   # HTTP client
  freezed_annotation: ^2.4.1    # Immutable models
  json_annotation: ^4.9.0       # JSON serialization
  cached_network_image: ^3.3.1  # Image caching
  flutter_secure_storage: ^9.2.2 # Secure local storage
  intl: ^0.19.0                 # i18n/l10n

dev_dependencies:
  freezed: ^2.5.2
  json_serializable: ^6.8.0
  build_runner: ^2.4.8
  riverpod_generator: ^2.4.0
  flutter_lints: ^4.0.0
  mocktail: ^1.0.3
```

**Read `references/code-templates.md` § Freezed Models for the model generation workflow.**

---

## Reference Files

Read these as needed — they contain full implementation code:

| File | When to read |
|---|---|
| `references/architecture-patterns.md` | Scaffolding new projects or restructuring existing ones |
| `references/state-management.md` | Implementing providers, BLoCs, or migrating state approach |
| `references/code-templates.md` | Need copy-paste templates for models, screens, tests, routing |
| `references/quality-gates.md` | Setting up CI/CD, linting, pre-commit hooks, release pipeline |
