---
name: editor-development
description: When you are working on the Tiptap v3 block editor. Use this for extending the editor, adding nodes, or debugging rich text issues.
---

# Editor Development (Tiptap v3)

## 1. Overview

- **Package:** `libs/editor` (published as `@nextblock-cms/editor`).
- **Core:** Tiptap v3 based (Headless).
- **Goal:** Provide a Notion-style block editing experience.

## 2. Key Locations

- **Entrypoint:** `libs/editor/src/lib/editor.tsx` (`NotionEditor` component).
- **Extensions:** `libs/editor/src/lib/kit.ts` (Defines the editor schema: nodes, marks, extensions).
- **Toolbar:** `libs/editor/src/lib/components/menus/Toolbar.tsx`.
- **Menus:** `libs/editor/src/lib/components/menus/` (Bubble, Floating, Slash menus).

## 3. Workflow

### Adding a new Node/Extension

1.  Install dependency if needed (e.g., `@tiptap/extension-youtube`).
2.  Register in `libs/editor/src/lib/kit.ts`.
3.  If it needs a custom view, create a React component and use `ReactNodeViewRenderer`.

### CSP Compliance

- **Strict CSP:** The editor runs in a strict CSP environment.
- **Inline Styles:** Avoid inline `style="..."` attributes if possible, or ensure they are handled by `Rehype` sanitization in the renderer.
- See `docs/03-CMS-AND-EDITOR.md` for deep dive.

## 4. Build & Test

- **Build:** `nx build editor`. Note: The build process injects `'use client';` directives.
- **Test:** Manual QA required for rich text interactions (selection, shortcuts, menu positioning).
