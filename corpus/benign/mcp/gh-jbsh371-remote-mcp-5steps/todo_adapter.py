"""최종 장 - 여러분의 서비스로 옮기기

바뀐 것: 도구 함수의 몸통. 파일 대신 여러분 서비스 API(service_api.py)를 부릅니다.
도구 바깥(전송·OAuth·로그인·발급·검증)은 5단계 그대로. diff todo_v5.py todo_adapter.py 로 확인하세요.
"""

from fastmcp import FastMCP
from fastmcp.server.auth import OAuthProvider
from fastmcp.server.auth.auth import (
    ClientRegistrationOptions, PrivateKeyJWTClientAuthenticator, TokenHandler,
)
from fastmcp.server.auth.cimd import CIMDClientManager
from mcp.server.auth.handlers.metadata import MetadataHandler
from mcp.server.auth.routes import build_metadata, cors_middleware
from mcp.server.auth.settings import RevocationOptions
from fastmcp.server.dependencies import get_access_token
from mcp.server.auth.provider import (
    AccessToken, AuthorizationCode, AuthorizationParams,
    AuthorizeError, RefreshToken, TokenError, construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.routing import Route

import hashlib, os, secrets, sys, time
from datetime import datetime, timezone
import httpx
from issue_token import issue_token, token_info

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")
TOKEN_TTL = 3600                           # 로그인이 내주는 토큰의 수명 (초)
PENDING_TTL = 600                          # 진행 중인 로그인이 버티는 시간 (초)

# 미리 만들어 둔 계정 셋. 가입·재설정·잠금은 만들지 않습니다.
USERS = {
    "kim": hashlib.sha256(b"kim-pw").hexdigest(),
    "lee": hashlib.sha256(b"lee-pw").hexdigest(),
    "park": hashlib.sha256(b"park-pw").hexdigest(),
}

LOGIN_FORM = """<!doctype html><meta charset="utf-8">
<title>로그인</title>
<h2>TODO 서버 로그인</h2>
<p style="color:#c00">{error}</p>
<form method="post">
  <input type="hidden" name="txn" value="{txn}">
  <p><input name="username" placeholder="아이디" autofocus></p>
  <p><input name="password" type="password" placeholder="비밀번호"></p>
  <p><button type="submit">로그인</button></p>
</form>"""


# ---- OAuth 제공자 ------------------------------------------



class TodoOAuthProvider(OAuthProvider):
    # 보관함을 마련하고 등록 창구를 켭니다
    def __init__(self, base_url: str):
        super().__init__(
            base_url=base_url,
            # 기본값이 False 입니다. 안 켜면 /register 가 404 라서
            #    자기 문서가 없는 클라이언트(Inspector)가 붙지 못합니다 - 부록 H.
            client_registration_options=ClientRegistrationOptions(enabled=True),
        )
        # 주소는 여기서 한 번만 다듬습니다. 아래는 전부 이 둘을 씁니다
        self._base = str(base_url).rstrip("/")
        self._resource = f"{self._base}/mcp"    # 이 서버. 토큰은 여기서만 통합니다
        self._clients: dict[str, OAuthClientInformationFull] = {}
        # 클라이언트 문서를 읽어 오고 검사하는 일을 맡습니다
        self._cimd = CIMDClientManager(enable_cimd=True)
        self._pending: dict[str, tuple[str, AuthorizationParams, float]] = {}
        self._codes: dict[str, AuthorizationCode] = {}
        self._refresh: dict[str, RefreshToken] = {}
        self._issued: dict[str, tuple[str, str]] = {}   # 토큰 → (사용자, client_id)

    # 클라이언트가 누구인지 확인합니다 - FastMCP가 알아서 부릅니다
    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        if self._cimd.is_cimd_client_id(client_id):        # 이름표(client_id)가 주소 모양이면
            return await self._cimd.get_client(client_id)  #   그 주소의 문서를 읽어 확인
        return self._clients.get(client_id)                # 주소 모양이 아니면 등록해 둔 것을 찾습니다

    # 등록해 달라고 오면 적어 둡니다
    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self._clients[client_info.client_id] = client_info

    # FastMCP의 주소 목록을 손봅니다. 둘을 갈아 끼우고 /login 하나를 더합니다
    def get_routes(self, mcp_path: str | None = None) -> list[Route]:
        routes = super().get_routes(mcp_path)              # FastMCP의 표준 라우트
        routes = self._enable_cimd_routes(routes)          # 새 방식으로 바꿔 답니다
        routes.append(Route("/login", self._login, methods=["GET", "POST"]))
        return routes

    # 표준 라우트 둘을 새 방식용으로 바꿉니다. 나머지는 그대로 둡니다.
    #   /token      - 서명하는 클라이언트는 여기서 서명한 JWT로 자기를 증명합니다
    #   메타데이터  - "우리는 새 방식도 받는다"고 알립니다
    def _enable_cimd_routes(self, routes: list[Route]) -> list[Route]:
        out = []
        for r in routes:
            if getattr(r, "path", None) == "/token":
                handler = TokenHandler(
                    provider=self,
                    client_authenticator=PrivateKeyJWTClientAuthenticator(
                        provider=self, cimd_manager=self._cimd,
                        token_endpoint_url=f"{self._base}/token",
                    ),
                )
                out.append(Route("/token",
                                 cors_middleware(handler.handle, ["POST", "OPTIONS"]),
                                 methods=["POST", "OPTIONS"]))
            elif getattr(r, "path", None) == "/.well-known/oauth-authorization-server":
                meta = build_metadata(
                    self.base_url, self.service_documentation_url,
                    self.client_registration_options or ClientRegistrationOptions(),
                    self.revocation_options or RevocationOptions(),
                )
                meta.issuer = self.issuer_url
                meta.client_id_metadata_document_supported = True
                meta.token_endpoint_auth_methods_supported = ["none", "private_key_jwt"]
                out.append(Route(r.path,
                                 cors_middleware(MetadataHandler(meta).handle, ["GET", "OPTIONS"]),
                                 methods=r.methods or ["GET", "OPTIONS"], name=r.name))
            else:
                out.append(r)
        return out

    # 끝내지 않고 떠난 로그인을 걷어냅니다. 안 걷으면 메모리에 계속 쌓입니다
    def _sweep_pending(self) -> None:
        dead = time.time() - PENDING_TTL
        for txn in [k for k, v in self._pending.items() if v[2] < dead]:
            del self._pending[txn]

    # 로그인 화면으로 보내는 자리. 여기서 인가 코드를 내주면 안 됩니다 - 사람에게 먼저 물어봐야 합니다.
    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        if not params.code_challenge:
            raise AuthorizeError(
                error="invalid_request", error_description="PKCE가 필요합니다."
            )
        # 남의 서버를 쓰겠다는 요청이면 여기서 끊습니다
        if params.resource and str(params.resource).rstrip("/") != self._resource:
            raise AuthorizeError(
                error="invalid_target",
                error_description=f"이 서버를 위한 인가 요청이 아닙니다: {params.resource}",
            )
        self._sweep_pending()
        txn = secrets.token_urlsafe(24)
        self._pending[txn] = (client.client_id, params, time.time())
        return f"{self._base}/login?txn={txn}"            # 인가 코드가 아니라 로그인 주소

    # 우리가 만드는 유일한 화면
    async def _login(self, request):
        txn = request.query_params.get("txn") or (await request.form()).get("txn")
        entry = self._pending.get(txn)
        if not entry or time.time() - entry[2] > PENDING_TTL:
            self._pending.pop(txn, None)                   # 기한이 지난 로그인
            return HTMLResponse("만료된 요청입니다. 다시 시도해 주세요.", 400)

        if request.method == "GET":
            return HTMLResponse(LOGIN_FORM.format(txn=txn, error=""))

        form = await request.form()
        user = self._verify(form.get("username", ""), form.get("password", ""))
        if not user:
            # 실패 사유를 구분하지 않습니다
            return HTMLResponse(
                LOGIN_FORM.format(txn=txn, error="로그인 실패"), 401
            )

        client_id, params, _ = self._pending.pop(txn)      # 임시 번호는 한 번만 씁니다
        code = AuthorizationCode(
            code=secrets.token_urlsafe(32),
            client_id=client_id,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            scopes=params.scopes or [],
            expires_at=time.time() + 300,
            code_challenge=params.code_challenge,
            resource=params.resource,
            subject=user,                                  # 여기에 사용자를 실습니다
        )
        self._codes[code.code] = code
        return RedirectResponse(
            construct_redirect_uri(str(params.redirect_uri),
                                   code=code.code, state=params.state),
            status_code=302,
        )

    # 아이디·비밀번호를 대조합니다. 맞으면 아이디, 아니면 None
    def _verify(self, username: str, password: str) -> str | None:
        stored = USERS.get(username)
        if stored and secrets.compare_digest(
            stored, hashlib.sha256(password.encode()).hexdigest()
        ):
            return username
        return None

    # 인가 코드가 이 클라이언트 것이고 아직 안 만료됐는지 봅니다
    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        code = self._codes.get(authorization_code)
        if code and code.client_id == client.client_id and code.expires_at > time.time():
            return code
        return None

    # 4단계 발급을 그대로 부릅니다. 새로 만드는 것이 아닙니다.
    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        if self._codes.pop(authorization_code.code, None) is None:
            raise TokenError("invalid_grant", "이미 사용된 코드입니다.")

        user = authorization_code.subject
        token = issue_token(user, ttl=TOKEN_TTL, resource=self._resource)  # 4단계의 그 함수
        self._issued[token] = (user, client.client_id)

        refresh = secrets.token_urlsafe(32)
        self._refresh[refresh] = RefreshToken(
            token=refresh, client_id=client.client_id,
            scopes=authorization_code.scopes, expires_at=None,
        )
        self._issued[refresh] = (user, client.client_id)
        return OAuthToken(
            access_token=token, token_type="Bearer",
            expires_in=TOKEN_TTL, refresh_token=refresh,
            scope=" ".join(authorization_code.scopes),
        )

    # 갱신 토큰이 이 클라이언트 것이 맞는지 봅니다
    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        rt = self._refresh.get(refresh_token)
        return rt if rt and rt.client_id == client.client_id else None

    # 갱신 토큰으로 새 접근 토큰을 냅니다. 갱신 토큰도 새것으로 바꿉니다
    async def exchange_refresh_token(
        self, client: OAuthClientInformationFull,
        refresh_token: RefreshToken, scopes: list[str],
    ) -> OAuthToken:
        user, _ = self._issued.get(refresh_token.token, (None, None))
        self._refresh.pop(refresh_token.token, None)       # 쓴 갱신 토큰은 버립니다
        token = issue_token(user, ttl=TOKEN_TTL, resource=self._resource)
        self._issued[token] = (user, client.client_id)
        new_refresh = secrets.token_urlsafe(32)
        self._refresh[new_refresh] = RefreshToken(
            token=new_refresh, client_id=client.client_id,
            scopes=scopes, expires_at=None,
        )
        self._issued[new_refresh] = (user, client.client_id)
        return OAuthToken(
            access_token=token, token_type="Bearer",
            expires_in=TOKEN_TTL, refresh_token=new_refresh, scope=" ".join(scopes),
        )

    # FastMCP가 토큰을 확인할 때 부릅니다. 검문소를 그대로 부르는 한 줄
    async def load_access_token(self, token: str) -> AccessToken | None:
        return await self.verify_token(token)

    async def verify_token(self, token: str) -> AccessToken | None:
        """4단계의 토큰 저장소를 그대로 씁니다."""
        row = token_info(token)                 # 없거나 취소·만료면 None
        if row is None:
            return None
        # None 도 통과시킵니다 - 4단계에서 손으로 발급한 토큰에는 쓸 서버가 안 적혀
        # 있습니다. 로그인도 앱 등록도 안 거친 관리자 발급 토큰이라 수명도 없습니다.
        if row["resource"] not in (None, self._resource):
            return None                         # 다른 서버에 발급된 토큰
        _, client_id = self._issued.get(token, (None, "unknown"))
        deadline = row["expires_at"]
        if deadline is not None:
            deadline = datetime.fromisoformat(deadline)
            if deadline.tzinfo is None:       # token_info 와 같은 기준으로 읽습니다
                deadline = deadline.replace(tzinfo=timezone.utc)
        return AccessToken(
            token=token,
            client_id=client_id,        # 어느 앱으로 들어왔나 (감사용)
            scopes=[],
            resource=row["resource"],   # 이 토큰을 쓸 수 있는 서버
            expires_at=int(deadline.timestamp()) if deadline else None,
            claims={"sub": row["user"]},  # 누구의 요청인가. 여기에 실어야 살아남습니다
        )

    # FastMCP가 요구하는 자리. 갱신 토큰만 지웁니다
    async def revoke_token(self, token) -> None:
        self._refresh.pop(getattr(token, "token", token), None)


auth = TodoOAuthProvider(base_url=BASE_URL)
mcp = FastMCP("todo", auth=auth)


# ---- 사용자 확인 -------------------------------------------

def current_user() -> str:
    """3단계에서 만든 그 함수. 안쪽만 또 바뀝니다."""
    token = get_access_token()
    if token is None:
        raise ValueError("인증이 필요합니다")
    return token.claims["sub"]    # client_id 가 아닙니다


# ---- 서비스 API 호출 - 이 장에서 새로 만드는 유일한 함수 -----

SERVICE_INTERNAL_URL = os.environ.get("SERVICE_INTERNAL_URL", "http://127.0.0.1:8001")
SERVICE_KEY = os.environ.get("SERVICE_KEY", "dev-internal-key")
if SERVICE_KEY == "dev-internal-key":              # 이 값은 책에 적혀 있습니다
    print("경고: SERVICE_KEY 가 기본값입니다. 로컬 실습에서만 쓰세요.", file=sys.stderr)


def call_service(method: str, path: str, user: str, **kwargs) -> httpx.Response:
    """내부 신뢰 경로. 서비스 간 비밀키로 우리를 증명하고, 누구를 대신하는지 헤더로 넘깁니다."""
    try:
        r = httpx.request(
            method, f"{SERVICE_INTERNAL_URL}{path}",
            headers={
                "X-Service-Key": SERVICE_KEY,     # 서비스끼리만 아는 비밀키
                "X-On-Behalf-Of": user,           # 누구를 대신하는가
            },
            timeout=5, **kwargs,
        )
    except httpx.HTTPError as e:
        raise ValueError(f"서비스에 닿지 못했습니다: {e.__class__.__name__}")
    if r.status_code >= 400:                  # 오류 응답을 성공 응답인 양 읽지 않게 먼저 거릅니다
        raise ValueError(f"서비스가 {r.status_code} 로 거절했습니다")
    return r


# ---- 도구 - 몸통만 바뀝니다 ---------------------------------

@mcp.tool
def add_todo(text: str) -> str:
    """내 할 일을 추가한다"""
    user = current_user()                                                # 그대로
    return call_service("POST", "/todos", user, json={"text": text}).json()["result"]


@mcp.tool
def list_todos() -> list[dict]:
    """내 할 일 목록을 반환한다"""
    user = current_user()                                                # 그대로
    return call_service("GET", "/todos", user).json()                    # 몸통만


@mcp.tool
def complete_todo(todo_id: int) -> str:
    """내 할 일을 완료 처리한다"""
    user = current_user()                                                # 그대로
    return call_service("POST", f"/todos/{todo_id}/complete", user).json()["result"]


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="http", host="0.0.0.0", port=port)
