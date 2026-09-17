---
name: ssr-tanstack-strapi
description: Build SSR applications with TanStack Start and Strapi CMS. Use when creating content-driven websites with server-side rendering, SEO requirements, and headless CMS integration. Covers monorepo setup, TanStack Query integration, type-safe API clients, and production-ready patterns.
---

# SSR TanStack Strapi

Build production-ready SSR applications using TanStack Start (React) frontend with Strapi headless CMS backend.

## When to Use

- Building content-driven websites (blogs, wikis, documentation sites)
- SEO-critical applications requiring server-side rendering
- Projects needing a headless CMS for content management
- Multi-entity applications with complex relationships
- Applications requiring search, filtering, and pagination

## Tech Stack

### Frontend
- **Framework**: TanStack Start (React-based full-stack framework)
- **Routing**: TanStack Router (file-based)
- **SSR**: Nitro-based server-side rendering
- **Data Fetching**: TanStack Query with SSR support
- **HTTP Client**: Native fetch + @strapi/client
- **Build Tool**: Vite
- **Language**: TypeScript

### Backend
- **CMS**: Strapi 5.x (headless)
- **Database**: PostgreSQL (recommended for production)
- **API**: REST with auto-generated endpoints

### Monorepo
- **Package Manager**: pnpm with workspaces
- **Structure**: `frontend/` + `backend/` in single repo

## Project Structure

```
my-app/
├── frontend/                    # TanStack Start application
│   ├── src/
│   │   ├── routes/              # File-based routing
│   │   │   ├── __root.tsx       # Root layout
│   │   │   ├── index.tsx        # Home page
│   │   │   └── posts/
│   │   │       ├── index.tsx    # List page
│   │   │       └── $slug.tsx    # Detail page
│   │   ├── hooks/               # TanStack Query hooks
│   │   ├── lib/
│   │   │   └── strapiClient.ts  # API client
│   │   ├── types/
│   │   │   └── strapi.ts        # TypeScript types
│   │   └── components/          # UI components
│   ├── app.config.ts            # TanStack Start config
│   └── package.json
├── backend/                     # Strapi application
│   └── src/api/                 # Content types
└── pnpm-workspace.yaml
```

## Quick Start

**Before starting, ask the user:**
> "Do you want to install the project in the current directory? (yes/no)"

- **If YES**: Create `frontend/` and `backend/` directly in the current directory
- **If NO**: Create a new project directory first, then create `frontend/` and `backend/` inside it

### 1. Initialize Monorepo

**If installing in current directory:**
```bash
# Create pnpm workspace in current directory
cat > pnpm-workspace.yaml << 'EOF'
packages:
  - 'frontend'
  - 'backend'
EOF
```

**If creating new project directory:**
```bash
# Ask user for project name, default to 'my-ssr-app'
read -p "Project name (default: my-ssr-app): " project_name
project_name=${project_name:-my-ssr-app}
mkdir "$project_name" && cd "$project_name"

# Create pnpm workspace
cat > pnpm-workspace.yaml << 'EOF'
packages:
  - 'frontend'
  - 'backend'
EOF
```

### 2. Initialize Frontend (TanStack Start)

**Use the new TanStack CLI with pnpm:**

```bash
# Interactive mode (recommended) - guides you through project setup
pnpm dlx @tanstack/cli create frontend

# Or non-interactive with defaults
pnpm dlx @tanstack/cli create frontend -y

# With add-ons (optional)
pnpm dlx @tanstack/cli create frontend --add-ons tanstack-query
```

**Note:** The CLI will create a project in the `frontend/` directory. After creation:
- Set up React + TypeScript
- Configure Vite + TanStack Router
- Set up file-based routing
- Configure development server

**Run the project:**
```bash
cd frontend
pnpm dev
# Open http://localhost:3000
```

### 3. Initialize Backend (Strapi)

**Use pnpm with the new Strapi CLI:**

```bash
# Create Strapi project (interactive mode)
pnpm dlx create-strapi@latest backend

# Or with options
pnpm dlx create-strapi@latest backend --template <template-name>
```

**Note:** The CLI will create a project in the `backend/` directory. After creation:
- Set up Strapi with TypeScript
- Configure database (SQLite by default for development)
- Set up admin panel
- Configure API endpoints

**Run the project:**
```bash
cd backend
pnpm dev
# Open http://localhost:1337/admin
```

### 4. Install Additional Dependencies

**Frontend dependencies:**

```bash
cd frontend

# Strapi client SDK
pnpm add @strapi/client

# TanStack Query for data fetching
pnpm add @tanstack/react-query

# Optional: Zustand for state management
pnpm add zustand

# Optional: DOMPurify for safe HTML rendering
pnpm add dompurify
pnpm add -D @types/dompurify
```

**Backend dependencies:**

```bash
cd backend

# PostgreSQL driver (for production)
pnpm add pg

# Or SQLite for development
pnpm add better-sqlite3
```

