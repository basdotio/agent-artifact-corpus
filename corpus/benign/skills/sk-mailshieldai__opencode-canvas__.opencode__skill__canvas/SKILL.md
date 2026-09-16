---
name: canvas
description: |
  **The primary skill for terminal TUI components.** Covers spawning, controlling, and interacting with terminal canvases.
  Use when displaying calendars, documents, or flight bookings.
---

# Canvas TUI Toolkit

**Start here when using terminal canvases.** This skill covers the overall workflow, canvas types, and IPC communication.

## Example Prompts

Try asking Claude things like:

**Calendar:**
- "Schedule a meeting with the team next week"
- "Find a time when Alice and Bob are both free"

**Document:**
- "Draft an email to the sales team about the new feature"
- "Help me edit this document - let me select what to change"

**Flight:**
- "Find flights from SFO to Denver next Friday"
- "Book me a window seat on the morning flight"

## Overview

Canvas provides interactive terminal displays (TUIs) that can be spawned and controlled via the OpenCode tools. Each canvas type supports multiple scenarios for different interaction modes.

## Available Canvas Types

| Canvas | Purpose | Scenarios |
|--------|---------|-----------|
| `calendar` | Display calendars, pick meeting times | `display`, `meeting-picker` |
| `document` | View/edit markdown documents | `display`, `edit`, `email-preview` |
| `flight` | Flight comparison and seat selection | `booking` |

## OpenCode Tools

### `canvas_spawn`
Spawn a canvas in a tmux split pane.

```typescript
canvas_spawn({
  kind: "calendar",
  scenario: "meeting-picker",
  config: JSON.stringify({
    calendars: [
      { name: "Alice", color: "blue", events: [...] },
      { name: "Bob", color: "green", events: [...] }
    ],
    slotGranularity: 30
  })
})
// Returns: { success: true, id: "calendar-1234567890-abc123", ... }
```

### `canvas_update`
Send updated config to a running canvas.

```typescript
canvas_update({
  id: "calendar-1234567890-abc123",
  config: JSON.stringify({ events: [...] })
})
```

### `canvas_selection`
Get text selection from a document canvas.

```typescript
canvas_selection({ id: "document-1234567890-abc123" })
// Returns: { success: true, selection: { selectedText: "...", startOffset: 0, endOffset: 10 } }
```

### `canvas_content`
Get full content from a document canvas.

```typescript
canvas_content({ id: "document-1234567890-abc123" })
// Returns: { success: true, content: { content: "...", cursorPosition: 0 } }
```

### `canvas_close`
Close a running canvas.

```typescript
canvas_close({ id: "calendar-1234567890-abc123" })
```

## IPC Communication

Interactive canvases communicate via Unix domain sockets.

**Canvas -> Controller:**
```typescript
{ type: "ready", scenario }        // Canvas is ready
{ type: "selected", data }         // User made a selection
{ type: "cancelled", reason? }     // User cancelled
{ type: "error", message }         // Error occurred
```

**Controller -> Canvas:**
```typescript
{ type: "update", config }  // Update canvas configuration
{ type: "close" }           // Request canvas to close
{ type: "ping" }            // Health check
```

## Requirements

- **tmux**: Canvas spawning requires a tmux session
- **Terminal with mouse support**: For click-based interactions
- **Bun**: Runtime for executing canvas commands

## Skills Reference

| Skill | Purpose |
|-------|---------|
| `calendar` | Calendar display and meeting picker details |
| `document` | Document rendering and text selection |
| `flight` | Flight comparison and seat map details |
