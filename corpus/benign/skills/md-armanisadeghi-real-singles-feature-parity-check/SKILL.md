---
name: feature-parity-check
description: Comprehensive cross-platform feature verification and synchronization. Use after completing a feature to ensure identical functionality across Web Desktop, Web Mobile, iOS, and Android with native implementations. Audits for missing features, API consistency, and sister functionalities that need updating.
---

# Feature Parity Check

Systematic verification that a feature is complete, consistent, and native across all platforms.

## When to Use

- After completing a feature implementation
- When user says "verify parity", "check all platforms", "sync feature", or "feature-parity-check"
- Before marking any multi-platform feature as done

---

## Verification Workflow

Copy this checklist and update as you progress:

```
Feature: [NAME]
Status: In Progress

Phase 1 - Discovery
- [ ] Web implementation reviewed
- [ ] Mobile implementation reviewed
- [ ] All functionality catalogued

Phase 2 - Native Verification
- [ ] Web Desktop: Proper desktop patterns
- [ ] Web Mobile: Touch-friendly, responsive
- [ ] iOS: Native components (SF Symbols, native sheets, haptics)
- [ ] Android: Native components (Material Icons, native patterns)

Phase 3 - Functionality Parity
- [ ] Feature matrix completed
- [ ] All gaps identified and fixed

Phase 4 - API Consistency
- [ ] Single API endpoint for each operation
- [ ] No local business logic duplication
- [ ] Constants synced (mobile/constants/options.ts ↔ web/src/types/index.ts)

Phase 5 - Sister Functionality Audit
- [ ] Related UI touchpoints identified
- [ ] All related views updated
- [ ] Cross-references working
```

---

## Phase 1: Discovery

**Goal:** Understand EVERYTHING each platform does before making changes. Never lose functionality.

### Step 1.1: Identify All Implementation Files

Search for the feature across both codebases:

```bash
# Web implementation
rg -l "feature-keyword" web/src/

# Mobile implementation  
rg -l "feature-keyword" mobile/

# API routes
rg -l "feature-keyword" web/src/app/api/
```

### Step 1.2: Read and Document Each Implementation

For each file found, document:
- What actions/operations it supports
- What data it displays
- What user interactions it handles
- Any platform-specific behaviors

### Step 1.3: Create Functionality Inventory

```markdown
## [Feature Name] Functionality Inventory

### Operations Found
| Operation | Web | Mobile | API Endpoint |
|-----------|-----|--------|--------------|
| Create X  | ✓   | ✓      | POST /api/x  |
| Edit X    | ✓   | ✗      | PUT /api/x   |
| Delete X  | ✗   | ✓      | DELETE /api/x|

### Data Displayed
| Data Point | Web | Mobile |
|------------|-----|--------|
| Title      | ✓   | ✓      |
| Thumbnail  | ✓   | ✗      |

### Missing in Web: [list]
### Missing in Mobile: [list]
```

**CRITICAL:** If one platform has functionality the others don't, ADD it to the others—never remove it.

---

## Phase 2: Native Verification

**Goal:** Each platform must feel native, not like a cross-platform wrapper.

### 2.1 Web Desktop Checklist

- [ ] Hover states on interactive elements
- [ ] Keyboard navigation support
- [ ] Appropriate use of modals/dialogs (not mobile sheets)
- [ ] Desktop-appropriate spacing and sizing
- [ ] Mouse-optimized click targets

### 2.2 Web Mobile Checklist

- [ ] Touch targets minimum 44x44px
- [ ] No hover-dependent functionality
- [ ] Responsive layout (no horizontal scroll)
- [ ] Input fields 16px+ font (prevents iOS zoom)
- [ ] Uses `h-dvh` not `h-screen`
- [ ] Bottom elements have `pb-safe`
- [ ] Swipe gestures where appropriate

### 2.3 iOS Checklist

- [ ] SF Symbols for icons (via `expo-symbols`)
- [ ] Native sheets (`@gorhom/bottom-sheet`)
- [ ] Native navigation patterns
- [ ] Haptic feedback on important actions
- [ ] System colors respected
- [ ] Safe area handling (no manual padding fighting system)
- [ ] Native pickers/date selectors where appropriate

### 2.4 Android Checklist

- [ ] Material Icons (or properly-sized PNGs at 24dp)
- [ ] Material Design patterns followed
- [ ] Native back button behavior
- [ ] Appropriate ripple effects
- [ ] System navigation bar handling
- [ ] Native components where available

### Red Flags (Fix Immediately)

- ❌ Custom JS-drawn bottom tabs (use `expo-router/unstable-native-tabs`)
- ❌ Emoji as icons
- ❌ Heavy custom styling overriding platform defaults
- ❌ JS-based animations instead of `react-native-reanimated`
- ❌ Manual safe area padding on native components

---

## Phase 3: Functionality Parity

**Goal:** Identical capabilities across all platforms.

