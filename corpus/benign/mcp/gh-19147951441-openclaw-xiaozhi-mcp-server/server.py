#!/usr/bin/env python3
from mcp.server.fastmcp import FastMCP
import asyncio
import logging
import json
from openclaw_client import openclaw_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('openclaw_mcp')

# 创建 MCP 服务器
mcp = FastMCP("OpenClaw")

# 存储任务状态
task_results = {}

@mcp.tool()
async def process_intent(intent: str, context: dict = None) -> dict:
    """
    将用户意图发送给 OpenClaw 处理。
    
    流程：
    1. 立即返回"处理中"状态
    2. 异步发送给 OpenClaw
    3. OpenClaw 完成后通过 callback 返回结果
    
    Args:
        intent: 用户的意图或请求内容
        context: 可选的上下文信息
    
    Returns:
        {"status": "processing", "task_id": "xxx", "message": "..."}
    """
    try:
        # 确保连接
        if not openclaw_client.connected:
            await openclaw_client.connect()
        
        # 发送意图
        task_id = await openclaw_client.send_intent(intent, context)
        
        # 注册回调（异步等待结果）
        async def on_complete(result):
            task_results[task_id] = result
            logger.info(f"✅ 任务 {task_id} 完成：{result}")
        
        openclaw_client.register_callback(task_id, on_complete)
        
        # 立即返回处理中状态
        response = {
            "status": "processing",
            "task_id": task_id,
            "message": "意图已接收，正在处理中...",
            "intent_preview": intent[:100] + "..." if len(intent) > 100 else intent
        }
        
        logger.info(f"📥 接收意图：{intent[:50]}... -> 任务 ID: {task_id}")
        return response
        
    except Exception as e:
        logger.error(f"❌ 处理错误：{e}")
        return {
            "status": "error",
            "error": str(e),
            "intent_preview": intent[:100]
        }

@mcp.tool()
async def get_task_result(task_id: str) -> dict:
    """
    查询任务处理结果。
    
    Args:
        task_id: 任务 ID（由 process_intent 返回）
    
    Returns:
        {"status": "completed", "result": ...} 或 {"status": "processing"}
    """
    if task_id in task_results:
        return {
            "status": "completed",
            "result": task_results[task_id]
        }
    return {
        "status": "processing",
        "message": "任务仍在处理中，请稍后查询"
    }

if __name__ == "__main__":
    logger.info("🚀 OpenClaw MCP Server 启动...")
    
    # 预连接 WebSocket
    try:
        asyncio.get_event_loop().run_until_complete(openclaw_client.connect())
    except Exception as e:
        logger.error(f"❌ 预连接失败：{e}")
        logger.info("⚠️ 将在首次请求时尝试连接")
    
    # 启动 MCP 服务器
    mcp.run(transport="stdio")
