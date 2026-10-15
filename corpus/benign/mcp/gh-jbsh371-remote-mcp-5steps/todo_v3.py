"""3단계 - 토큰으로 사용자 확인하기

바뀐 것: 토큰을 실을 수 있는 전송 방식(HTTP)으로 전환.
user 인자가 사라지고, 요청 헤더의 토큰에서 사용자를 알아냅니다.
"""

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
import json, os, pathlib

mcp = FastMCP("todo")
DB = pathlib.Path(__file__).parent / "todos.json"

# 교육용 고정 토큰 표 - 발급 절차 대신 토큰과 사용자 이름을 미리 적어 둡니다.
TOKENS = {"tok-kim-1234": "kim", "tok-lee-5678": "lee"}      # 새로 생긴 표


def _load():
    return json.loads(DB.read_text(encoding="utf-8")) if DB.exists() else []


def _save(todos):
    tmp = DB.with_suffix(".tmp")
    tmp.write_text(json.dumps(todos, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, DB)


def current_user() -> str:                                    # 새로 생긴 함수
    """요청 헤더의 토큰을 사용자 이름으로 바꿉니다. 실패하면 예외를 냅니다.

    사용자를 확인하는 지점은 이 함수 하나입니다.
    도구 안에서 get_http_headers()를 부르지 마세요.
    4·5단계에서 이 함수 안쪽만 바뀌고 도구는 그대로 남습니다.
    """
    # 기본값은 authorization 을 지웁니다. 명시적으로 요청해야 합니다.
    auth = get_http_headers(include={"authorization"}).get("authorization", "")
    scheme, _, value = auth.partition(" ")     # "Bearer <토큰>" 을 둘로 나눕니다
    if scheme.lower() != "bearer":             # 접두사가 없거나 다르면 여기서 끝
        raise ValueError("유효하지 않은 토큰")
    token = value.strip()
    if token not in TOKENS:
        raise ValueError("유효하지 않은 토큰")
    return TOKENS[token]


@mcp.tool
def add_todo(text: str) -> str:            # user 인자가 사라졌습니다
    """내 할 일을 추가한다"""
    user = current_user()                   # 사용자는 이제 토큰에서 나옵니다
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
    mcp.run(transport="http", host="127.0.0.1", port=8000)    # 바뀐 한 줄
