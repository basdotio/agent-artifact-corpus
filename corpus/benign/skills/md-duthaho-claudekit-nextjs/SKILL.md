---
name: nextjs
description: >
  Use this skill when working with Next.js applications, App Router, Server Components, or Server Actions. Trigger for any mention of Next.js, next/server, next/navigation, route handlers, SSR, SSG, ISR, middleware, or the app/ directory structure. Also applies when building full-stack React applications with API routes, implementing streaming or suspense boundaries, or configuring next.config.
---

# Next.js

## When to Use

- React applications with SSR/SSG
- Full-stack applications
- App Router patterns
- SEO-critical sites needing server rendering

## When NOT to Use

- Pure React SPAs without SSR needs — use the `frameworks/react` skill instead
- Non-React frameworks (Vue, Svelte, Angular) — this skill is React/Next.js specific
- Backend-only projects without a frontend — consider `frameworks/fastapi` or `frameworks/django`

---

## Core Patterns

### 1. App Router

#### Directory structure

```
app/
├── layout.tsx              # Root layout (wraps entire app)
├── page.tsx                # Home page (/)
├── loading.tsx             # Root loading UI (Suspense fallback)
├── error.tsx               # Root error boundary
├── not-found.tsx           # Custom 404 page
├── global-error.tsx        # Error boundary for root layout itself
├── favicon.ico
├── globals.css
├── api/
│   ├── users/
│   │   └── route.ts        # GET/POST /api/users
│   │   └── [id]/
│   │       └── route.ts    # GET/PUT/DELETE /api/users/:id
│   └── webhooks/
│       └── stripe/
│           └── route.ts    # POST /api/webhooks/stripe
├── (marketing)/            # Route group (no URL segment)
│   ├── layout.tsx          # Layout for marketing pages only
│   ├── page.tsx            # / (same as root, can override)
│   ├── about/
│   │   └── page.tsx        # /about
│   └── pricing/
│       └── page.tsx        # /pricing
├── (app)/                  # Route group for authenticated app
│   ├── layout.tsx          # App shell layout (sidebar, nav)
│   ├── dashboard/
│   │   ├── page.tsx        # /dashboard
│   │   ├── loading.tsx     # Loading skeleton for dashboard
│   │   └── error.tsx       # Error boundary for dashboard
│   ├── projects/
│   │   ├── page.tsx        # /projects
│   │   └── [id]/
│   │       ├── page.tsx    # /projects/:id
│   │       ├── edit/
│   │       │   └── page.tsx # /projects/:id/edit
│   │       └── layout.tsx  # Shared layout for project detail
│   └── settings/
│       └── page.tsx        # /settings
└── @modal/                 # Parallel route slot
    └── (.)projects/
        └── [id]/
            └── page.tsx    # Intercepted route modal
```

#### Special files and their roles

| File | Purpose | Renders when |
|------|---------|-------------|
| `page.tsx` | Route UI | URL matches segment |
| `layout.tsx` | Shared wrapper, preserved across navigation | Always for child routes |
| `loading.tsx` | Suspense fallback | While page/data is loading |
| `error.tsx` | Error boundary | When child throws |
| `not-found.tsx` | 404 UI | When `notFound()` is called |
| `route.ts` | API endpoint | HTTP request to segment |
| `template.tsx` | Like layout but re-mounts on navigation | Every navigation |
| `default.tsx` | Fallback for parallel routes | When slot has no match |

```tsx
// app/layout.tsx — Root layout (required)
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: { default: "My App", template: "%s | My App" },
  description: "Application description",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav>{/* Global navigation */}</nav>
        <main>{children}</main>
      </body>
    </html>
  );
}

// app/error.tsx — Error boundary (must be client component)
"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div>
      <h2>Something went wrong</h2>
      <button onClick={reset}>Try again</button>
    </div>
  );
}

// app/not-found.tsx
export default function NotFound() {
  return (
    <div>
      <h2>Page not found</h2>
      <p>The requested resource does not exist.</p>
    </div>
  );
}
```

### 2. Server vs Client Components

#### Decision guide

| Use Server Component when | Use Client Component when |
|---------------------------|--------------------------|
| Fetching data | Using useState, useEffect, useRef |
| Accessing backend resources directly | Adding event handlers (onClick, onChange) |
| Keeping sensitive data on server | Using browser APIs (localStorage, window) |
| Reducing client bundle size | Using third-party client libraries |
| SEO-critical content | Animations, real-time updates |

#### Composition patterns

