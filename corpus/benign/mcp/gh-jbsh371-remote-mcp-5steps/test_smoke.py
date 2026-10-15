"""저장소 코드 점검 - 다섯 버전이 실제로 도는지 확인합니다.

    python test_smoke.py

fastmcp Client 로 in-memory 접속해 도구를 부릅니다.
5단계는 HTTP 로 띄워 OAuth 흐름 전체를 왕복합니다.
"""

import asyncio, hashlib, importlib, json, os, pathlib, re, shutil, sys, tempfile, time
from datetime import datetime, timedelta, timezone

WORK = pathlib.Path(tempfile.mkdtemp(prefix="todo-smoke-"))
os.environ["DATA_DIR"] = str(WORK)
sys.path.insert(0, str(pathlib.Path(__file__).parent))

OK, FAIL = [], []


def check(name, cond, detail=""):
    (OK if cond else FAIL).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{'  - ' + detail if detail else ''}")


def reset():
    """WORK 안만 지웁니다. 작업 디렉터리의 파일은 건드리지 않습니다."""
    for f in ("todos.json", "tokens.json"):
        (WORK / f).unlink(missing_ok=True)


async def stdio_stage(modname, calls):
    """v1·v2 - 인메모리 클라이언트로 도구 호출"""
    from fastmcp import Client
    mod = importlib.import_module(modname)
    mod.DB = WORK / "todos.json"      # v1~v3 은 스크립트 옆에 저장합니다. 임시 폴더로 돌립니다
    async with Client(mod.mcp) as c:
        out = []
        for tool, args in calls:
            r = await c.call_tool(tool, args)
            out.append(r.data if hasattr(r, "data") else r)
        return out


async def stdio_print_stage():
    """v1 - 진짜 stdio 전송으로 왕복. 도구 안의 stray print가 통신을 못 깨는지 본다.

    mcp 2.0의 stdio 전송은 fd 1을 빼돌려 stray 출력을 stderr로 보낸다 (2026-08-14 실측).
    구세대(mcp 1.x)는 보호가 없어 print가 통신선에 실린다. 다만 버퍼링과 클라이언트
    관용 때문에 증상이 즉시 안 나타날 수 있다 - 이 점검은 구세대에서도 통과할 수 있다.
    """
    from fastmcp import Client
    src = (pathlib.Path(__file__).parent / "todo_v1.py").read_text(encoding="utf-8")
    tgt = WORK / "todo_v1_print.py"
    tgt.write_text(
        src.replace('"""할 일을 추가한다"""\n',
                    '"""할 일을 추가한다"""\n    print("debug")\n', 1),
        encoding="utf-8")
    async with Client(tgt) as c:           # 경로를 주면 stdio로 띄웁니다
        r = await c.call_tool("add_todo", {"text": "stdio"})
        return r.data if hasattr(r, "data") else r


async def http_stage(modname, port, token_header):
    """v3·v4 - HTTP 로 띄우고 헤더에 토큰을 실어 호출"""
    from fastmcp import Client
    import fastmcp
    mod = importlib.import_module(modname)
    task = asyncio.create_task(
        mod.mcp.run_async(transport="http", host="127.0.0.1", port=port, show_banner=False)
    )
    await asyncio.sleep(2.5)
    try:
        results = {}
        for label, tok in token_header.items():
            try:
                # auth 에 문자열을 주면 Authorization: Bearer <값> 으로 실립니다
                async with Client(f"http://127.0.0.1:{port}/mcp", auth=tok) as c:
                    r = await c.call_tool("list_todos", {})
                    results[label] = r.data if hasattr(r, "data") else r
            except Exception as e:
                results[label] = f"ERROR: {type(e).__name__}: {e}"[:90]
        return results
    finally:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


def _here_digest():
    """저장소 폴더의 실습 데이터 해시. 테스트가 건드리면 안 되는 파일들입니다."""
    here = pathlib.Path(__file__).parent
    return {n: (hashlib.sha256((here / n).read_bytes()).hexdigest()
                if (here / n).exists() else None)
            for n in ("todos.json", "tokens.json")}


