---
name: localStorage-patterns
description: Standardized patterns for localStorage utilities, including key naming conventions, error handling, and testing strategies. Use when creating or modifying localStorage utilities, when localStorage key mismatches occur, or when testing storage functionality. This codebase uses camelCase keys (e.g., pixelGameSettings, not pixel-game-settings).
---

# localStorage Patterns

## Overview

Standardize localStorage utility creation with consistent key naming, error handling, and testing patterns.

## Key Naming Conventions

**This codebase uses camelCase**: `pixelGameSettings` (not `pixel-game-settings`)

**Before using localStorage**:
1. Read the storage utility file to find the correct key name
2. Check for constants file with exported storage keys
3. Verify key format matches codebase (camelCase)
4. Don't assume naming conventions - check actual implementation

See `references/key-naming.md` for detailed naming patterns.

## Error Handling Pattern

Always include error handling:

1. **Check localStorage availability**: `typeof Storage !== 'undefined'`
2. **Wrap JSON.parse in try-catch**
3. **Validate parsed data structure**
4. **Fallback to defaults on any error**
5. **Log warnings for debugging**

See `references/error-handling.md` for complete error handling pattern.

## Testing Strategies

- Use test seam commands to manipulate localStorage
- Test both empty state and populated state
- Verify persistence across page reloads
- Test quota exceeded scenarios (if applicable)

## Code Structure

- Separate storage utilities by domain (settings, highScores)
- Export storage keys as constants
- Use consistent API: `load*()`, `save*()`, `get*()`
- Include JSDoc comments

## Template

See `assets/template.ts` for localStorage utility template.

## Resources

- `references/key-naming.md` - camelCase vs kebab-case patterns
- `references/error-handling.md` - Availability checks, JSON parsing, validation
- `assets/template.ts` - Template for localStorage utilities