```tsx
// Server Component (default — no directive needed)
// app/projects/page.tsx
import { ProjectList } from "./project-list";
import { SearchBar } from "./search-bar"; // Client component

export default async function ProjectsPage() {
  const projects = await db.project.findMany({
    orderBy: { createdAt: "desc" },
  });

  return (
    <div>
      <h1>Projects</h1>
      {/* Client component receives server data as props */}
      <SearchBar />
      {/* Server component can render client children */}
      <ProjectList projects={projects} />
    </div>
  );
}

// Client Component — must have "use client" at top
// app/projects/search-bar.tsx
"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";

export function SearchBar() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  function handleSearch(term: string) {
    const params = new URLSearchParams(searchParams);
    if (term) {
      params.set("q", term);
    } else {
      params.delete("q");
    }
    startTransition(() => {
      router.replace(`/projects?${params.toString()}`);
    });
  }

  return (
    <input
      type="search"
      placeholder="Search projects..."
      defaultValue={searchParams.get("q") ?? ""}
      onChange={(e) => handleSearch(e.target.value)}
      className={isPending ? "opacity-50" : ""}
    />
  );
}
```

**Key rule:** The `"use client"` directive creates a boundary. Everything imported into a client component becomes part of the client bundle. Pass server data down as serializable props (no functions, no classes).

### 3. Data Fetching

#### Server component fetch with caching

```tsx
// Fetch with automatic deduplication and caching
async function getProjects() {
  const res = await fetch("https://api.example.com/projects", {
    next: { revalidate: 60 },       // Revalidate every 60 seconds (ISR)
    // next: { tags: ["projects"] }, // Tag-based revalidation
    // cache: "no-store",            // Always fresh (SSR)
    // cache: "force-cache",         // Cache indefinitely (SSG)
  });
  if (!res.ok) throw new Error("Failed to fetch projects");
  return res.json();
}

export default async function ProjectsPage() {
  const projects = await getProjects();
  return <ProjectList projects={projects} />;
}
```

#### generateStaticParams for static generation

```tsx
// app/projects/[id]/page.tsx
export async function generateStaticParams() {
  const projects = await db.project.findMany({ select: { id: true } });
  return projects.map((p) => ({ id: String(p.id) }));
}

export default async function ProjectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const project = await db.project.findUnique({ where: { id } });
  if (!project) notFound();
  return <ProjectDetail project={project} />;
}
```

#### Route handlers (API routes)

```typescript
// app/api/projects/route.ts
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const page = Number(searchParams.get("page") ?? "1");
  const limit = Number(searchParams.get("limit") ?? "20");

  const projects = await db.project.findMany({
    skip: (page - 1) * limit,
    take: limit,
  });

  return NextResponse.json({ data: projects, page, limit });
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const project = await db.project.create({ data: body });
  return NextResponse.json(project, { status: 201 });
}

// Dynamic route: app/api/projects/[id]/route.ts
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const project = await db.project.findUnique({ where: { id } });
  if (!project) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }
  return NextResponse.json(project);
}
```

### 4. Server Actions

#### Form actions

```tsx
// app/actions.ts
"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { z } from "zod";

const ProjectSchema = z.object({
  title: z.string().min(3).max(200),
  description: z.string().optional(),
});

export async function createProject(prevState: unknown, formData: FormData) {
  const parsed = ProjectSchema.safeParse({
    title: formData.get("title"),
    description: formData.get("description"),
  });

  if (!parsed.success) {
    return { errors: parsed.error.flatten().fieldErrors };
  }

  const project = await db.project.create({ data: parsed.data });
  revalidatePath("/projects");
  redirect(`/projects/${project.id}`);
}

export async function deleteProject(id: string) {
  await db.project.delete({ where: { id } });
  revalidatePath("/projects");
}
```

#### Using actions in client components with useActionState

```tsx
"use client";

import { useActionState } from "react";
import { createProject } from "../actions";

export function CreateProjectForm() {
  const [state, formAction, isPending] = useActionState(createProject, null);

  return (
    <form action={formAction}>
      <input name="title" placeholder="Project title" required />
      {state?.errors?.title && (
        <p className="text-red-500">{state.errors.title[0]}</p>
      )}
      <textarea name="description" placeholder="Description" />
      <button type="submit" disabled={isPending}>
        {isPending ? "Creating..." : "Create Project"}
      </button>
    </form>
  );
}
```

#### Optimistic updates

