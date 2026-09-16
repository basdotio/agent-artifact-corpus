import { createBrowserClient } from "@supabase/ssr"
import type { Database } from "@/types/database.types"

/**
 * 브라우저(클라이언트 컴포넌트)용 Supabase 클라이언트.
 * - 'use client' 컴포넌트 / hooks / Zustand store 안에서만 사용.
 * - Server Component에서 호출하면 cookies 접근 불가로 동작하지 않는다.
 */
export function createClient() {
  return createBrowserClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  )
}
