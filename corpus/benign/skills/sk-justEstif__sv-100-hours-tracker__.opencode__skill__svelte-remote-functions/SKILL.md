---
name: svelte-remote-functions
description: Use SvelteKit remote functions (query, form, command, prerender) for type-safe client-server communication, data fetching, form handling, and mutations.
metadata:
  audience: developers
  workflow: sveltekit-development
---

# SvelteKit Remote Functions

Remote functions enable type-safe client-server communication in SvelteKit. They run on the server but can be called from anywhere in your app.

## When to Use This Skill

- Creating `.remote.ts` or `.remote.js` files
- Type-safe data fetching from components
- Form handling with schema validation
- Server-side mutations (likes, updates, deletes)
- Prerendering static data at build time

## Function Types

| Function      | Purpose                          | Returns                       |
| ------------- | -------------------------------- | ----------------------------- |
| `query`       | Read dynamic data                | Promise-like with `refresh()` |
| `query.batch` | Batched queries (n+1 solution)   | Promise-like                  |
| `form`        | Form submissions with validation | Spreadable form attributes    |
| `command`     | Programmatic mutations           | Promise                       |
| `prerender`   | Static data at build time        | Cached Promise-like           |

## Configuration

Enable in `svelte.config.js`:

```js
const config = {
  kit: {
    experimental: {
      remoteFunctions: true,
    },
  },
  compilerOptions: {
    experimental: {
      async: true, // Optional: enables await in components
    },
  },
};
```

## Basic Pattern

```ts
// src/routes/data.remote.ts
import * as v from "valibot";
import { query, form, command } from "$app/server";

export const getItems = query(async () => {
  // fetch from database
});

export const getItem = query(v.string(), async (id) => {
  // validated id parameter
});

export const createItem = form(v.object({ name: v.string() }), async (data) => {
  // handle form submission
});

export const deleteItem = command(v.string(), async (id) => {
  // handle mutation
});
```

## Full Documentation

Use the `svelte-mcp` skill and fetch documentation with section `kit/remote-functions` for complete API reference, form fields, validation, single-flight mutations, and advanced patterns.
