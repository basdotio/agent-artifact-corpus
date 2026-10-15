# Edge-Case Checklist (Core)

These categories are platform-neutral. For each one, check its trigger condition
against the feature in scope. Only add a test case when the condition is actually
met - applying every category to every feature produces noise, not coverage.

Platform-specific categories and detection signals live in `references/platforms/`
and are checked separately, in addition to this list.

| Category | Trigger condition |
|---|---|
| Network failure | Feature makes a network call (referenced in spec, or the code uses a networking layer) |
| Server error / malformed response | Feature makes a network call and the server can return an error status or invalid payload. Distinct from "network failure": here the connection succeeds but the response is bad. |
| Permission denied | Feature touches a permission-gated capability (camera, location, contacts, notifications, etc.) |
| Background / foreground transition | Feature involves a long-running process: media playback, real-time data, a timer, location tracking |
| Empty state / loading state | Feature fetches or displays a list or collection of data |
| Boundary / invalid input | Feature has a form or input field the user can type into |
| Large dataset / pagination | Feature displays a list or collection that can grow large |
| Session / auth expiry | Feature requires an authenticated session |
| Concurrency (double-tap, race condition) | Feature has an async action a user could trigger more than once (e.g. a submit button) |
| App killed & relaunch (state restoration) | Feature has state that should survive being killed: a draft, scroll position, an in-progress session |
| Data migration / version upgrade | Feature depends on a local data schema that has changed or could change (e.g. Core Data / SwiftData model) |
| Multi-device / concurrent session | Feature is tied to an account that can be active on more than one device |
| Rotation | Applies to every screen by default, unless the screen is explicitly locked to one orientation |
| Accessibility baseline | Applies to every screen: one generic test case per screen at minimum. Add more only if the screen has a custom control or gesture that a screen reader needs specific handling for |

Every test case generated from this checklist must be marked:
`Source: inferred (checklist: <category name>)`
