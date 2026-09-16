import { createServerClient } from "@supabase/ssr"
import { cookies } from "next/headers"
import type { Database } from "@/types/database.types"

/**
 * Server Component / Route Handler / Server Action용 Supabase 클라이언트.
 * - 매 요청마다 새로 만들어 사용 (cookieStore가 요청별로 다름).
 * - getAll/setAll 패턴은 Supabase SSR 권장 방식.
 */
export async function createClient() {
  const cookieStore = await cookies()

  return createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll()
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options),
            )
          } catch {
            // Server Component에서 setAll 호출 시 발생.
            // middleware에서 세션 갱신 중이면 무시해도 안전하다.
          }
        },
      },
    },
  )
}
