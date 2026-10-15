"""2단계 - 데이터에 주인 붙이기

바뀐 것: 데이터 모델에 user 필드. 도구가 user 인자를 받습니다.
사용자를 확인하지는 않습니다. 호출하는 쪽 말을 그대로 믿습니다.
"""

from fastmcp import FastMCP
import json, os, pathlib

mcp = FastMCP("todo")
DB = pathlib.Path(__file__).parent / "todos.json"


def _load():
    return json.loads(DB.read_text(encoding="utf-8")) if DB.exists() else []


def _save(todos):
    tmp = DB.with_suffix(".tmp")
    tmp.write_text(json.dumps(todos, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, DB)


@mcp.tool
def add_todo(text: str, user: str) -> str:          # user 인자가 생겼습니다
    """user의 할 일을 추가한다"""
    todos = _load()
    todos.append({"id": len(todos) + 1, "user": user, "text": text, "done": False})   # 데이터에 user가 붙습니다
    _save(todos)
    return f"[{user}] 추가됨: {text}"


@mcp.tool
def list_todos(user: str) -> list[dict]:
    """user의 할 일 목록만 반환한다"""
    return [t for t in _load() if t["user"] == user]   # 데이터 분리의 탄생


@mcp.tool
def complete_todo(todo_id: int, user: str) -> str:
    """user의 할 일을 완료 처리한다"""
    todos = _load()
    for t in todos:
        if t["id"] == todo_id and t["user"] == user:   # 주인이 user와 같은 행만 바꿉니다
            t["done"] = True
            _save(todos)
            return f"[{user}] 완료: {t['text']}"
    return "해당 id 없음"


if __name__ == "__main__":
    mcp.run()
