import asyncio
import os
from fastmcp import Context, FastMCP
from typing import Annotated
from pydantic import Field
from dotenv import load_dotenv
from open_sdk_py import OpenPlatformClient

# 加载环境变量
load_dotenv()

main_mcp = FastMCP(name="云枢MCP服务器")
sf_mcp = FastMCP(name="顺丰MCP服务器")

# 服务器配置
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8080"))
# 使用MCP_PATH避免与系统PATH冲突
MCP_PATH = os.getenv("MCP_PATH", "/mcp")
if not MCP_PATH.startswith("/"):
    MCP_PATH = "/" + MCP_PATH


@sf_mcp.tool(
    name="query_route",
    description="通过云枢调用顺丰接口，获取顺丰的物流信息",
    tags={"open platform", "sf"},
    annotations={
        "title": "sf query route",
        "readOnlyHint": True,
        "openWorldHint": True,
    },
)
async def query_route(
    appKey: Annotated[str, Field(description="云枢的appKey")],
    appSecret: Annotated[str, Field(description="云枢的appSecret")],
    sfCode: Annotated[str, Field(description="顺丰的快递单号")],
    phone: Annotated[str, Field(description="快递接收方手机号信息")],
    ctx: Context,
    requestUrl: Annotated[str, Field(description="云枢顺丰接口请求地址")] = None,
) -> dict:
    """通过云枢调用顺丰接口，获取顺丰的物流信息"""
    await ctx.info(f"请求顺丰mcp接口，sfCode: {sfCode}, phone: {phone}")
    # 请求顺丰接口
    client = (
        OpenPlatformClient(appKey, appSecret, requestUrl)
        .set_request_data(
            {"trackingType": "1", "trackingNumber": [sfCode], "checkPhoneNo": phone}
        )
        .set_product_case("DEFAULT_JOINT-INNER_BINDINGS")
    )

    return client.send()


main_mcp.mount(sf_mcp, prefix="sf")


async def main():
    # 使用streamable-http启动
    await main_mcp.run_async(
        transport="streamable-http",
        host=HOST,
        port=PORT,
        path=MCP_PATH,
    )


if __name__ == "__main__":
    # mcp.run() 基础stdio启动
    asyncio.run(main())
