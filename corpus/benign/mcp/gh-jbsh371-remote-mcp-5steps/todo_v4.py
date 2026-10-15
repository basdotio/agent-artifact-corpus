"""4단계 - 서버를 인터넷에 내놓기

바뀐 것: 서버의 위치. current_user() 안쪽이 딕셔너리에서 파일 조회로.
도구 코드는 3단계와 한 글자도 다르지 않습니다.
"""

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
from issue_token import resolve_token          # 4단계 발급 스크립트와 짝입니다
import json, os, pathlib

mcp = FastMCP("todo")

DATA_DIR = pathlib.Path(os.environ.get("DATA_DIR", "."))
DB = DATA_DIR / "todos.json"


def _load():
    return json.loads(DB.read_text(encoding="utf-8")) if DB.exists() else []


def _save(todos):
    tmp = DB.with_suffix(".tmp")
    tmp.write_text(json.dumps(todos, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, DB)


def current_user() -> str:
    """요청 헤더의 토큰을 사용자 이름으로 바꿉니다. 실패하면 예외를 냅니다."""
    # 기본값은 authorization 을 지웁니다. 명시적으로 요청해야 합니다.
    auth = get_http_headers(include={"authorization"}).get("authorization", "")
    scheme, _, value = auth.partition(" ")     # "Bearer <토큰>" 을 둘로 나눕니다
    if scheme.lower() != "bearer":             # 접두사가 없거나 다르면 여기서 끝
        raise ValueError("유효하지 않은 토큰")
    token = value.strip()
    user = resolve_token(token)               # 여기부터 바뀝니다
    if user is None:
        raise ValueError("유효하지 않은 토큰")   # 이유를 구분해 알려주지 않습니다
    return user


@mcp.tool
def add_todo(text: str) -> str:
    """내 할 일을 추가한다"""
    user = current_user()
    todos = _load()
    todos.append({"id": len(todos) + 1, "user": user, "text": text, "done": False})
    _save(todos)
    return f"[{user}] 추가됨: {text}"


@mcp.tool
def list_todos() -> list[dict]:
    """내 할 일 목록을 반환한다"""
    user = current_user()
    return [t for t in _load() if t["user"] == user]


@mcp.tool
def complete_todo(todo_id: int) -> str:
    """내 할 일을 완료 처리한다"""
    user = current_user()
    todos = _load()
    for t in todos:
        if t["id"] == todo_id and t["user"] == user:
            t["done"] = True
            _save(todos)
            return f"[{user}] 완료: {t['text']}"
    return "해당 id 없음"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="http", host="0.0.0.0", port=port)       # 127.0.0.1 이 아닙니다
