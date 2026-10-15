import asyncio
import json
import websockets
import logging
from typing import Optional, Callable
from config import OPENCLAW_WS_URL, OPENCLAW_TOKEN

logger = logging.getLogger("openclaw_client")

class OpenClawClient:
    def __init__(self):
        self.ws = None
        self.connected = False
        self.pending_tasks = {}
        self.message_counter = 0
        self.callbacks = {}
        
    async def connect(self):
        """连接 WebSocket"""
        url = f"{OPENCLAW_WS_URL}?token={OPENCLAW_TOKEN}"
        try:
            self.ws = await websockets.connect(url)
            self.connected = True
            logger.info("✅ OpenClaw WebSocket 已连接")
            
            # 启动接收循环
            asyncio.create_task(self._receive_loop())
        except Exception as e:
            logger.error(f"❌ 连接失败：{e}")
            raise
            
    async def _receive_loop(self):
        """持续接收消息"""
        try:
            async for message in self.ws:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("⚠️ WebSocket 连接已关闭")
            self.connected = False
        except Exception as e:
            logger.error(f"❌ 接收消息错误：{e}")
            
    async def _handle_message(self, message):
        """处理收到的消息"""
        try:
            data = json.loads(message)
            task_id = data.get("task_id")
            
            if task_id and task_id in self.callbacks:
                callback = self.callbacks[task_id]
                await callback(data)
                del self.callbacks[task_id]
                
        except json.JSONDecodeError:
            logger.error(f"❌ JSON 解析错误：{message}")
        except Exception as e:
            logger.error(f"❌ 处理消息错误：{e}")
            
    async def send_intent(self, intent: str, context: dict = None) -> str:
        """发送意图，返回 task_id"""
        if not self.connected:
            await self.connect()
            
        self.message_counter += 1
        task_id = f"task_{self.message_counter}"
        
        message = {
            "task_id": task_id,
            "type": "intent",
            "payload": {
                "intent": intent,
                "context": context or {},
                "timestamp": asyncio.get_event_loop().time()
            }
        }
        
        await self.ws.send(json.dumps(message))
        logger.info(f"📤 已发送意图：{intent[:50]}...")
        
        return task_id
        
    def register_callback(self, task_id: str, callback: Callable):
        """注册任务完成回调"""
        self.callbacks[task_id] = callback
        
    async def close(self):
        """关闭连接"""
        if self.ws:
            await self.ws.close()
            self.connected = False
            logger.info("🔌 WebSocket 连接已关闭")

# 全局客户端实例
openclaw_client = OpenClawClient()
