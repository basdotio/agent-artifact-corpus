import { createServerClient } from "@supabase/ssr"
import { NextResponse, type NextRequest } from "next/server"

/**
 * Supabase 세션 갱신 + 보호 라우트 리다이렉트.
 * 루트 middleware.ts에서 이 함수를 호출하는 패턴:
 *
 *   import { updateSession } from "@/lib/supabase/middleware"
 *   export async function middleware(request: NextRequest) {
 *     return await updateSession(request)
 *   }
 *
 * ⚠️ createServerClient와 supabase.auth.getUser() 사이에 다른 코드를 넣지 말 것.
 *    세션이 무작위로 만료되는 디버깅 어려운 버그가 생긴다.
 */
export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value),
          )
          supabaseResponse = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options),
          )
        },
      },
    },
  )

  const {
    data: { user },
  } = await supabase.auth.getUser()

  // 인증되지 않은 사용자 보호: /auth, /error 외 접근 시 로그인 페이지로
  if (
    !user &&
    !request.nextUrl.pathname.startsWith("/auth") &&
    !request.nextUrl.pathname.startsWith("/error")
  ) {
    const url = request.nextUrl.clone()
    url.pathname = "/auth/login"
    return NextResponse.redirect(url)
  }

  return supabaseResponse
}
