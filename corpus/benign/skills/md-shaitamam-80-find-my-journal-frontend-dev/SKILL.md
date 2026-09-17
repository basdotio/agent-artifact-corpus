---
name: frontend-dev
description: React + TypeScript + Vite frontend development specialist. Use when building UI components, pages, forms, API integration, state management, or styling with Tailwind CSS. Triggers on requests for component creation, form handling, data fetching, responsive design, or debugging React applications. Includes Supabase integration patterns.
---

# Frontend Dev Skill

React + TypeScript + Vite specialist for modern web applications.

## Stack

| Layer | Technology |
|-------|------------|
| Framework | React 18+ |
| Language | TypeScript |
| Build | Vite |
| Styling | Tailwind CSS |
| Backend | Supabase (Auth + DB) |
| HTTP | fetch / TanStack Query |

## Project Structure

```
frontend/
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── ui/           # Base components (Button, Input, Card)
│   │   └── features/     # Feature-specific components
│   ├── pages/            # Route pages
│   ├── hooks/            # Custom hooks
│   ├── lib/              # Utilities & config
│   │   └── supabase.ts   # Supabase client
│   ├── types/            # TypeScript types
│   ├── services/         # API calls
│   └── App.tsx
├── .env.local            # Environment variables
└── tailwind.config.js
```

## Component Patterns

### Basic Component Template

```tsx
// components/features/SearchForm.tsx
import { useState } from 'react'

interface SearchFormProps {
  onSearch: (query: string) => void
  isLoading?: boolean
}

export function SearchForm({ onSearch, isLoading = false }: SearchFormProps) {
  const [query, setQuery] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) onSearch(query)
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search..."
        className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
        disabled={isLoading}
      />
      <button
        type="submit"
        disabled={isLoading || !query.trim()}
        className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
      >
        {isLoading ? 'Searching...' : 'Search'}
      </button>
    </form>
  )
}
```

### Custom Hook Pattern

```tsx
// hooks/useSearch.ts
import { useState, useCallback } from 'react'

interface UseSearchResult<T> {
  data: T | null
  isLoading: boolean
  error: string | null
  search: (query: string) => Promise<void>
}

export function useSearch<T>(endpoint: string): UseSearchResult<T> {
  const [data, setData] = useState<T | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const search = useCallback(async (query: string) => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await fetch(`${endpoint}?q=${encodeURIComponent(query)}`)
      if (!res.ok) throw new Error('Search failed')
      setData(await res.json())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setIsLoading(false)
    }
  }, [endpoint])

  return { data, isLoading, error, search }
}
```

## Supabase Integration

### Client Setup

```tsx
// lib/supabase.ts
import { createClient } from '@supabase/supabase-js'
import type { Database } from '@/types/database'

export const supabase = createClient<Database>(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY
)
```

### Auth Hook

```tsx
// hooks/useAuth.ts
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import type { User } from '@supabase/supabase-js'

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null)
      setLoading(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => setUser(session?.user ?? null)
    )

    return () => subscription.unsubscribe()
  }, [])

  return { user, loading, isAuthenticated: !!user }
}
```

### Data Fetching

```tsx
// services/journals.ts
import { supabase } from '@/lib/supabase'

export async function getSearchHistory(userId: string) {
  const { data, error } = await supabase
    .from('search_history')
    .select('*')
    .eq('user_id', userId)
    .order('created_at', { ascending: false })
    .limit(10)

  if (error) throw error
  return data
}
```

## Common Patterns

### Loading States

```tsx
function SearchResults({ isLoading, error, data }) {
  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorMessage message={error} />
  if (!data?.length) return <EmptyState message="No results found" />
  
  return (
    <ul className="space-y-4">
      {data.map(item => <ResultCard key={item.id} {...item} />)}
    </ul>
  )
}
```

### Form with Validation

```tsx
const [errors, setErrors] = useState<Record<string, string>>({})

const validate = (values: FormValues): boolean => {
  const newErrors: Record<string, string> = {}
  
  if (!values.title || values.title.length < 10) {
    newErrors.title = 'Title must be at least 10 characters'
  }
  if (!values.abstract || values.abstract.length < 50) {
    newErrors.abstract = 'Abstract must be at least 50 characters'
  }
  
  setErrors(newErrors)
  return Object.keys(newErrors).length === 0
}
```

### Protected Route

```tsx
// components/ProtectedRoute.tsx
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) return <LoadingSpinner />
  if (!user) return <Navigate to="/login" replace />
  
  return <>{children}</>
}
```

## Tailwind Patterns

### Responsive Design

```tsx
// Mobile-first approach
className="
  w-full              // Mobile: full width
  md:w-1/2            // Tablet: half width
  lg:w-1/3            // Desktop: third width
  p-4 md:p-6 lg:p-8   // Responsive padding
"
```

### Common Utilities

```tsx
// Card
"bg-white rounded-lg shadow-md p-6 border border-gray-200"

// Button Primary
"px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"

// Button Secondary
"px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"

// Input
"w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"

// Error Text
"text-sm text-red-600 mt-1"
```