```tsx
"use client";

import { useOptimistic } from "react";
import { deleteProject } from "../actions";

export function ProjectList({ projects }: { projects: Project[] }) {
  const [optimisticProjects, removeOptimistic] = useOptimistic(
    projects,
    (state, removedId: string) => state.filter((p) => p.id !== removedId),
  );

  async function handleDelete(id: string) {
    removeOptimistic(id);
    await deleteProject(id);
  }

  return (
    <ul>
      {optimisticProjects.map((project) => (
        <li key={project.id}>
          {project.title}
          <button onClick={() => handleDelete(project.id)}>Delete</button>
        </li>
      ))}
    </ul>
  );
}
```

### 5. Middleware

```typescript
// middleware.ts (root of project, NOT inside app/)
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Auth check
  const token = request.cookies.get("session")?.value;
  if (pathname.startsWith("/dashboard") && !token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Add headers
  const response = NextResponse.next();
  response.headers.set("x-pathname", pathname);

  // Geo-based redirect
  const country = request.geo?.country;
  if (pathname === "/" && country === "DE") {
    return NextResponse.redirect(new URL("/de", request.url));
  }

  // Rewrite (URL stays same, content changes)
  if (pathname.startsWith("/old-path")) {
    return NextResponse.rewrite(new URL("/new-path", request.url));
  }

  return response;
}

// Matcher: only run middleware on specific paths
export const config = {
  matcher: [
    // Match all paths except static files and api routes
    "/((?!_next/static|_next/image|favicon.ico|api).*)",
    // Or match specific paths
    // "/dashboard/:path*",
    // "/projects/:path*",
  ],
};
```

### 6. Caching

#### Cache layers overview

| Layer | What it caches | Control |
|-------|---------------|---------|
| Request Memoization | `fetch()` calls with same URL during single render | Automatic, per-request |
| Data Cache | `fetch()` results across requests | `next: { revalidate }`, `cache` option |
| Full Route Cache | HTML and RSC payload of static routes | `export const dynamic = "force-dynamic"` |
| Router Cache | Client-side RSC payload | `router.refresh()`, time-based |

#### Revalidation strategies

```tsx
// Time-based revalidation (ISR)
fetch(url, { next: { revalidate: 3600 } }); // 1 hour

// On-demand revalidation by path
import { revalidatePath } from "next/cache";
revalidatePath("/projects");          // Revalidate specific page
revalidatePath("/projects", "layout"); // Revalidate layout and all pages under it

// On-demand revalidation by tag
import { revalidateTag } from "next/cache";
// When fetching:
fetch(url, { next: { tags: ["projects"] } });
// When invalidating:
revalidateTag("projects");

// Route segment config
export const dynamic = "force-dynamic"; // Never cache (SSR)
export const revalidate = 60;           // ISR with 60s interval
export const fetchCache = "default-cache";
```

#### unstable_cache for non-fetch data

```tsx
import { unstable_cache } from "next/cache";

const getCachedProjects = unstable_cache(
  async (orgId: string) => {
    return db.project.findMany({ where: { organizationId: orgId } });
  },
  ["projects"],              // Cache key parts
  { revalidate: 60, tags: ["projects"] },
);

export default async function ProjectsPage() {
  const projects = await getCachedProjects("org-123");
  return <ProjectList projects={projects} />;
}
```

### 7. Route Groups & Parallel Routes

#### Route groups with `(groupName)`

Route groups organize routes without affecting the URL:

```
app/
├── (marketing)/     # URL: / , /about, /pricing (no "marketing" in URL)
│   ├── layout.tsx   # Marketing layout (hero, footer)
│   ├── page.tsx
│   └── about/page.tsx
├── (app)/           # URL: /dashboard, /projects
│   ├── layout.tsx   # App layout (sidebar, auth)
│   └── dashboard/page.tsx
```

#### Parallel routes with `@slotName`

```
app/
├── layout.tsx
├── page.tsx
├── @analytics/
│   ├── page.tsx           # Rendered in parallel
│   └── default.tsx        # Fallback when no match
├── @sidebar/
│   ├── page.tsx
│   └── default.tsx
```

```tsx
// app/layout.tsx — receives parallel route slots as props
export default function Layout({
  children,
  analytics,
  sidebar,
}: {
  children: React.ReactNode;
  analytics: React.ReactNode;
  sidebar: React.ReactNode;
}) {
  return (
    <div className="flex">
      <aside>{sidebar}</aside>
      <main>{children}</main>
      <aside>{analytics}</aside>
    </div>
  );
}
```

#### Intercepting routes

```
app/
├── projects/
│   ├── page.tsx                    # /projects — full list
│   └── [id]/
│       └── page.tsx                # /projects/:id — full page
├── @modal/
│   ├── (.)projects/
│   │   └── [id]/
│   │       └── page.tsx            # Intercepts /projects/:id as modal
│   └── default.tsx                 # No modal by default
```

