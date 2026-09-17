---
name: build-card-widget-skill
description: Enforces strict standards for building Flutter Card widgets using the shared styles resources directory, theme-based colors, clean helper-based composition, and explicit usage verification.
---

# Build Card Widget Skill

This skill defines **mandatory rules and patterns** for building Card widgets in Flutter.

Its goals are:
- UI consistency
- Theme safety
- Clean, readable code
- Clear card structure for humans
- Verifiable skill usage

---

## When to use this skill

- Use this skill **whenever building, updating, or refactoring any Card widget**.
- Applies to all card types (info cards, action cards, list cards, switch cards, etc.).

---

## How to use it

### 1. Card as the Main Container (Mandatory)

- Always use Flutter’s `Card` widget as the **main and outer container**.
- The Card acts as a **rubber / structural widget** that wraps all content.

Rules:
- ❌ Do not use `Container`, `DecoratedBox`, or similar widgets instead of `Card`.
- ❌ Do not customize card appearance directly:
  - No colors
  - No borders
  - No border radius overrides
  - No elevation or shadows

The card’s appearance must come **only** from the theme.

---

### 2. Clean Structure & Readability

- Card widgets must follow a **clear and readable structure**.
- Use **helper methods** to split the card into logical sections.

Recommended pattern:
- One main widget (class or method)
- Private helper methods for:
  - Header / title
  - Body / content
  - Footer / actions (if needed)

Rules:
- ❌ No large, unreadable build methods
- ❌ No deeply nested widget trees without separation
- ✅ A human should understand the card layout at a glance

---

### 3. Styling & Layout Resources (Mandatory)

All widget styling and layout decisions must come from the **shared styles resources directory**:

```
lib/core/resources/styles/
```

The agent must **explore and reuse** the available resources instead of creating new styles.

#### Allowed & Relevant Style Files

Only the following files are relevant when creating and styling widgets:

- `colors_resources.dart`  
  → Shared color definitions (when not using theme directly)

- `font_styles_manager.dart`  
  → Text styles and typography

- `sizes_resources.dart`  
  → Sizes, icon sizes, and layout constants

- `spaces_resources.dart` / `spacing_resources.dart`  
  → Padding, margin, and spacing utilities

- `border_radius_resources.dart`  
  → Standardized border radii (when applicable)

- `shadows_resources.dart`  
  → Shared shadow definitions (not for Cards unless explicitly allowed)

#### Rules

- ❌ Do not hardcode colors, sizes, spacing, or text styles
- ❌ Do not create ad-hoc styling values
- ✅ Always search the styles directory first
- ✅ Reuse existing resources even if they are not a perfect match

---

### 4. Colors

- ❌ Never hardcode colors.
- Prefer theme colors:
  - Titles → `Theme.of(context).colorScheme.onSurface`
  - Subtitles / secondary text → `Theme.of(context).colorScheme.onSurfaceVariant`

If a non-theme color is required, it **must** come from `colors_resources.dart`.

---

## Skill Enforcement: Usage Marker (Mandatory)

To verify that this skill was used, the agent **must add a specific comment** at the start of every card widget implementation.

### Required Comment (Exact)

```dart
// build-card-widget-skill: applied
```

### Placement Rules

- The comment must appear **directly above**:
  - The Card widget class, **or**
  - The method/function that returns a `Card`

If the comment is missing or altered, the skill is considered **NOT used**.

---

## Mental Model (Enforced)

- Card = structure & layout
- Theme = visual authority
- Styles directory = single source of truth
- Helpers = readability
- Comment = verification

Any violation makes the card implementation **invalid** and requires refactoring.
