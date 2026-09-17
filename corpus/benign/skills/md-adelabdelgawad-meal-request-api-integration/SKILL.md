---
name: api-integration
description: |
  Handle Next.js API routes proxying to FastAPI backend with proper cookie forwarding.
  Use when creating API proxy routes, implementing cookie forwarding, handling Set-Cookie
  propagation, creating server actions, or setting up SWR hooks with proper typing.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# API Integration

## Overview

This skill handles the complexity of Next.js to FastAPI API integration:

- **API Routes** - Proxy endpoints in `/app/api/`
- **Cookie Forwarding** - Server-side auth token handling
- **Server Actions** - Data fetching for Server Components
- **Client API** - Typed client-side API calls
- **SWR Integration** - Data fetching hooks

> **CRITICAL**: Cookie handling mistakes break authentication. Always test auth flows.

## When to Use This Skill

Activate when request involves:

- Creating new API proxy routes
- Implementing cookie forwarding
- Handling Set-Cookie header propagation
- Creating server actions for mutations
- Setting up SWR hooks with proper typing
- Fixing authentication issues in API calls

## Quick Reference

### File Locations

| Component | Path |
|-----------|------|
| API Routes | `src/my-app/app/api/` |
| Server API Client | `src/my-app/lib/http/axios-server.ts` |
| Client API Client | `src/my-app/lib/http/axios-client.ts` |
| Server Actions | `src/my-app/lib/actions/*.actions.ts` |
| Client API Functions | `src/my-app/lib/api/*.ts` |
| Type Definitions | `src/my-app/types/` |