## Environment Variables

```bash
# .env.local (NEVER commit!)
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
VITE_API_URL=https://api.example.com
```

Access in code:
```tsx
const apiUrl = import.meta.env.VITE_API_URL
```

## Error Handling

### Error Boundary (react-error-boundary)

```tsx
// Install: npm install react-error-boundary
import { ErrorBoundary } from 'react-error-boundary'

function ErrorFallback({ error, resetErrorBoundary }) {
  return (
    <div className="p-6 bg-red-50 rounded-lg text-center">
      <h2 className="text-red-800 font-semibold">Something went wrong</h2>
      <p className="text-red-600 text-sm mt-2">{error.message}</p>
      <button
        onClick={resetErrorBoundary}
        className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg"
      >
        Try again
      </button>
    </div>
  )
}

// Usage in App.tsx
<ErrorBoundary FallbackComponent={ErrorFallback}>
  <Routes />
</ErrorBoundary>
```

### Toast Notifications (sonner)

```tsx
// Install: npm install sonner
// App.tsx - add Toaster
import { Toaster } from 'sonner'

function App() {
  return (
    <>
      <Toaster position="top-right" richColors />
      <Routes />
    </>
  )
}

// Usage anywhere
import { toast } from 'sonner'

toast.success('Saved successfully')
toast.error('Failed to save')
toast.loading('Searching...')
```

## Loading States

### Skeleton Component

```tsx
// components/ui/Skeleton.tsx
export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={`animate-pulse bg-slate-200 rounded ${className}`} />
  )
}

// JournalCardSkeleton.tsx
export function JournalCardSkeleton() {
  return (
    <div className="bg-white rounded-2xl border p-6">
      <Skeleton className="h-6 w-3/4 mb-4" />
      <Skeleton className="h-4 w-1/2 mb-2" />
      <Skeleton className="h-4 w-1/3" />
      <div className="flex gap-2 mt-4">
        <Skeleton className="h-6 w-16 rounded-full" />
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
    </div>
  )
}

// Usage
{isLoading ? (
  <div className="space-y-4">
    {[...Array(3)].map((_, i) => <JournalCardSkeleton key={i} />)}
  </div>
) : (
  <JournalList data={data} />
)}
```

## Performance Optimization

### When to Use memo

```tsx
import { memo } from 'react'

// ✅ Use memo when:
// - Component re-renders often with same props
// - Component is expensive to render
// - Parent re-renders frequently

const JournalCard = memo(function JournalCard({ journal, onSave }: Props) {
  return (/* ... */)
})

// ✅ Use useMemo for expensive calculations
const sortedJournals = useMemo(() => 
  journals.sort((a, b) => b.impactFactor - a.impactFactor),
  [journals]
)

// ✅ Use useCallback for stable function references
const handleSave = useCallback((id: string) => {
  saveJournal(id)
}, [saveJournal])
```

### Component Splitting Guidelines

```
⚠️ Split component when:
- File exceeds 200-300 lines
- Multiple unrelated responsibilities
- Reusable sub-sections exist
- Testing becomes difficult

📁 Pattern:
Search.tsx (465 lines) → Split into:
├── SearchForm.tsx (form logic)
├── SearchResults.tsx (results display)
├── useJournalSearch.ts (data fetching hook)
└── SearchFilters.tsx (filter controls)
```

## RTL Support (Hebrew/Arabic)

### Logical Properties

```tsx
// ❌ Physical (breaks in RTL)
"ml-4 mr-2 pl-6 text-left border-l"

// ✅ Logical (works in RTL)
"ms-4 me-2 ps-6 text-start border-s"

// Mapping:
// ml/mr → ms/me (margin-start/end)
// pl/pr → ps/pe (padding-start/end)
// left/right → start/end
// border-l/r → border-s/e
// rounded-l/r → rounded-s/e
```

## Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| "VITE_ env not found" | Restart dev server after adding env vars |
| Hook called conditionally | Hooks must be at component top level |
| Infinite re-renders | Add dependencies to useEffect/useCallback |
| Type errors on Supabase | Generate types with `supabase gen types` |
| CORS errors | Check API URL, ensure backend allows origin |
| Component too large | Split when >200 lines, extract hooks |
| RTL layout broken | Use logical properties (ms/me/ps/pe) |

## Recommended Packages

```bash
# UI & UX
npm install sonner              # Toast notifications
npm install react-error-boundary # Error handling

# Forms
npm install react-hook-form     # Form management
npm install zod                 # Schema validation

# Data Fetching
npm install @tanstack/react-query # Server state management
```

## File References

- **Component Examples**: See `references/components.md`
- **Tailwind Cheatsheet**: See `references/tailwind.md`
- **TypeScript Patterns**: See `references/typescript.md`

## Quick Commands

```bash
# Dev server
npm run dev

# Type check
npm run type-check

# Build
npm run build

# Generate Supabase types
npx supabase gen types typescript --project-id YOUR_ID > src/types/database.ts
```