### 3.1 Build Feature Matrix

| Capability | Web Desktop | Web Mobile | iOS | Android | Notes |
|------------|-------------|------------|-----|---------|-------|
| View list  | ✓ | ✓ | ✓ | ✓ | |
| Create new | ✓ | ✓ | ✗ | ✗ | NEEDS FIX |
| Edit       | ✓ | ✓ | ✓ | ✓ | |
| Delete     | ✓ | ✗ | ✓ | ✓ | NEEDS FIX |
| Filter     | ✓ | ✓ | ✗ | ✗ | NEEDS FIX |

### 3.2 Fix All Gaps

For each gap:
1. Identify the reference implementation (usually web)
2. Implement the missing functionality
3. Ensure it uses the same API endpoint
4. Verify the UI is native to that platform

### 3.3 Edge Cases to Check

- Empty states (no data)
- Loading states
- Error states
- Offline behavior
- Permission denied states
- Data validation feedback

---

## Phase 4: API Consistency

**Goal:** All platforms use the same backend logic.

### 4.1 Verify Single Source of Truth

For each operation in the feature:

```
Operation: [e.g., "Update profile photo"]

✓ CORRECT: All platforms call → PUT /api/users/me/photo
✗ WRONG: Mobile has local logic, Web calls API
```

### 4.2 Check for Logic Leakage

Search for business logic that should be server-side:

```bash
# Check mobile for embedded logic
rg -A5 "supabase\.(from|rpc)" mobile/
rg "\.update\(|\.insert\(|\.delete\(" mobile/

# These should be API calls, not direct DB operations
```

**Rule:** Mobile should ONLY call `web/src/app/api/` endpoints via `mobile/lib/api.ts`.

### 4.3 Constants Sync

Compare and sync:
- `mobile/constants/options.ts`
- `web/src/types/index.ts`

Any shared constants (dropdown options, enums, validation rules) must be identical.

---

## Phase 5: Sister Functionality Audit

**Goal:** Find and update all related UI that touches this feature.

### 5.1 Identify Related Touchpoints

Search for references to the feature's:
- Data types
- API endpoints
- State/store keys
- Component names

```bash
# Find all files referencing this data type
rg "EventType|Event\[|events\." --type ts --type tsx

# Find all components that might display this data
rg -l "event" web/src/components/
rg -l "event" mobile/components/
```

### 5.2 Common Sister Functionalities

| If you changed... | Also check... |
|-------------------|---------------|
| Events | Calendar views, notifications, home feed, search results |
| User profiles | Match cards, chat headers, review displays |
| Photos/Gallery | Profile previews, thumbnails, chat image sends |
| Settings/Preferences | Any feature that reads those preferences |
| Notifications | Badge counts, notification lists, push handlers |

### 5.3 Update All Related Views

For each related view found:
1. Verify it reflects the new/changed functionality
2. Update if needed
3. Apply same parity check (all 4 platforms)

---

## Completion Criteria

Before marking complete, verify ALL of these:

```
FINAL CHECKLIST

Functionality
- [ ] All operations work on Web Desktop
- [ ] All operations work on Web Mobile  
- [ ] All operations work on iOS
- [ ] All operations work on Android
- [ ] No functionality was lost from any platform

Native Feel
- [ ] Web uses appropriate desktop/mobile patterns
- [ ] iOS uses SF Symbols and native components
- [ ] Android uses Material Icons and native patterns
- [ ] No platform feels like a wrapped web app

API Consistency  
- [ ] All platforms call the same API endpoints
- [ ] No business logic in client code
- [ ] Constants are synced

Sister Features
- [ ] All related UI touchpoints identified
- [ ] All related views updated
- [ ] No orphaned references to old implementations
```

---

## Quick Reference: Project Locations

| Type | Path |
|------|------|
| Web pages | `web/src/app/` |
| Web components | `web/src/components/` |
| Web API routes | `web/src/app/api/` |
| Web services | `web/src/lib/services/` |
| Mobile screens | `mobile/app/` |
| Mobile components | `mobile/components/` |
| Mobile API client | `mobile/lib/api.ts` |
| Mobile constants | `mobile/constants/options.ts` |
| Web types/constants | `web/src/types/index.ts` |

---

## Reporting Format

After completing verification, provide summary:

```markdown
## Feature Parity Report: [Feature Name]

### Status: ✓ VERIFIED / ⚠️ ISSUES FOUND

### Changes Made
- [List all fixes applied]

### Platform Status
| Platform | Status | Notes |
|----------|--------|-------|
| Web Desktop | ✓ | |
| Web Mobile | ✓ | |
| iOS | ✓ | |
| Android | ✓ | |

### API Verification
- Endpoints used: [list]
- Business logic location: [path]

### Sister Features Updated
- [List any related features that were also updated]

### Remaining Issues (if any)
- [List anything that couldn't be fixed automatically]
```