## API Architecture

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   Browser Client    │────▶│   Next.js Server    │────▶│   FastAPI Backend   │
│                     │     │   /app/api/*        │     │   /api/v1/*         │
│  - SWR hooks        │     │  - Cookie forward   │     │  - JWT validation   │
│  - Client API       │     │  - Server actions   │     │  - Business logic   │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

## Server API Client Pattern

```typescript
// lib/http/axios-server.ts
import { cookies } from "next/headers";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

interface ApiResult<T> {
  ok: boolean;
  data: T;
  error?: string;
  status: number;
}

interface RequestOptions {
  params?: Record<string, string | number>;
  useVersioning?: boolean;
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access_token")?.value;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  return headers;
}

export const serverApi = {
  async get<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<ApiResult<T>> {
    try {
      const { params, useVersioning = true } = options;
      const headers = await getAuthHeaders();

      // Build URL with versioning
      let url = `${BACKEND_URL}${useVersioning ? "/api/v1" : ""}${endpoint}`;

      // Add query params
      if (params) {
        const searchParams = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
          searchParams.append(key, String(value));
        });
        url += `?${searchParams.toString()}`;
      }

      const response = await fetch(url, {
        method: "GET",
        headers,
        cache: "no-store",  // SSR always fresh
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        return {
          ok: false,
          data: null as T,
          error: error.detail || `HTTP ${response.status}`,
          status: response.status,
        };
      }

      const data = await response.json();
      return { ok: true, data, status: response.status };

    } catch (error) {
      return {
        ok: false,
        data: null as T,
        error: error instanceof Error ? error.message : "Network error",
        status: 0,
      };
    }
  },

  async post<T>(
    endpoint: string,
    body: unknown,
    options: RequestOptions = {}
  ): Promise<ApiResult<T>> {
    try {
      const { useVersioning = true } = options;
      const headers = await getAuthHeaders();

      const url = `${BACKEND_URL}${useVersioning ? "/api/v1" : ""}${endpoint}`;

      const response = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        return {
          ok: false,
          data: null as T,
          error: error.detail || `HTTP ${response.status}`,
          status: response.status,
        };
      }

      const data = await response.json();
      return { ok: true, data, status: response.status };

    } catch (error) {
      return {
        ok: false,
        data: null as T,
        error: error instanceof Error ? error.message : "Network error",
        status: 0,
      };
    }
  },

  // Similar for put, patch, delete...
};
```

## Client API Client Pattern

```typescript
// lib/http/axios-client.ts
"use client";

interface ApiResult<T> {
  ok: boolean;
  data: T;
  error?: string;
  status: number;
}

export const clientApi = {
  async get<T>(endpoint: string): Promise<ApiResult<T>> {
    try {
      const response = await fetch(endpoint, {
        method: "GET",
        credentials: "include",  // Send cookies
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        return {
          ok: false,
          data: null as T,
          error: error.detail || error.message || `HTTP ${response.status}`,
          status: response.status,
        };
      }

      const data = await response.json();
      return { ok: true, data, status: response.status };

    } catch (error) {
      return {
        ok: false,
        data: null as T,
        error: error instanceof Error ? error.message : "Network error",
        status: 0,
      };
    }
  },

  async post<T>(endpoint: string, body: unknown): Promise<ApiResult<T>> {
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        return {
          ok: false,
          data: null as T,
          error: error.detail || error.message || `HTTP ${response.status}`,
          status: response.status,
        };
      }

      const data = await response.json();
      return { ok: true, data, status: response.status };

    } catch (error) {
      return {
        ok: false,
        data: null as T,
        error: error instanceof Error ? error.message : "Network error",
        status: 0,
      };
    }
  },

  async put<T>(endpoint: string, body: unknown): Promise<ApiResult<T>> {
    // Similar to post with method: "PUT"
  },

  async delete<T>(endpoint: string): Promise<ApiResult<T>> {
    // Similar with method: "DELETE"
  },
};
```

## API Route Pattern

```typescript
// app/api/users/route.ts
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access_token")?.value;

  if (!accessToken) {
    return NextResponse.json(
      { error: "Unauthorized" },
      { status: 401 }
    );
  }

  try {
    // Forward query params
    const searchParams = request.nextUrl.searchParams;
    const url = new URL("/api/v1/users", BACKEND_URL);
    searchParams.forEach((value, key) => {
      url.searchParams.append(key, value);
    });

    const response = await fetch(url.toString(), {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);

  } catch (error) {
    console.error("API proxy error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access_token")?.value;

  if (!accessToken) {
    return NextResponse.json(
      { error: "Unauthorized" },
      { status: 401 }
    );
  }

  try {
    const body = await request.json();

    const response = await fetch(`${BACKEND_URL}/api/v1/users`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data, { status: 201 });

  } catch (error) {
    console.error("API proxy error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
```

## Server Action Pattern

```typescript
// lib/actions/users.actions.ts
"use server";

import { serverApi } from "@/lib/http/axios-server";
import type { UserListResponse, User } from "@/types/user";

export async function getUsers(
  limit: number = 10,
  skip: number = 0,
  filters?: {
    is_active?: string;
    search?: string;
  }
): Promise<UserListResponse | null> {
  try {
    const params: Record<string, string | number> = { limit, skip };

    if (filters?.is_active) params.is_active = filters.is_active;
    if (filters?.search) params.search = filters.search;

    const result = await serverApi.get<UserListResponse>("/users", {
      params,
      useVersioning: true,
    });

    if (result.ok) {
      return result.data;
    }

    console.error("Failed to fetch users:", result.error);
    return null;

  } catch (error) {
    console.error("Error in getUsers:", error);
    return null;
  }
}

export async function getUser(userId: string): Promise<User | null> {
  const result = await serverApi.get<User>(`/users/${userId}`);

  if (result.ok) {
    return result.data;
  }

  return null;
}
```

## Client API Function Pattern

```typescript
// lib/api/users.ts
import { clientApi } from "@/lib/http/axios-client";
import type { User, UserCreate, UserUpdate } from "@/types/user";

export async function createUser(data: UserCreate): Promise<User> {
  const result = await clientApi.post<User>("/api/users", data);

  if (!result.ok) {
    throw new Error(result.error || "Failed to create user");
  }

  return result.data;
}

export async function updateUser(
  userId: string,
  data: UserUpdate
): Promise<User> {
  const result = await clientApi.put<User>(`/api/users/${userId}`, data);

  if (!result.ok) {
    throw new Error(result.error || "Failed to update user");
  }

  return result.data;
}

export async function toggleUserStatus(
  userId: string,
  isActive: boolean
): Promise<User> {
  const result = await clientApi.put<User>(
    `/api/users/${userId}/status`,
    { isActive }
  );

  if (!result.ok) {
    throw new Error(result.error || "Failed to update status");
  }

  return result.data;
}

export async function deleteUser(userId: string): Promise<void> {
  const result = await clientApi.delete(`/api/users/${userId}`);

  if (!result.ok) {
    throw new Error(result.error || "Failed to delete user");
  }
}
```

## SWR Hook Pattern

```typescript
// hooks/use-users.ts
"use client";

import useSWR from "swr";
import { clientApi } from "@/lib/http/axios-client";
import type { UserListResponse } from "@/types/user";

const fetcher = async (url: string): Promise<UserListResponse> => {
  const result = await clientApi.get<UserListResponse>(url);
  if (!result.ok) {
    throw new Error(result.error);
  }
  return result.data;
};

interface UseUsersOptions {
  initialData?: UserListResponse | null;
  page?: number;
  limit?: number;
  filters?: {
    isActive?: boolean;
    search?: string;
  };
}

export function useUsers({
  initialData,
  page = 1,
  limit = 10,
  filters = {},
}: UseUsersOptions = {}) {
  // Build URL with params
  const params = new URLSearchParams();
  params.append("skip", ((page - 1) * limit).toString());
  params.append("limit", limit.toString());

  if (filters.isActive !== undefined) {
    params.append("is_active", String(filters.isActive));
  }
  if (filters.search) {
    params.append("search", filters.search);
  }

  const url = `/api/users?${params.toString()}`;

  const { data, error, isLoading, mutate } = useSWR<UserListResponse>(
    url,
    fetcher,
    {
      fallbackData: initialData ?? undefined,
      keepPreviousData: true,
      revalidateOnMount: false,
      revalidateIfStale: true,
      revalidateOnFocus: false,
    }
  );

  return {
    users: data?.items ?? [],
    total: data?.total ?? 0,
    activeCount: data?.activeCount ?? 0,
    inactiveCount: data?.inactiveCount ?? 0,
    isLoading,
    error,
    mutate,
  };
}
```

## Allowed Operations

**DO:**
- Forward auth cookies in server-side requests
- Return typed API results
- Handle errors consistently
- Use `credentials: "include"` in client requests
- Use server actions for SSR data fetching
- Use client API functions for mutations

**DON'T:**
- Expose backend URLs to client
- Skip cookie forwarding
- Return untyped responses
- Mix server and client code
- Forget error handling

## Validation Checklist

- [ ] Auth cookies forwarded from server
- [ ] API responses properly typed
- [ ] Error handling in all API calls
- [ ] Client requests include credentials
- [ ] Server actions use serverApi
- [ ] Client functions use clientApi
- [ ] SWR hooks properly configured

## Additional Resources

- [REFERENCE.md](REFERENCE.md) - Quick reference

## Trigger Phrases

- "API route", "proxy route"
- "cookie forwarding", "authorization"
- "server action", "client API"
- "SWR", "data fetching"
- "authentication", "401", "403"