def main():
    print(f"작업 디렉토리: {WORK}\n")

    before = _here_digest()

    # ---- 1단계 --------------------------------------------
    print("1단계 - stdio, 사용자 없음")
    reset()
    r = asyncio.run(stdio_stage("todo_v1", [
        ("add_todo", {"text": "우유 사기"}),
        ("add_todo", {"text": "보고서 쓰기"}),
        ("list_todos", {}),
    ]))
    check("도구 3개 등록·호출", "추가됨" in str(r[0]))
    check("목록에 2건", len(r[2]) == 2, str(r[2]))
    check("주인이 없다 (구멍)", all("user" not in t for t in r[2]))

    reset()
    out = asyncio.run(stdio_print_stage())
    check("stdio 왕복 + stray print 무해", "추가됨" in str(out), str(out))
    print()

    # ---- 2단계 --------------------------------------------
    print("2단계 - user 필드, 자기 신고")
    reset()
    r = asyncio.run(stdio_stage("todo_v2", [
        ("add_todo", {"text": "우유 사기", "user": "kim"}),
        ("add_todo", {"text": "보고서 쓰기", "user": "lee"}),
        ("list_todos", {"user": "kim"}),
        ("add_todo", {"text": "청소하기", "user": "lee"}),   # 남인 척
        ("list_todos", {"user": "lee"}),
    ]))
    check("데이터 분리 동작", len(r[2]) == 1 and r[2][0]["user"] == "kim", str(r[2]))
    check("거짓 신고가 통한다 (구멍)", len(r[4]) == 2, str(len(r[4])))
    print()

    # ---- 3단계 --------------------------------------------
    print("3단계 - HTTP + 헤더 토큰")
    reset()
    import todo_v3
    todo_v3.DB = WORK / "todos.json"
    res = asyncio.run(http_stage("todo_v3", 8931, {
        "kim": "tok-kim-1234", "lee": "tok-lee-5678", "가짜": "tok-park-9999",
    }))
    check("kim 토큰으로 접속", not str(res["kim"]).startswith("ERROR"), str(res["kim"]))
    check("lee 토큰으로 접속", not str(res["lee"]).startswith("ERROR"), str(res["lee"]))
    check("모르는 토큰은 거부", str(res["가짜"]).startswith("ERROR"), str(res["가짜"]))
    print()

    # ---- 4단계 --------------------------------------------
    print("4단계 - 파일 토큰 저장소 + 발급")
    reset()
    from issue_token import issue_token, resolve_token
    t_kim = issue_token("kim")
    check("발급된 토큰 형식", t_kim.startswith("tok-kim-"), t_kim[:20] + "...")
    check("해시만 저장", t_kim not in (WORK / "tokens.json").read_text(encoding="utf-8"))
    check("조회 성공", resolve_token(t_kim) == "kim")
    check("모르는 토큰은 None", resolve_token("tok-없음") is None)
    rows = json.loads((WORK / "tokens.json").read_text(encoding="utf-8"))
    rows[0]["revoked"] = True
    (WORK / "tokens.json").write_text(json.dumps(rows), encoding="utf-8")
    check("취소하면 죽는다", resolve_token(t_kim) is None)
    rows[0]["revoked"] = False
    (WORK / "tokens.json").write_text(json.dumps(rows), encoding="utf-8")

    res = asyncio.run(http_stage("todo_v4", 8932, {"kim": t_kim, "가짜": "tok-없음"}))
    check("발급 토큰으로 접속", not str(res["kim"]).startswith("ERROR"), str(res["kim"]))
    check("모르는 토큰은 거부", str(res["가짜"]).startswith("ERROR"))
    print()

    # ---- 5단계 --------------------------------------------
    print("5단계 - OAuth")
    reset()
    ok = asyncio.run(oauth_stage(8933))
    print()

    # ---- 경계 - 거절해야 할 것을 거절하는가 ------------------
    print("경계 - 만료·사용 대상·로그인 거래 기한")
    reset()
    boundary_stage()
    check("실습 데이터 파일을 건드리지 않았다", _here_digest() == before)
    print()

    import todo_v5
    if todo_v5.TOKEN_TTL != 3600:
        print(f"  주의  todo_v5.TOKEN_TTL 이 {todo_v5.TOKEN_TTL} 입니다. "
              f"실측용으로 줄이신 거라면 출시 전에 3600 으로 되돌리세요 (원고는 3600 입니다)")
        print()

    print("-" * 50)
    print(f"통과 {len(OK)}  실패 {len(FAIL)}")
    if FAIL:
        print("실패:", ", ".join(FAIL))
    shutil.rmtree(WORK, ignore_errors=True)
    return 1 if FAIL else 0


_DROP = object()          # rewrite() 에서 "이 키를 아예 빼라"는 표시


