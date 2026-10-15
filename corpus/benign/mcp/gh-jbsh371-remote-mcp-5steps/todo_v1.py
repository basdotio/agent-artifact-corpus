"""1단계 - 말로 움직이는 서버 만들기

stdio 전송. 사용자 개념 없음.
"""

from fastmcp import FastMCP
import json, os, pathlib

mcp = FastMCP("todo")
# 서버가 어디서 뜰지 모르니 스크립트와 같은 폴더에 저장합니다
DB = pathlib.Path(__file__).parent / "todos.json"


def _load():
    return json.loads(DB.read_text(encoding="utf-8")) if DB.exists() else []


def _save(todos):
    # 원자적 쓰기 - 중간에 죽어도 반쪽짜리 파일이 남지 않습니다
    tmp = DB.with_suffix(".tmp")
    tmp.write_text(json.dumps(todos, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, DB)


@mcp.tool
def add_todo(text: str) -> str:
    """할 일을 추가한다"""
    todos = _load()
    todos.append({"id": len(todos) + 1, "text": text, "done": False})
    _save(todos)
    return f"추가됨: {text}"


@mcp.tool
def list_todos() -> list[dict]:
    """할 일 목록을 반환한다"""
    return _load()


@mcp.tool
def complete_todo(todo_id: int) -> str:
    """할 일을 완료 처리한다"""
    todos = _load()
    for t in todos:
        if t["id"] == todo_id:
            t["done"] = True
            _save(todos)
            return f"완료: {t['text']}"
    return "해당 id 없음"


if __name__ == "__main__":
    mcp.run()           # 인자가 없습니다. 기본값이 stdio입니다
