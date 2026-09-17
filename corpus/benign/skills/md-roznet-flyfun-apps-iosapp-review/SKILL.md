---
name: iosapp-review
description: >
  Review iOS app code changes for FlyFun EuroAIP architecture compliance.
  Use when reviewing Swift code in app/FlyFunEuroAIP/, checking architecture patterns,
  or validating adherence to designs/IOS_APP_DESIGN.md. Verifies RZFlight model reuse,
  composed AppState pattern, repository abstraction, and platform-specific UI patterns.
allowed-tools: Read, Glob, Grep
---

# iOS App Architecture Review

Review code changes in `app/FlyFunEuroAIP/` for compliance with the architecture defined in `designs/IOS_APP_DESIGN.md`.

## Architecture Rules

1. **RZFlight Model Reuse (CRITICAL)**:
   - Use `RZFlight.Airport`, `RZFlight.Runway`, `RZFlight.Procedure`, `RZFlight.AIPEntry` directly
   - No duplicate models
   - Query through `KnownAirports`
   - Extend RZFlight library when functionality is missing

2. **Composed AppState**:
   - Single source of truth with domain objects
   - Domains: `AirportDomain`, `ChatDomain`, `NavigationDomain`, `SystemDomain`, `SettingsDomain`
   - Each domain ~200-400 lines
   - Cross-domain coordination via callbacks
   - Inject via `@Environment(\.appState)`

3. **No ViewModels**:
   - Domains replace ViewModels
   - No standalone `*ViewModel.swift` files
   - ViewCoordinators are structs with computed properties only

4. **Repository Pattern**:
   - `AirportRepositoryProtocol` defines unified API
   - `LocalAirportDataSource` uses `KnownAirports`
   - Repository returns `RZFlight.Airport` directly

5. **FilterConfig is Pure Data**:
   - Simple `Codable` struct
   - No `apply(to:db:)` method
   - Filtering logic lives in repository

6. **API Adapters**:
   - API response models are internal only
   - `APIAirportAdapter.toRZFlight()` converts immediately
   - Never expose `APIAirport` outside adapters

7. **Region-Based Map Loading**:
   - Use `airportsInRegion(boundingBox:filters:limit:)`
   - Debounce 300ms
   - Limit 500 markers
   - Prefetch with 1.3x padding

8. **File-Based Caching**:
   - Simple JSON files
   - No SwiftData
   - Cache in `Caches/` directory

9. **Modern Swift Only (iOS 18.0+/macOS 15.0+)**:
   - `@Observable` macro (no `ObservableObject`)
   - `@Environment` injection (no `@EnvironmentObject`)
   - `async/await` everywhere (no Combine)
   - Modern MapKit with `Map { }` builder

10. **DB is Canonical Source**:
    - Local SQLite is truth
    - API is read-only view
    - Full DB replacement for sync

## Red Flags

Flag these violations immediately:

- **Duplicate models**: Creating `Airport`, `Runway` in app instead of using RZFlight
- **ViewModel files**: Any `*ViewModel.swift` file
- **God-class AppState**: Single file >500 lines without domain composition
- **Direct SQL queries**: Using `FMDatabase` directly instead of `KnownAirports`
- **FilterConfig with DB logic**: `apply(to:db:)` method
- **Exposed API models**: `APIAirport` used outside adapter files
- **SwiftData usage**: Any `@Model` or SwiftData imports
- **ObservableObject**: Using instead of `@Observable`
- **Combine imports**: Using for state management
- **All airports loaded**: Loading all 10K+ airports at once for map

## Review Process

1. Analyze changed files in `app/FlyFunEuroAIP/`
2. Check imports - should see `import RZFlight`, no `import Combine`
3. Verify model usage - search for `RZFlight.Airport` vs local `Airport`
4. Check state management - domains composed in AppState?
5. Verify repository pattern - data access through repository?
6. Check UI patterns - adaptive layouts, environment injection?
7. Identify violations with file paths and line numbers
8. Suggest fixes with code examples

## Output Format

**APPROVED:**
- `file:line` - Explanation of why it's correct

**VIOLATION:**
- `file:line` - Description
- **Problem:** Why it violates architecture
- **Fix:** Suggested corrected implementation
- **Impact:** What breaks (performance, maintainability, etc.)

## Key Files

### Core Architecture
- `App/State/AppState.swift` - Composed domains?
- `App/State/Domains/*.swift` - Each domain ~200-400 lines?
- `App/Data/Repositories/AirportRepository.swift` - Returns RZFlight types?

### Model Usage
- `App/Models/*.swift` - Should be minimal (app-specific only)
- Any `struct Airport` - Should NOT exist (use RZFlight.Airport)

### UI Layer
- `UserInterface/Views/*.swift` - Uses `@Environment(\.appState)`?
- `UserInterface/Views/Map/*.swift` - Region-based loading?

## Approved Patterns

**RZFlight Model Usage:**
```swift
// GOOD
import RZFlight
let airport: Airport  // This is RZFlight.Airport

// BAD
struct AppAirport { let icao: String; let name: String }
```

**Composed AppState:**
```swift
// GOOD
@Observable @MainActor
final class AppState {
    let airports: AirportDomain
    let chat: ChatDomain
    let navigation: NavigationDomain
}
```

**Environment Injection:**
```swift
// GOOD
struct AirportMapView: View {
    @Environment(\.appState) private var state
}

// BAD
@StateObject private var viewModel = AirportMapViewModel()
```

**Region-Based Loading:**
```swift
// GOOD
func onRegionChange(_ region: MKCoordinateRegion) {
    regionUpdateTask?.cancel()
    regionUpdateTask = Task {
        try? await Task.sleep(for: .milliseconds(300))
        airports = try await repository.airportsInRegion(
            boundingBox: region.paddedBy(factor: 1.3).boundingBox,
            filters: filters, limit: 500
        )
    }
}

// BAD
airports = try await repository.allAirports()  // 10K+ airports!
```

## Reference

See `designs/IOS_APP_DESIGN.md` for full design details.
