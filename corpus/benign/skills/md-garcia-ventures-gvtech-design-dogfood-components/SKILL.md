---
name: dogfood-components
description: Guidelines for using library components within the documentation site itself to ensure consistency and showcase real-world usage.
---

# Dogfooding Components Skill

Use this skill whenever you are modifying the documentation site structure, headers, or layout. The goal is to maximize the use of our own UI components within the documentation logic itself (dogfooding).

## Workflow

### 1. Analysis

- **Identify Ad-hoc UI**: Look for custom HTML or static elements in the docs site (`apps/playground-web/src/App.tsx`, `apps/playground-web/src/components/docs/CombinedDocsLayout.tsx`, `apps/playground-web/src/pages/`) that replicate component functionality.
- **Check Library availability**: Verify if a corresponding component exists in `@gv-tech/ui-web` (e.g., Breadcrumbs, Tabs, Alerts, Badges).

### 2. Implementation

- **Prioritize Library Components**: Replace custom implementations with components from `@gv-tech/ui-web`.
- **Pass Real State**: Connect these components to the documentation's state (e.g., using `activeItem` with `Breadcrumb` or `Tabs`).
- **Consistent Styling**: Use the same variants and props that we recommend to our users.

### 3. Validation

- **Functional Check**: Ensure the component behaves correctly within the documentation context (e.g., navigation links work).
- **Visual Check**: Verify the component renders with the correct theme and layout in the docs.

## Checklist

- [ ] Identified custom UI elements that can be replaced.
- [ ] Used components from `@gv-tech/ui-web` instead of ad-hoc HTML/CSS.
- [ ] Component is correctly wired to relevant documentation state.
- [ ] Verified that navigation and interaction remains functional.
- [ ] `bun validate` passes successfully.
