# Android stack guide: Kotlin, MVVM, Compose, coroutines, Hilt, Room

Follow the repository first: if it uses Java, XML views, or another architecture, keep using them and note any problems in the tech-debt list. Check current versions on Maven Central or Google's Maven repository before pinning anything new, and keep them in the version catalog.

## Architecture
- MVVM with unidirectional data flow. The ViewModel exposes one `StateFlow<FeatureUiState>` for screen state and handles user actions through plain functions (`onRetryClicked()`).
- One-off events (navigation, snackbars) go through a `Channel` or `SharedFlow`, or are modeled as state the UI clears.
- Repositories are the single source of truth for each kind of data and hide whether it came from the network or the database.
- Add a domain layer with use cases only when logic is shared between ViewModels or is complex enough to test on its own.

## Jetpack Compose
- Hoist state: composables receive state and callbacks, and stay stateless where possible. Screen-level composables collect from the ViewModel with `collectAsStateWithLifecycle()`.
- Pass stable, immutable parameters. Keep lambdas and expensive work out of recomposition paths.
- Provide previews for each screen state (loading, empty, error, content).
- Use the theme for colors, typography, and shapes; no hard-coded colors or sizes in screens.

## Coroutines and Flow
- Launch from `viewModelScope` or lifecycle-aware scopes. Never use `GlobalScope`.
- Inject dispatchers so tests can replace them. Do I/O on `Dispatchers.IO` inside repositories, not in the UI.
- Turn flows into UI state with `stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), initialValue)`.
- Catch exceptions at the repository or ViewModel boundary and map them to UI state.

## Dependency injection
- Hilt: `@HiltViewModel` ViewModels, constructor injection everywhere, and modules in a `di` package. Bind interfaces to implementations with `@Binds`.

## Data
- Room: DAOs return `Flow` for observed data and suspend functions for one-shot work. Export the schema and write a test for every migration.
- Retrofit with OkHttp: set connect, read, and write timeouts, add a logging interceptor only in debug builds, and use kotlinx.serialization or Moshi.
- DataStore instead of SharedPreferences for new key-value data.
- WorkManager for deferrable background work that must survive process death, with constraints and backoff.

## Firebase
- Wrap Firebase SDKs (Auth, Firestore, Messaging, Remote Config, Crashlytics) behind repositories or data sources so the rest of the app does not depend on them directly and tests can fake them.
- Keep Firestore security rules and indexes in the repository and deploy them deliberately (deployment skill).

## Build and release
- Gradle Kotlin DSL with a version catalog (gradle/libs.versions.toml).
- Respect the repository's minSdk, targetSdk, and compileSdk. Raising them is a decision for the user.
- Keep R8 enabled for release builds with tested keep rules.
- Signing configs read keystore paths and passwords from local.properties or CI secrets. Keystores never go into the repository.
- Use build types or flavors for environments, with base URLs in BuildConfig fields rather than in code.

## Quality commands
On Windows use `gradlew.bat`, elsewhere `./gradlew`:
- `gradlew lint`, plus `ktlintCheck` or `detekt` if configured
- `gradlew testDebugUnitTest`
- `gradlew connectedDebugAndroidTest` (needs a device or emulator)
- `gradlew assembleDebug`

## Accessibility
Content descriptions on meaningful icons and images, touch targets of at least 48dp, support for font scaling, and TalkBack checks for new screens (ui-design skill).
