---
name: seating-ui-worker
description: Worker for the floor-plan read-only occupancy viewer, including React UI, state wiring, and regression tests
---

# Seating UI Worker

NOTE: Startup and cleanup are handled by `worker-base`. This skill defines the WORK PROCEDURE.

## When to Use This Skill

Use this skill for features that touch the floor-plan experience in `src/components/features/seating/**`, the related App Router entrypoints under `src/app/app/(app)/floor-plan` and `src/app/app/(app)/seating/**`, supporting floor-plan hooks/helpers, and the regression tests that prove the read-only contract.

## Required Skills

- `vercel-react-best-practices` — invoke before editing React/Next.js components so the implementation follows current React/Next.js performance and composition guidance.
- `agent-browser` — invoke for manual browser verification after implementation. Use the authenticated `/floor-plan` route first and the dev harness only if auth/bootstrap is blocked.

## Work Procedure

1. **Read the assignment carefully.**
   - Read `AGENTS.md`, the mission `AGENTS.md`, and `.factory/library/architecture.md`.
   - Read the relevant floor-plan files before editing.
   - Keep the work on the canonical floor-plan implementation; do not create duplicate routes or alternate flows.

2. **Understand the current behavior.**
   - Inspect `FloorPlanPage`, `FloorCanvas`, `TableInspector`, `useFloorPlanTables`, and any touched route files.
   - Confirm which status helpers and UI primitives already exist.
   - Note the exact read-only behaviors the feature must preserve or change.

3. **Write tests first (RED).**
   - Add or update focused Vitest / Testing Library tests before implementation.
   - For hooks/helpers, extend `tests/ops/useFloorPlanTables.test.tsx` or the relevant test file.
   - For page/component behavior, add focused component tests that prove the requested read-only contract.
   - Run the new/updated test target and capture the failing result before making implementation changes.

4. **Implement the feature (GREEN).**
   - Use existing Shadcn/UI primitives from `src/components/ui`.
   - Keep `FloorPlanPage` orchestration-only; avoid reintroducing navigation-side effects.
   - Keep status presentation centralized in `src/components/features/seating/floor-plan/lib/status.ts`.
   - Preserve keyboard pan/zoom, empty-search handling, route redirects, and current data sources.
   - When changing copy, ensure it is informational-only and does not mention booking actions.

5. **Make tests pass.**
   - Re-run the targeted tests until they pass.
   - If the feature changes status semantics or selection behavior, verify both the intended behavior and the no-regression cases.

6. **Run validators.**
   - Run the mission test command from `.factory/services.yaml`.
   - Run the mission lint command from `.factory/services.yaml`.
   - Run `pnpm typecheck`.
   - If a validator fails because of your changes, fix it before handoff.
   - Do not leave long-running or watch processes behind.

7. **Manual verification with `agent-browser`.**
   - Start the app if needed with the mission web service.
   - Log in at `http://app.localhost:3000/auth/signin` using the validator credentials documented in `.factory/library/user-testing.md`.
   - Verify the assigned flow on desktop or mobile as required by the feature.
   - If auth/bootstrap is blocked, use `http://localhost:3000/dev/ops-floor-plan` and document the fallback.
   - Record the exact interaction sequence and observed result in the handoff.

8. **Commit and hand off.**
   - Stage only the files relevant to the feature.
   - Commit with a descriptive message.
   - Return a concrete handoff that lists tests, browser checks, and any discovered issues.

## Example Handoff

```json
{
  "salientSummary": "Removed booking CTAs from FloorPlanPage and TableInspector, introduced a read-only context header and idle panel copy, and added component tests proving no mutation controls remain. Ran targeted vitest in red/green order, then passed the mission lint/typecheck/test commands and verified the authenticated /floor-plan route on desktop and mobile.",
  "whatWasImplemented": "Refactored the floor-plan shell into a read-only orchestration surface: dropped router-driven booking actions, replaced action-oriented header/inspector copy with passive read-only messaging, preserved zone/date/search/time controls, and kept route redirects unchanged. Added regression tests covering CTA removal, idle-state copy, and selection-driven detail rendering.",
  "whatWasLeftUndone": "",
  "verification": {
    "commandsRun": [
      {
        "command": "npx vitest run tests/components/floor-plan/FloorPlanPage.test.tsx --reporter=verbose",
        "exitCode": 1,
        "observation": "RED: new assertions failed because New booking/Browse bookings buttons were still rendered."
      },
      {
        "command": "npx vitest run tests/components/floor-plan/FloorPlanPage.test.tsx --reporter=verbose",
        "exitCode": 0,
        "observation": "GREEN: updated shell and inspector tests all passed."
      },
      {
        "command": "npx vitest run --maxWorkers=9",
        "exitCode": 0,
        "observation": "Mission test command passed."
      },
      {
        "command": "npx eslint \"src/components/features/seating/**/*.{ts,tsx}\" \"src/app/app/(app)/floor-plan/page.tsx\" \"src/app/app/(app)/seating/page.tsx\" \"src/app/app/(app)/seating/floor-plan/page.tsx\" \"src/app/(public)/dev/ops-floor-plan/**/*.{ts,tsx}\" \"tests/**/*.{ts,tsx}\"",
        "exitCode": 0,
        "observation": "Mission lint command passed."
      },
      {
        "command": "pnpm typecheck",
        "exitCode": 0,
        "observation": "TypeScript passed with no new errors."
      }
    ],
    "interactiveChecks": [
      {
        "action": "Logged in at http://app.localhost:3000/auth/signin, opened /floor-plan on desktop, and confirmed the header showed only read-only context with no booking buttons.",
        "observed": "No New booking/Browse bookings actions remained and the route stayed on /floor-plan."
      },
      {
        "action": "Selected a table on desktop, then opened the same flow on a mobile viewport.",
        "observed": "Desktop panel and mobile sheet showed the same read-only fields and no action buttons."
      }
    ]
  },
  "tests": {
    "added": [
      {
        "file": "tests/components/floor-plan/FloorPlanPage.test.tsx",
        "cases": [
          {
            "name": "renders no booking CTAs in the shell",
            "verifies": "The read-only redesign removes booking-navigation and assignment controls."
          },
          {
            "name": "opens passive table details on selection",
            "verifies": "Selecting a table shows the expected read-only fields only."
          }
        ]
      }
    ]
  },
  "discoveredIssues": []
}
```

## When to Return to Orchestrator

- The feature needs a new backend/data contract or route structure change that falls outside this mission’s boundaries.
- Required UI behavior is ambiguous, especially around selection persistence or responsive parity.
- Auth/bootstrap or the dev harness is unavailable and prevents manual verification.
- Validators fail for unrelated pre-existing reasons that block completion.
