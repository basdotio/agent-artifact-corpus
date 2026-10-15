"""3단계 점검 스크립트 - Inspector 없이 실습 2~4를 재현합니다."""
import asyncio, os, sys
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

URL = os.environ.get("MCP_URL", "http://127.0.0.1:8000/mcp")


def label(token: str) -> str:
    """화면에 남길 이름입니다. 토큰 원문은 찍지 않습니다 - 4단계 토큰은 진짜 열쇠입니다."""
    head = "-".join(token.split("-")[:2])                        # tok-kim
    return f"{head}-… ({len(token)}자)"


async def check(token: str):
    who = label(token)
    transport = StreamableHttpTransport(URL, headers={"Authorization": f"Bearer {token}"})
    async with Client(transport) as client:                      # 연결과 규약 협의는 여기서 자동
        tools = await client.list_tools()
        print(f"[{who}] 연결됨 - 도구: {[t.name for t in tools]}")
        try:
            result = await client.call_tool("list_todos", {})
            print(f"[{who}] list_todos → {result.data}")
        except Exception as e:                                    # 무효 토큰이면 여기로 옵니다
            print(f"[{who}] list_todos → {e}")


tokens = sys.argv[1:] or ["tok-kim-1234", "tok-lee-5678", "tok-park-9999"]
for t in tokens:
    asyncio.run(check(t))