## Core Configuration

### 1. TanStack Start Config

Create/Update `frontend/app.config.ts`:

```typescript
import { defineConfig } from '@tanstack/react-start/config';
import tsConfigPaths from 'vite-tsconfig-paths';

export default defineConfig({
  vite: {
    plugins: [
      tsConfigPaths({
        projects: ['./tsconfig.json'],
      }),
    ],
  },
});
```

### 2. Strapi Client Setup

Create `frontend/src/lib/strapiClient.ts`:

```typescript
import { strapi } from '@strapi/client';

const STRAPI_URL = import.meta.env.VITE_STRAPI_URL || 'http://localhost:1337';

// Strapi SDK client
export const strapiClient = strapi({
  baseURL: STRAPI_URL,
});

// Type-safe fetch wrapper
export async function strapiFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${STRAPI_URL}/api${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}
```

### 3. TypeScript Types

Create `frontend/src/types/strapi.ts`:

```typescript
export interface StrapiResponse<T> {
  data: T;
  meta?: {
    pagination?: {
      page: number;
      pageSize: number;
      pageCount: number;
      total: number;
    };
  };
}

export interface StrapiImage {
  id: number;
  name: string;
  url: string;
  formats?: {
    thumbnail?: { url: string };
    small?: { url: string };
    medium?: { url: string };
    large?: { url: string };
  };
}

export interface Post {
  id: number;
  documentId: string;
  title: string;
  slug: string;
  content: string;
  excerpt?: string;
  featuredImage?: StrapiImage;
  publishedAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Category {
  id: number;
  documentId: string;
  name: string;
  slug: string;
  description?: string;
}
```

## Core Patterns

### 1. TanStack Query Hooks

Create `frontend/src/hooks/usePosts.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { strapiFetch } from '@/lib/strapiClient';
import type { Post, StrapiResponse } from '@/types/strapi';

export function usePosts(filters?: {
  category?: string;
  search?: string;
}) {
  return useQuery({
    queryKey: ['posts', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      
      if (filters?.category && filters.category !== 'all') {
        params.append('filters[category][slug][$eq]', filters.category);
      }
      
      if (filters?.search) {
        params.append('filters[title][$containsi]', filters.search);
      }
      
      params.append('populate', '*');
      params.append('sort[0]', 'publishedAt:desc');
      
      return strapiFetch<StrapiResponse<Post[]>>(`/posts?${params}`);
    },
  });
}

export function usePost(slug: string) {
  return useQuery({
    queryKey: ['post', slug],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('filters[slug][$eq]', slug);
      params.append('populate', '*');
      
      const response = await strapiFetch<StrapiResponse<Post[]>>(
        `/posts?${params}`
      );
      
      if (!response.data.length) {
        throw new Error('Post not found');
      }
      
      return response.data[0];
    },
  });
}
```

### 2. Route with SSR Data Fetching

```typescript
// frontend/src/routes/posts/$slug.tsx
import { createFileRoute } from '@tanstack/react-router';
import { usePost } from '@/hooks/usePosts';

export const Route = createFileRoute('/posts/$slug')({
  component: PostDetailPage,
  loader: async ({ params, context }) => {
    // Prefetch for SSR
    await context.queryClient.prefetchQuery({
      queryKey: ['post', params.slug],
      queryFn: () => fetchPost(params.slug),
    });
    return { slug: params.slug };
  },
  head: ({ loaderData }) => ({
    meta: [
      { title: `Post: ${loaderData.slug}` },
    ],
  }),
});

function PostDetailPage() {
  const { slug } = Route.useLoaderData();
  const { data: post, isLoading, error } = usePost(slug);
  
  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!post) return <div>Not found</div>;
  
  return (
    <article>
      <h1>{post.title}</h1>
      <div>{post.content}</div>
    </article>
  );
}
```

### 3. List Page with Filtering

```typescript
// frontend/src/routes/posts/index.tsx
import { createFileRoute, useSearch } from '@tanstack/react-router';
import { usePosts } from '@/hooks/usePosts';

export const Route = createFileRoute('/posts/')({
  component: PostsListPage,
  validateSearch: (search) => ({
    category: (search.category as string) || 'all',
    q: (search.q as string) || '',
  }),
});

function PostsListPage() {
  const { category, q } = useSearch({ from: '/posts/' });
  const { data, isLoading } = usePosts({ category, search: q });
  const navigate = useNavigate();
  
  return (
    <div>
      <input
        type="search"
        value={q}
        onChange={(e) => navigate({
          search: (prev) => ({ ...prev, q: e.target.value }),
        })}
        placeholder="Search posts..."
      />
      
      {isLoading ? (
        <div>Loading...</div>
      ) : (
        <div className="grid">
          {data?.data.map((post) => (
            <Link
              key={post.id}
              to="/posts/$slug"
              params={{ slug: post.slug }}
            >
              <h3>{post.title}</h3>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
```

### 4. Image Component with Lazy Loading

