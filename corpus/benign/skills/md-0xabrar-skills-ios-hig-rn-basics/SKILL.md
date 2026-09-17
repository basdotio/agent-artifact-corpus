---
name: ios-hig-rn-basics
description: Core iOS HIG guidance and design rules. Use when giving iOS UI/UX advice on layout, typography, color, spacing, controls, and iconography (not Expo Router implementation).
---

# iOS HIG + RN/Expo Basics

## Overview
Provide practical iOS UX/UI guidance and map each recommendation to React Native or Expo implementation hints.

## Quick Start
- Ask for screen type, primary action, and target devices (iPhone, iPad, or both).
- Apply the baseline checks in `references/checklist.md`.
- Output prioritized recommendations with severity and a brief RN/Expo mapping note.

## Core Rules

### Layout and Safe Areas
- Keep the root scrollable when content may exceed the viewport.
- Let the system handle safe area insets instead of hard-coding top/bottom padding.
- Keep content aligned to a clear grid with consistent spacing rhythm.

### Touch Targets and Controls
- Ensure all tap targets are at least 44x44pt.
- Prefer native controls over custom replicas.
- Make the primary action obvious and reachable with one thumb.

### Typography
- Prefer system text styles and allow Dynamic Type scaling.
- Keep line lengths short enough for scanability.
- Use weight and size to express hierarchy, not color alone.

### Color and Contrast
- Prefer semantic system colors for text and backgrounds.
- Maintain contrast for normal and large text.
- Do not rely on color alone to encode status or state.

### Iconography
- Prefer SF Symbols for familiar system metaphors.
- Pair icon-only buttons with clear labels or accessibility text.

## RN/Expo Mapping
- Safe areas and scrolling: `ScrollView` or `FlatList` with `contentInsetAdjustmentBehavior="automatic"`.
- System colors: `PlatformColor` or `DynamicColorIOS`.
- Icons: `expo-symbols` for SF Symbols.
- Haptics: `expo-haptics` for confirmation feedback.

## Output Format
- Provide a short list of issues and improvements.
- Include severity tags: High, Medium, Low.
- Add a brief RN/Expo implementation hint for each recommendation.

## References
- `references/checklist.md`
- `references/component-map.md`