def boundary_stage():
    """토큰의 수명과 사용 대상, 로그인 거래 기한을 확인합니다.

    HTTP 왕복 없이 저장소와 제공자를 직접 부릅니다.
    """
    from datetime import datetime, timedelta, timezone
    import todo_v5
    from issue_token import issue_token, token_info

    auth = todo_v5.TodoOAuthProvider(base_url=todo_v5.BASE_URL)
    store = WORK / "tokens.json"

    def age_out(token):
        """그 토큰 행의 만료 시각을 과거로 돌립니다."""
        digest = hashlib.sha256(token.encode()).hexdigest()
        rows = json.loads(store.read_text(encoding="utf-8"))
        past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        for row in rows:
            if row["token_hash"] == digest:
                row["expires_at"] = past
        store.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

    # 수명
    live = issue_token("kim", ttl=3600, resource=auth._resource)
    check("수명이 남은 토큰은 통한다", token_info(live) is not None)
    age_out(live)
    check("수명이 다한 토큰은 거절한다", token_info(live) is None)
    check("4단계 수동 발급은 만료가 없다",
          token_info(issue_token("kim"))["expires_at"] is None)

    # 사용 대상
    mine = issue_token("kim", ttl=3600, resource=auth._resource)
    other = issue_token("kim", ttl=3600, resource="https://다른서버.example/mcp")
    got = asyncio.run(auth.verify_token(mine))
    check("이 서버의 토큰은 통과한다", got is not None)
    check("만료 시각이 토큰에 실린다", got is not None and got.expires_at is not None)
    check("다른 서버의 토큰은 거절한다", asyncio.run(auth.verify_token(other)) is None)

    # 잘못된 입력과 옛 형식 - 거절하는 자리는 token_info() 하나입니다
    try:
        issue_token("kim", ttl=0)
        check("ttl=0 은 발급을 거절한다", False, "예외가 안 났습니다")
    except ValueError:
        check("ttl=0 은 발급을 거절한다", True)

    def rewrite(token, **fields):
        """그 토큰 행을 손으로 고칩니다. 독자가 tokens.json 을 여는 것과 같습니다."""
        digest = hashlib.sha256(token.encode()).hexdigest()
        rows = json.loads(store.read_text(encoding="utf-8"))
        for row in rows:
            if row["token_hash"] == digest:
                for k, v in fields.items():
                    if v is _DROP:
                        row.pop(k, None)
                    else:
                        row[k] = v
        store.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

    bad = issue_token("kim", ttl=3600, resource=auth._resource)
    rewrite(bad, expires_at="2020-01-01")            # 시간대 없는 과거
    check("시간대 없는 과거 시각은 만료로 거절한다", token_info(bad) is None)
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).replace(tzinfo=None)
    rewrite(bad, expires_at=future.isoformat())       # 시간대 없는 미래
    row = token_info(bad)
    check("시간대 없는 미래 시각은 UTC 로 보고 통과시킨다", row is not None)
    check("제공자도 같은 기준으로 읽는다",
          row is not None
          and (asyncio.run(auth.verify_token(bad)).expires_at
               == int(future.replace(tzinfo=timezone.utc).timestamp())))
    rewrite(bad, expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())
    check("시간대 있는 미래 시각은 통과시킨다", token_info(bad) is not None)
    rewrite(bad, expires_at="어제")                  # 읽을 수 없는 값
    check("읽을 수 없는 만료 시각은 거절한다", token_info(bad) is None)
    rewrite(bad, expires_at="")                      # 빈 값
    check("빈 만료 시각은 거절한다", token_info(bad) is None)

    old_row = issue_token("kim", ttl=3600, resource=auth._resource)
    rewrite(old_row, resource=_DROP, expires_at=_DROP)
    check("옛 형식 행은 거절한다", token_info(old_row) is None)

    # 로그인 거래 기한
    auth._pending["old"] = ("c", None, time.time() - todo_v5.PENDING_TTL - 1)
    auth._pending["new"] = ("c", None, time.time())
    auth._sweep_pending()
    check("기한 지난 로그인 거래는 걷힌다", "old" not in auth._pending)
    check("진행 중인 로그인 거래는 남는다", "new" in auth._pending)