```typescript
// frontend/src/components/StrapiImage.tsx
import { useState } from 'react';
import type { StrapiImage as StrapiImageType } from '@/types/strapi';

interface StrapiImageProps {
  image: StrapiImageType;
  alt: string;
  size?: 'thumbnail' | 'small' | 'medium' | 'large';
  className?: string;
}

export function StrapiImage({ 
  image, 
  alt, 
  size = 'medium',
  className 
}: StrapiImageProps) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  
  const imageUrl = image.formats?.[size]?.url || image.url;
  const fullUrl = `${import.meta.env.VITE_STRAPI_URL}${imageUrl}`;
  
  if (error) {
    return <div className="bg-gray-200" />;
  }
  
  return (
    <img
      src={fullUrl}
      alt={alt}
      loading="lazy"
      className={`transition-opacity ${loaded ? 'opacity-100' : 'opacity-0'} ${className}`}
      onLoad={() => setLoaded(true)}
      onError={() => setError(true)}
    />
  );
}
```

### 5. Safe HTML Rendering

```typescript
// frontend/src/components/SafeHTML.tsx
import DOMPurify from 'dompurify';

interface SafeHTMLProps {
  html: string;
  className?: string;
}

export function SafeHTML({ html, className }: SafeHTMLProps) {
  const sanitized = DOMPurify.sanitize(html);
  
  return (
    <div 
      className={className}
      dangerouslySetInnerHTML={{ __html: sanitized }}
    />
  );
}
```

## Strapi Content Types Setup

### Example Content Types

1. **Category**
   - name: Text (required)
   - slug: UID (based on name)
   - description: Rich Text

2. **Post** (main content)
   - title: Text (required)
   - slug: UID (based on title)
   - content: Rich Text
   - excerpt: Text
   - category: Relation (Many-to-One)
   - featuredImage: Media
   - publishedAt: DateTime

3. **Tag**
   - name: Text (required)
   - slug: UID

### API Permissions

In Strapi Admin:
1. Settings > Users & Permissions Plugin > Roles > Public
2. Enable `find` and `findOne` for each content type
3. Save

## Environment Configuration

### Frontend (.env.local)

```env
VITE_STRAPI_URL=http://localhost:1337
```

### Backend (.env)

```env
# Database (PostgreSQL for production)
DATABASE_CLIENT=postgres
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=strapi
DATABASE_USERNAME=strapi
DATABASE_PASSWORD=password
DATABASE_SSL=false

# JWT Secrets
JWT_SECRET=your-jwt-secret
ADMIN_JWT_SECRET=your-admin-jwt-secret
APP_KEYS=key1,key2,key3,key4
API_TOKEN_SALT=your-api-token-salt
TRANSFER_TOKEN_SALT=your-transfer-token-salt
```

## Development Workflow

```bash
# Terminal 1: Start Strapi
cd backend
pnpm dev

# Terminal 2: Start TanStack Start
cd frontend
pnpm dev

# Access:
# - Frontend: http://localhost:3000
# - Strapi Admin: http://localhost:1337/admin
```

## Production Deployment

### Build Commands

```bash
# Build frontend
cd frontend
pnpm build

# Build Strapi
cd backend
pnpm build
```

### Production Checklist

- [ ] Configure production database (PostgreSQL)
- [ ] Set up environment variables
- [ ] Configure CORS in Strapi
- [ ] Set up image CDN (Cloudinary/AWS S3)
- [ ] Configure SSL certificates
- [ ] Set up monitoring and logging

## Common Patterns

### Pagination

```typescript
const { data } = useQuery({
  queryKey: ['posts', page],
  queryFn: () => strapiFetch(
    `/posts?pagination[page]=${page}&pagination[pageSize]=10`
  ),
});
```

### Sorting

```typescript
strapiFetch('/posts?sort[0]=publishedAt:desc')
```

### Deep Population

```typescript
strapiFetch('/posts?populate[category][populate]=*&populate[author][populate]=*')
```

### Search with Filters

```typescript
const params = new URLSearchParams();
params.append('filters[$or][0][title][$containsi]', query);
params.append('filters[$or][1][content][$containsi]', query);
strapiFetch(`/posts?${params}`);
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| CORS errors | Configure `cors` in Strapi config |
| Hydration mismatch | Ensure SSR and client render same data |
| Images not loading | Check `VITE_STRAPI_URL` includes protocol |
| Type errors | Regenerate types after Strapi schema changes |
| Query not refetching | Check `queryKey` includes all dependencies |

## Best Practices

1. **Always use `populate=*`** to get related data
2. **Use `documentId`** for stable identifiers (Strapi 5+)
3. **Implement error boundaries** for route errors
4. **Use `useSuspenseQuery`** for SSR-friendly loading states
5. **Cache API responses** with appropriate staleTime
6. **Implement search debouncing** (300-500ms)
7. **Use image formats** for responsive images
8. **Sanitize HTML** before rendering rich text
