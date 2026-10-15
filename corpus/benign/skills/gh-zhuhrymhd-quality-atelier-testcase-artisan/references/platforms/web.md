# Platform Pack: Web

Loaded when the repo root has `package.json` with a frontend framework dependency
(react, vue, svelte, angular, etc.), or a `vite.config.*` / `index.html` at the root.
A plain `package.json` with no frontend framework and no such config file is not
enough on its own - treat it as an undetected stack instead (see SKILL.md Step 3)
rather than assuming Web conventions apply.

## Detection signals for core categories

Use these to decide whether a core category from `edge-case-checklist.md` actually
applies, and to phrase the test case in web-accurate terms.

| Core category | Web-specific signal / phrasing |
|---|---|
| Permission denied | Check for `navigator.permissions`, `getUserMedia`, or `Notification.requestPermission` usage. Steps should reference the browser's native permission prompt, not a custom in-app dialog. |
| Background / foreground | Use the Page Visibility API (`document.visibilitychange`) as the signal: a backgrounded/minimized tab, not a killed process. |
| App killed & relaunch | On web this means a closed tab/window or a hard refresh, not OS process death. State must be checked against `localStorage`, `sessionStorage`, or IndexedDB rather than any OS-level restoration mechanism. |
| Rotation | Relevant mainly for mobile web: treat it as a responsive-breakpoint / viewport-width change rather than a full page recreation. |
| Session / auth expiry | Distinguish an httpOnly-cookie-based session (server-controlled expiry) from a client-stored token (e.g. JWT in `localStorage`), since the failure mode and the fix differ. Consider whether a refresh-token flow exists. |

## Web-exclusive categories

These have no equivalent in the platform-neutral checklist and only apply on web.

| Category | Trigger condition |
|---|---|
| Browser back/forward navigation | Feature interacts with the History API or client-side routing (SPA navigation) |
| Page refresh / hard reload | Feature has in-progress client-side state that a refresh would wipe if not persisted |
| Responsive breakpoints | Feature's layout must adapt across viewport widths (not just mobile vs desktop) |
| Multi-tab state sync | Feature's state should stay consistent if the same app is open in more than one tab (relevant if `BroadcastChannel` or storage events are used) |
| Cross-browser compatibility | Feature uses a Web API that isn't uniformly supported across major browsers |
| Slow / throttled connection | Feature has a loading sequence that should degrade gracefully, distinct from a full network failure or a server error |
| Ad blocker / extension interference | Feature depends on a third-party script or tracking pixel that a blocker could prevent from loading |
| Browser zoom / text scaling | Feature's layout must stay usable when the browser's zoom or font size is increased significantly |

Mark test cases from this section the same way as core checklist items:
`Source: inferred (checklist: <category name>)`.
