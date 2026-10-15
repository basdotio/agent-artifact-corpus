# import os
# from mcp.server.fastmcp import FastMCP

# mcp = FastMCP()


# @mcp.tool()
# def get_downloads_files():
#     """获取下载文件夹下的文件列表"""
#     return os.listdir(os.path.expanduser("~/Downloads"))


# if __name__ == "__main__":
#     mcp.run(transport="stdio")


import os
import sys
import logging
from mcp.server.fastmcp import FastMCP

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/tmp/mcp_debug.log'
)
logger = logging.getLogger(__name__)

try:
    logger.debug("初始化 FastMCP")
    mcp = FastMCP()

    @mcp.tool()
    def get_downloads_files():
        """获取下载文件夹下的文件列表"""
        logger.debug("调用 get_downloads_files 函数")
        return os.listdir(os.path.expanduser("~/Downloads"))

    if __name__ == "__main__":
        logger.debug("开始运行 MCP 服务")
        mcp.run(transport="stdio")
except Exception as e:
    logger.error(f"发生错误: {e}", exc_info=True)
    sys.exit(1)    