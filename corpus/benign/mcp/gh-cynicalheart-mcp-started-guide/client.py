"""
MCP客户端测试
"""

import asyncio
import os
from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.exceptions import ToolError

# 加载环境变量
load_dotenv()

APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
REQUEST_URL = os.getenv("REQUEST_URL")


client = Client("http://localhost:8080/mcp/sf")


async def call_tool(sf_code: str):
    try:
        async with client:
            # 测试连接
            res = await client.ping()
            await asyncio.to_thread(print, f"ping结果\n{res=}")
            # 列出所有工具、资源和提示词
            tools, resources, prompts = await asyncio.gather(
                client.list_tools(),
                client.list_resources(),
                client.list_prompts(),
                return_exceptions=True,  # 防止一个失败影响其他
            )
            await asyncio.to_thread(
                print,
                f"连接成功，工具列表: {tools}\n资源列表: {resources}\n提示词列表: {prompts}",
            )

            result = await client.call_tool(
                "sf_query_route",
                {
                    "appKey": APP_KEY,
                    "appSecret": APP_SECRET,
                    "sfCode": sf_code,
                    "phone": "0851",  # 修改成接收顺丰快递人员手机号后四位
                    "requestUrl": REQUEST_URL,
                },
            )
            await asyncio.to_thread(print, f"查询结果\n{result=}")
    except ToolError as e:
        await asyncio.to_thread(print, f"发生错误: {e}")
        import traceback

        await asyncio.to_thread(traceback.print_exc)


asyncio.run(call_tool("SF0267637989800"))
