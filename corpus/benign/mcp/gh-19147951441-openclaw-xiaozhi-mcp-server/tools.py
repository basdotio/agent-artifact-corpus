# tools.py
"""
MCP 工具定义
小智客户端可以通过这些工具调用贾维斯的能力
"""

from mcp.server.fastmcp import FastMCP
import logging

logger = logging.getLogger("mcp-xiaozhi-tools")
mcp = FastMCP("贾维斯工具集")


@mcp.tool()
def ask_jarvis(question: str, context: dict = None) -> dict:
    """
    向贾维斯提问
    
    Args:
        question: 问题内容
        context: 可选的上下文信息
    
    Returns:
        贾维斯的回答
    """
    logger.info(f"收到问题: {question}")
    return {
        "success": True,
        "answer": "贾维斯正在思考...",
        "timestamp": "now"
    }


@mcp.tool()
def execute_task(task_description: str, parameters: dict = None) -> dict:
    """
    让贾维斯执行任务
    
    Args:
        task_description: 任务描述
        parameters: 任务参数
    
    Returns:
        任务执行结果
    """
    logger.info(f"执行任务: {task_description}")
    return {
        "success": True,
        "status": "completed",
        "result": "任务已完成"
    }


@mcp.tool()
def get_status() -> dict:
    """
    获取贾维斯状态
    
    Returns:
        当前状态信息
    """
    return {
        "name": "贾维斯",
        "status": "online",
        "version": "1.0.0",
        "capabilities": [
            "自然语言理解",
            "任务执行",
            "信息查询",
            "工具调用"
        ]
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