Convention: `(.)` = same level, `(..)` = one level up, `(...)` = root.

### 8. Image & Font Optimization

#### next/image

```tsx
import Image from "next/image";

// Local image (automatically gets width/height)
import heroImage from "@/public/hero.png";

export function Hero() {
  return (
    <Image
      src={heroImage}
      alt="Hero banner"
      placeholder="blur"          // Auto blur placeholder for local images
      priority                     // Preload for LCP images
      className="w-full h-auto"
    />
  );
}

// Remote image (must specify dimensions)
export function Avatar({ url, name }: { url: string; name: string }) {
  return (
    <Image
      src={url}
      alt={name}
      width={48}
      height={48}
      className="rounded-full"
    />
  );
}

// next.config.ts — allow remote image domains
const config = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "avatars.githubusercontent.com" },
      { protocol: "https", hostname: "**.cloudinary.com" },
    ],
  },
};
```

#### next/font

```tsx
// app/layout.tsx
import { Inter, JetBrains_Mono } from "next/font/google";
import localFont from "next/font/local";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

const customFont = localFont({
  src: "./fonts/CustomFont.woff2",
  variable: "--font-custom",
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable}`}>
      <body className="font-sans">{children}</body>
    </html>
  );
}
```

```css
/* In Tailwind config or globals.css */
:root {
  --font-sans: var(--font-inter);
  --font-mono: var(--font-mono);
}
```

---

## Best Practices

1. **Default to Server Components** — only add `"use client"` when you need interactivity, event handlers, or browser APIs. Server Components reduce bundle size and allow direct data access.

2. **Colocate data fetching with the component that uses it** — fetch inside the Server Component that renders the data, not in a parent that passes it down. Next.js deduplicates identical `fetch()` calls automatically.

3. **Use `loading.tsx` for instant loading states** — every route segment can have a `loading.tsx` that wraps the page in a Suspense boundary. This gives users immediate feedback during navigation.

4. **Validate Server Action inputs** — Server Actions are public HTTP endpoints. Always validate with zod or similar. Never trust `formData` values without parsing and validating.

5. **Use route groups to share layouts without affecting URLs** — `(marketing)` and `(app)` let you have completely different layouts (public vs authenticated) without nesting URL segments.

6. **Prefer `revalidatePath`/`revalidateTag` over `cache: "no-store"`** — on-demand revalidation gives you fresh data when it changes while still serving cached content for performance. Only use `"no-store"` for truly dynamic per-request data.

7. **Put middleware at the project root** — `middleware.ts` must be at the same level as `app/`, not inside it. Use the `matcher` config to limit which paths it runs on for performance.

8. **Use `next/image` for all images** — it handles lazy loading, responsive sizes, format conversion (WebP/AVIF), and blur placeholders. Set `priority` on above-the-fold LCP images. Configure `remotePatterns` for external image sources.

---

## Common Pitfalls

1. **Using hooks in Server Components** — `useState`, `useEffect`, `useRouter` (from `next/navigation`) only work in Client Components. If you see "hooks can only be called inside a function component," add `"use client"` or restructure to push interactivity to a child component.

2. **Passing non-serializable props across the server/client boundary** — functions, class instances, and Dates cannot be passed from Server to Client Components. Serialize data to plain objects and strings before passing as props.

3. **Large client bundles from misplaced `"use client"`** — placing the directive too high in the tree pulls entire subtrees into the client bundle. Push `"use client"` as deep as possible, wrapping only the interactive leaf components.

4. **Stale data from aggressive caching** — the Full Route Cache and Data Cache can serve stale content. Use `revalidatePath()`/`revalidateTag()` in Server Actions and route handlers after mutations. Call `router.refresh()` on the client if needed.

5. **Missing `default.tsx` for parallel routes** — when navigating to a URL that does not match a parallel route slot, Next.js renders `default.tsx`. Without it, you get a 404. Always provide a default for every `@slot`.

6. **Forgetting `loading.tsx` leads to blank pages during navigation** — without loading boundaries, users see nothing while Server Components fetch data. Add `loading.tsx` at every route segment that does async work.

---

## Related Skills

- `frameworks/react` — React component patterns, hooks, and state management
- `languages/typescript` — TypeScript strict mode and type patterns
- `frontend/tailwind` — Styling with Tailwind CSS
- `frontend/shadcn-ui` — UI component library built on Radix and Tailwind
- `patterns/authentication` — Protected routes and auth middleware for Next.js
- `patterns/caching` — Next.js caching layers and invalidation
- `patterns/state-management` — React state management in Next.js apps
