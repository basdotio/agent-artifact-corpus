# test_client.py - 测试 MCP 客户端
import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test-client")

# 小智 MCP 端点
XIAOZHI_MCP_URL = "wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjQyOTgwNCwiYWdlbnRJZCI6MTIzNjk2MSwiZW5kcG9pbnRJZCI6ImFnZW50XzEyMzY5NjEiLCJwdXJwb3NlIjoibWNwLWVuZHBvaW50IiwiaWF0IjoxNzczNDIzNTQxLCJleHAiOjE4MDQ5ODExNDF9.W9oecoRJfH87Zy9bFkodEK4l2VUbnn3uWcIIhEfu2DybszNc4i7gHXCFPdhTFXk4AWKnUBrRpdggxW2W4QwsXw"

async def test_connection():
    """测试连接"""
    logger.info("🧪 测试 MCP 连接...")
    
    try:
        async with websockets.connect(XIAOZHI_MCP_URL) as ws:
            logger.info("✅ 已连接到 MCP 服务器")
            
            # 测试 1: 发送 ping
            logger.info("📤 发送心跳测试...")
            await ws.send(json.dumps({"type": "ping"}))
            
            # 等待响应
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                logger.info(f"📥 收到响应: {response}")
            except asyncio.TimeoutError:
                logger.warning("⏱️ 等待响应超时")
            
            # 测试 2: 发送用户意图
            logger.info("📤 发送用户意图测试...")
            test_intent = {
                "type": "intent",
                "request_id": "test_001",
                "user_id": "test_user",
                "data": {
                    "intent": "你好，贾维斯！"
                }
            }
            await ws.send(json.dumps(test_intent))
            logger.info(f"📤 已发送: {test_intent}")
            
            # 等待响应
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=10.0)
                data = json.loads(response)
                logger.info(f"📥 收到响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
                if data.get("status") == "accepted":
                    logger.info("✅ 测试通过: 意图已被接受")
                else:
                    logger.warning(f"⚠️ 意外响应: {data}")
                    
            except asyncio.TimeoutError:
                logger.warning("⏱️ 等待响应超时")
            
            # 测试 3: 发送查询
            logger.info("📤 发送查询测试...")
            test_query = {
                "type": "query",
                "request_id": "test_002",
                "user_id": "test_user",
                "data": {
                    "question": "现在几点了？"
                }
            }
            await ws.send(json.dumps(test_query))
            logger.info(f"📤 已发送: {test_query}")
            
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=10.0)
                data = json.loads(response)
                logger.info(f"📥 收到响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
                if data.get("data", {}).get("status") == "success":
                    logger.info("✅ 测试通过: 查询成功")
                else:
                    logger.warning(f"⚠️ 意外响应: {data}")
                    
            except asyncio.TimeoutError:
                logger.warning("⏱️ 等待响应超时")
            
            logger.info("🎉 测试完成!")
            
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_connection())
