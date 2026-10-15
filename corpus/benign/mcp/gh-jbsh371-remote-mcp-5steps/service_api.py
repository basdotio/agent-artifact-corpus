"""최종 장 - "여러분의 서비스 API" 자리에 서는 작은 서버입니다.

실제로는 여러분 회사의 기존 API가 여기 섭니다. 이 파일은 그 자리를 흉내 내어
내부 신뢰 경로(서비스 간 비밀키 + 대신하는 사용자 헤더)를 눈으로 보게 합니다.
MCP와 무관한 평범한 HTTP API입니다.

    (.venv) $ python service_api.py        # http://127.0.0.1:8001
"""
import json, os, pathlib
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

DB = pathlib.Path(__file__).parent / "todos.json"
SERVICE_KEY = os.environ.get("SERVICE_KEY", "dev-internal-key")   # 서비스 간 비밀


def _load():
    return json.loads(DB.read_text(encoding="utf-8")) if DB.exists() else []


def _save(todos):
    tmp = DB.with_suffix(".tmp")
    tmp.write_text(json.dumps(todos, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, DB)


def who(request: Request) -> str | None:
    """내부 경로 판정. 이 판정이 생명선입니다."""
    if request.headers.get("x-service-key") != SERVICE_KEY:
        return None                                        # 공개 경로 - 여기서는 열지 않습니다
    user = request.headers.get("x-on-behalf-of", "")       # 검증 없이 믿습니다
    print(f"{request.method} {request.url.path}  by: mcp-server  on-behalf-of: {user}")  # 감사 로그 자리
    return user or None


async def list_todos(request: Request):
    user = who(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return JSONResponse([t for t in _load() if t["user"] == user])


async def add_todo(request: Request):
    user = who(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    text = (await request.json()).get("text", "")
    todos = _load()
    todos.append({"id": len(todos) + 1, "user": user, "text": text, "done": False})
    _save(todos)
    return JSONResponse({"result": f"[{user}] 추가됨: {text}"})


async def complete_todo(request: Request):
    user = who(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    todo_id = int(request.path_params["todo_id"])
    todos = _load()
    for t in todos:
        if t["id"] == todo_id and t["user"] == user:
            t["done"] = True
            _save(todos)
            return JSONResponse({"result": f"[{user}] 완료: {t['text']}"})
    return JSONResponse({"result": "해당 id 없음"})


app = Starlette(routes=[
    Route("/todos", list_todos, methods=["GET"]),
    Route("/todos", add_todo, methods=["POST"]),
    Route("/todos/{todo_id}/complete", complete_todo, methods=["POST"]),
])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
