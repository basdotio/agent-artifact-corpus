---
name: modern-react-spa
description: Bootstrap production-ready React SPA projects. Use when creating new React applications, setting up frontend projects, or when user requests a modern React project with type-safe routing, data fetching, and state management. Triggers on "create React app", "new React project", "setup React SPA", "Vite React", or similar frontend project initialization requests.
---

# Modern React SPA Architecture

Bootstrap type-safe, scalable React SPAs with: Vite, TypeScript (strict), TanStack Router, TanStack Query, Zustand, and Tailwind CSS.

## Quick Start

Run these commands to initialize:

```bash
pnpm create vite@latest . --template react-ts
pnpm add @tanstack/react-router @tanstack/react-query zustand axios zod react-hook-form clsx tailwind-merge
pnpm add -D @tanstack/router-plugin tailwindcss @tailwindcss/vite eslint prettier
```

## Core Architecture Rules

### State Separation (Critical)

| State Type | Tool | Example |
|------------|------|---------|
| **Server State** | TanStack Query | API data, user profiles, lists |
| **Client State** | Zustand | UI toggles, theme, auth tokens |

**Never** put API responses in Zustand. Use Query hooks for all server data.

### Routing

Use TanStack Router with file-based routing in `src/routes/`. Validate search params with Zod schemas in route files.

### API Layer

All HTTP requests through `src/lib/api.ts`. Handle 401 globally via interceptors.

## Directory Structure

```
src/
├── components/
│   ├── ui/           # Primitives (Button, Input) - shadcn
│   └── layout/       # Navbar, Sidebar, Footer
├── hooks/            # Global hooks (useMediaQuery, useDebounce)
├── lib/
│   ├── api.ts        # HTTP client with interceptors
│   ├── queryClient.ts
│   └── utils.ts      # cn() helper
├── routes/
│   ├── __root.tsx    # Root layout + providers
│   └── index.tsx     # Homepage
├── stores/           # Zustand stores
└── main.tsx
```

## Implementation

For detailed setup instructions and boilerplate code, see:
- [references/setup-guide.md](references/setup-guide.md) - Step-by-step configuration
- [references/boilerplate.md](references/boilerplate.md) - Copy-paste starter files

## Styling

Use Tailwind utilities. Combine dynamic classes with `clsx` + `tailwind-merge`:

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs));
```

## Quality Gates

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "lint": "eslint src",
    "test": "vitest",
    "validate": "pnpm lint && tsc --noEmit && pnpm test"
  }
}
```