async def oauth_stage(port):
    """5단계 - 등록·인가·로그인·코드교환·도구호출 전 과정"""
    import httpx, base64, hashlib as hl, secrets as sec
    os.environ["BASE_URL"] = f"http://127.0.0.1:{port}"
    import todo_v5
    importlib.reload(todo_v5)
    todo_v5.DB = WORK / "todos.json"

    task = asyncio.create_task(
        todo_v5.mcp.run_async(transport="http", host="127.0.0.1", port=port, show_banner=False)
    )
    await asyncio.sleep(2.5)
    base = f"http://127.0.0.1:{port}"
    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=10) as h:
            # 메타데이터
            m = await h.get(f"{base}/.well-known/oauth-authorization-server")
            check("메타데이터 공개", m.status_code == 200, f"HTTP {m.status_code}")
            meta = m.json() if m.status_code == 200 else {}
            check("PKCE S256 광고", "S256" in meta.get("code_challenge_methods_supported", []),
                  str(meta.get("code_challenge_methods_supported")))
            check("새 등록 방식 광고", meta.get("client_id_metadata_document_supported") is True
                  and "private_key_jwt" in meta.get("token_endpoint_auth_methods_supported", []),
                  f"cimd={meta.get('client_id_metadata_document_supported')} "
                  f"auth={meta.get('token_endpoint_auth_methods_supported')}")

            # 클라이언트 등록
            reg = await h.post(f"{base}/register", json={
                "client_name": "테스트", "redirect_uris": ["http://localhost:9999/cb"],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"], "token_endpoint_auth_method": "none",
            })
            check("클라이언트 등록", reg.status_code in (200, 201), f"HTTP {reg.status_code}")
            cid = reg.json().get("client_id") if reg.status_code in (200, 201) else None

            # 인가 요청 → 로그인 화면으로 가야 합니다
            ver = sec.token_urlsafe(32)
            chal = base64.urlsafe_b64encode(hl.sha256(ver.encode()).digest()).decode().rstrip("=")
            a = await h.get(f"{base}/authorize", params={
                "client_id": cid, "redirect_uri": "http://localhost:9999/cb",
                "response_type": "code", "code_challenge": chal,
                "code_challenge_method": "S256", "state": "xyz",
            })
            loc = a.headers.get("location", "")
            check("코드를 바로 안 준다", "code=" not in loc, loc[:60])
            check("로그인 화면으로 보낸다", "/login" in loc, loc[:60])

            txn = re.search(r"txn=([\w\-]+)", loc)
            txn = txn.group(1) if txn else None

            # 틀린 비밀번호
            bad = await h.post(f"{base}/login", data={
                "txn": txn, "username": "kim", "password": "틀림"})
            check("틀린 비밀번호는 거부", bad.status_code == 401, f"HTTP {bad.status_code}")

            # 맞는 비밀번호
            good = await h.post(f"{base}/login", data={
                "txn": txn, "username": "kim", "password": "kim-pw"})
            cb = good.headers.get("location", "")
            check("로그인하면 코드 발급", "code=" in cb, cb[:60])
            check("state 를 돌려준다", "state=xyz" in cb)
            code = re.search(r"code=([^&]+)", cb).group(1)

            # 코드 → 토큰
            tk = await h.post(f"{base}/token", data={
                "grant_type": "authorization_code", "code": code,
                "redirect_uri": "http://localhost:9999/cb",
                "client_id": cid, "code_verifier": ver,
            }, headers={"Content-Type": "application/x-www-form-urlencoded"})
            check("코드를 토큰으로 교환", tk.status_code == 200, f"HTTP {tk.status_code} {tk.text[:80]}")
            access = tk.json().get("access_token") if tk.status_code == 200 else None
            check("발급 토큰이 4단계 형식", bool(access) and access.startswith("tok-kim-"),
                  (access or "")[:20])
            adv = tk.json().get("expires_in") if tk.status_code == 200 else None
            check("광고한 수명이 실제 수명과 같다", adv == todo_v5.TOKEN_TTL,
                  f"expires_in={adv} TOKEN_TTL={todo_v5.TOKEN_TTL}")

            # 같은 코드 재사용은 막혀야 합니다
            again = await h.post(f"{base}/token", data={
                "grant_type": "authorization_code", "code": code,
                "redirect_uri": "http://localhost:9999/cb",
                "client_id": cid, "code_verifier": ver,
            })
            check("코드 재사용 차단", again.status_code != 200, f"HTTP {again.status_code}")

        # 토큰으로 도구 호출
        from fastmcp import Client
        async with Client(f"{base}/mcp", auth=access) as c:
            await c.call_tool("add_todo", {"text": "우유 사기"})
            r = await c.call_tool("list_todos", {})
            data = r.data if hasattr(r, "data") else r
        check("토큰으로 도구 호출", len(data) == 1, str(data))
        check("사용자가 claims 에서 나온다", data and data[0]["user"] == "kim", str(data))

        # 다른 사람은 자기 것만
        async with httpx.AsyncClient(follow_redirects=False, timeout=10) as h:
            reg = await h.post(f"{base}/register", json={
                "client_name": "테스트2", "redirect_uris": ["http://localhost:9999/cb"],
                "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"],
                "token_endpoint_auth_method": "none"})
            cid2 = reg.json()["client_id"]
            ver2 = sec.token_urlsafe(32)
            ch2 = base64.urlsafe_b64encode(hl.sha256(ver2.encode()).digest()).decode().rstrip("=")
            a = await h.get(f"{base}/authorize", params={
                "client_id": cid2, "redirect_uri": "http://localhost:9999/cb",
                "response_type": "code", "code_challenge": ch2,
                "code_challenge_method": "S256", "state": "s2"})
            txn2 = re.search(r"txn=([\w\-]+)", a.headers["location"]).group(1)
            g = await h.post(f"{base}/login", data={
                "txn": txn2, "username": "lee", "password": "lee-pw"})
            code2 = re.search(r"code=([^&]+)", g.headers["location"]).group(1)
            tk2 = await h.post(f"{base}/token", data={
                "grant_type": "authorization_code", "code": code2,
                "redirect_uri": "http://localhost:9999/cb",
                "client_id": cid2, "code_verifier": ver2})
            acc2 = tk2.json()["access_token"]

        async with Client(f"{base}/mcp", auth=acc2) as c:
            r = await c.call_tool("list_todos", {})
            d2 = r.data if hasattr(r, "data") else r
        check("각자 자기 데이터만 (클라이맥스)", len(d2) == 0, f"lee 목록 {len(d2)}건")
        check("client_id 는 서로 다른 앱", cid != cid2)

        # 같은 앱(client_id)으로 두 사람이 들어와도 갈리는가.
        # claude.ai 는 모든 고객이 같은 client_id 로 붙으므로 이쪽이 실제 조건입니다.
        async with httpx.AsyncClient(follow_redirects=False, timeout=10) as h:
            async def login_as(user):
                v = sec.token_urlsafe(32)
                c = base64.urlsafe_b64encode(hl.sha256(v.encode()).digest()).decode().rstrip("=")
                a = await h.get(f"{base}/authorize", params={
                    "client_id": cid, "redirect_uri": "http://localhost:9999/cb",
                    "response_type": "code", "code_challenge": c,
                    "code_challenge_method": "S256", "state": "same"})
                txn = re.search(r"txn=([\w\-]+)", a.headers["location"]).group(1)
                g = await h.post(f"{base}/login", data={
                    "txn": txn, "username": user, "password": user + "-pw"})
                code = re.search(r"code=([^&]+)", g.headers["location"]).group(1)
                tk = await h.post(f"{base}/token", data={
                    "grant_type": "authorization_code", "code": code,
                    "redirect_uri": "http://localhost:9999/cb",
                    "client_id": cid, "code_verifier": v})
                return tk.json()["access_token"]

            same_kim = await login_as("kim")
            same_lee = await login_as("lee")

        async def todos_of(tok):
            async with Client(f"{base}/mcp", auth=tok) as c:
                r = await c.call_tool("list_todos", {})
                return r.data if hasattr(r, "data") else r

        k = await todos_of(same_kim)
        l = await todos_of(same_lee)
        check("같은 client_id 로 붙어도 두 사람이 갈린다",
              len(k) == 1 and k[0]["user"] == "kim" and len(l) == 0,
              f"kim {len(k)}건 lee {len(l)}건")

        # 남의 항목을 완료 처리하려 하면 막히는가
        async with Client(f"{base}/mcp", auth=same_lee) as c:
            r = await c.call_tool("complete_todo", {"todo_id": k[0]["id"]})
            out = r.data if hasattr(r, "data") else r
        check("남의 항목은 완료 처리도 안 된다", "해당 id 없음" in str(out), str(out)[:60])
        after = await todos_of(same_kim)
        check("남의 완료 시도 뒤에도 원본이 그대로", after and after[0]["done"] is False, str(after)[:70])

    finally:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


if __name__ == "__main__":
    sys.exit(main())
