import { createClient } from "@supabase/supabase-js"
import type { Database } from "@/types/database.types"

/**
 * RLS 우회 service role 클라이언트.
 *
 * 사용처: cron, webhook, server action 안의 관리자 작업 등
 * 일반 유저 요청 흐름에서는 절대 사용하지 말 것 (RLS가 무력화됨).
 *
 * SUPABASE_SERVICE_ROLE_KEY는 서버에만 노출되어야 한다.
 * NEXT_PUBLIC_ prefix를 붙이지 않도록 주의.
 */
export function createServiceRoleClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY

  if (!url || !serviceRoleKey) {
    throw new Error("Supabase service role 환경변수가 설정되지 않았습니다.")
  }

  return createClient<Database>(url, serviceRoleKey, {
    auth: {
      persistSession: false,
      autoRefreshToken: false,
    },
  })
}
