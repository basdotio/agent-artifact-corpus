# bridge.py - 贾维斯 MCP 小智桥接器 (支持完整 MCP 协议)
import asyncio
import websockets
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-xiaozhi-bridge")

# 小智 MCP WebSocket 端点
XIAOZHI_MCP_URL = "wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjQyOTgwNCwiYWdlbnRJZCI6MTIzNjk2MSwiZW5kcG9pbnRJZCI6ImFnZW50XzEyMzY5NjEiLCJwdXJwb3NlIjoibWNwLWVuZHBvaW50IiwiaWF0IjoxNzczNDIzNTQxLCJleHAiOjE4MDQ5ODExNDF9.W9oecoRJfH87Zy9bFkodEK4l2VUbnn3uWcIIhEfu2DybszNc4i7gHXCFPdhTFXk4AWKnUBrRpdggxW2W4QwsXw"

# MCP 协议版本
MCP_PROTOCOL_VERSION = "2024-11-05"

class MCPXiaoZhiBridge:
    """
    MCP 小智桥接器 (支持完整 MCP 协议)
    - 连接到小智 MCP WebSocket 端点
    - 完成 MCP 初始化握手
    - 接收来自小智客户端的消息
    - 转发给 OpenClaw (贾维斯) 处理
    - 处理完成后通知用户
    """
    
    def __init__(self):
        self.ws = None
        self.connected = False
        self.initialized = False
        self.reconnect_delay = 5
        self.max_reconnect_delay = 60
        self.pending_requests: Dict[str, dict] = {}
        self.request_id_counter = 0
        
    async def connect(self):
        """连接到小智 MCP WebSocket"""
        while True:
            try:
                logger.info(f"正在连接小智 MCP...")
                
                async with websockets.connect(
                    XIAOZHI_MCP_URL,
                    ping_interval=30,
                    ping_timeout=10
                ) as websocket:
                    self.ws = websocket
                    self.connected = True
                    self.initialized = False
                    self.reconnect_delay = 5
                    
                    logger.info("✅ 已连接到小智 MCP 服务器")
                    
                    # 等待服务器发送 initialize 请求
                    async for message in websocket:
                        try:
                            await self.handle_message(message)
                        except Exception as e:
                            logger.error(f"处理消息错误：{e}")
                            
            except websockets.exceptions.ConnectionClosed:
                logger.warning("小智 MCP 连接已关闭")
            except Exception as e:
                logger.error(f"连接错误：{e}")
            finally:
                self.connected = False
                self.initialized = False
                self.ws = None
                
            logger.info(f"{self.reconnect_delay}秒后重连...")
            await asyncio.sleep(self.reconnect_delay)
            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
    
    def generate_id(self) -> int:
        """生成 JSON-RPC 请求 ID"""
        self.request_id_counter += 1
        return self.request_id_counter
    
    async def handle_message(self, message: str):
        """处理来自小智 MCP 服务器的消息"""
        try:
            data = json.loads(message)
            logger.info(f"收到消息：{json.dumps(data, ensure_ascii=False)[:200]}")
            
            # 检查是否是 JSON-RPC 消息
            if "jsonrpc" in data:
                await self.handle_jsonrpc_message(data)
            else:
                # 非 JSON-RPC 消息，按旧格式处理
                await self.handle_legacy_message(data)
                
        except json.JSONDecodeError:
            logger.error("无效的 JSON 消息")
        except Exception as e:
            logger.error(f"处理消息异常：{e}")
    
    async def handle_jsonrpc_message(self, data: dict):
        """处理 JSON-RPC 格式的消息"""
        method = data.get("method", "")
        msg_id = data.get("id")
        params = data.get("params", {})
        
        logger.info(f"JSON-RPC 方法：{method}, ID: {msg_id}")
        
        if method == "initialize":
            # MCP 初始化请求
            await self.handle_initialize(msg_id, params)
            
        elif method == "notifications/initialized":
            # 初始化完成通知
            logger.info("✅ MCP 初始化完成，可以开始处理请求")
            self.initialized = True
            
        elif method == "tools/list":
            # 工具列表请求
            await self.handle_tools_list(msg_id)
            
        elif method == "tools/call":
            # 工具调用请求
            await self.handle_tools_call(msg_id, params)
            
        elif method == "sampling/createMessage":
            # 采样请求（LLM 调用）
            await self.handle_sampling(msg_id, params)
            
        elif method == "ping":
            # Ping 请求
            await self.send_response(msg_id, {})
            
        else:
            logger.warning(f"未处理的 JSON-RPC 方法：{method}")
            await self.send_error(msg_id, -32601, f"Method not found: {method}")
    
    async def handle_initialize(self, msg_id: int, params: dict):
        """处理 MCP 初始化请求"""
        logger.info(f"收到初始化请求：{json.dumps(params, ensure_ascii=False)[:200]}")
        
        # 获取客户端信息
        client_info = params.get("clientInfo", {})
        client_name = client_info.get("name", "unknown")
        client_version = client_info.get("version", "unknown")
        protocol_version = params.get("protocolVersion", "unknown")
        
        logger.info(f"客户端：{client_name} v{client_version}, 协议版本：{protocol_version}")
        
        # 构建服务器能力
        server_capabilities = {
            "tools": {
                "listChanged": True
            },
            "logging": {},
            "prompts": {}
        }
        
        # 发送初始化响应
        response = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": server_capabilities,
                "serverInfo": {
                    "name": "jarvis-mcp-bridge",
                    "version": "1.0.0"
                }
            }
        }
        
        await self.send_json(response)
        logger.info("已发送初始化响应")
        
        # 发送 initialized 通知
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        await self.send_json(initialized_notification)
        logger.info("已发送 initialized 通知")
        
        self.initialized = True
        logger.info("✅ MCP 初始化完成")
    
    async def handle_tools_list(self, msg_id: int):
        """处理工具列表请求"""
        logger.info("收到工具列表请求")
        
        tools = [
            {
                "name": "ask_jarvis",
                "description": "向贾维斯提问，获取智能回答",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "要问的问题"
                        },
                        "context": {
                            "type": "object",
                            "description": "可选的上下文信息"
                        }
                    },
                    "required": ["question"]
                }
            },
            {
                "name": "execute_task",
                "description": "让贾维斯执行特定任务",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_description": {
                            "type": "string",
                            "description": "任务描述"
                        },
                        "parameters": {
                            "type": "object",
                            "description": "任务参数"
                        }
                    },
                    "required": ["task_description"]
                }
            },
            {
                "name": "get_status",
                "description": "获取贾维斯当前状态",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "process_intent",
                "description": "处理用户意图，异步执行并通知结果",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "description": "用户意图/指令"
                        },
                        "user_id": {
                            "type": "string",
                            "description": "用户 ID"
                        },
                        "callback_channel": {
                            "type": "string",
                            "description": "回调渠道 (telegram/qqbot/feishu/webchat)"
                        }
                    },
                    "required": ["intent", "user_id"]
                }
            }
        ]
        
        response = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": tools
            }
        }
        
        await self.send_json(response)
        logger.info(f"已返回工具列表：{len(tools)} 个工具")
    
    async def handle_tools_call(self, msg_id: int, params: dict):
        """处理工具调用请求"""
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})
        
        logger.info(f"工具调用：{tool_name}, 参数：{tool_args}")
        
        try:
            if tool_name == "ask_jarvis":
                result = await self.tool_ask_jarvis(tool_args)
            elif tool_name == "execute_task":
                result = await self.tool_execute_task(tool_args)
            elif tool_name == "get_status":
                result = await self.tool_get_status()
            elif tool_name == "process_intent":
                result = await self.tool_process_intent(tool_args)
            else:
                result = {
                    "content": [{"type": "text", "text": f"未知工具：{tool_name}"}],
                    "isError": True
                }
            
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": result
            }
            await self.send_json(response)
            logger.info(f"工具 {tool_name} 调用完成")
            
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": f"错误：{str(e)}"}],
                    "isError": True
                }
            }
            await self.send_json(error_response)
            logger.error(f"工具调用失败：{e}")
    
    async def handle_sampling(self, msg_id: int, params: dict):
        """处理采样请求（LLM 调用）"""
        logger.info(f"收到采样请求：{json.dumps(params, ensure_ascii=False)[:200]}")
        
        # 这里可以调用 OpenClaw 的 LLM 能力
        # 简化实现：返回一个示例响应
        response = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "role": "assistant",
                "content": {
                    "type": "text",
                    "text": "贾维斯已收到您的请求，正在处理中..."
                }
            }
        }
        
        await self.send_json(response)
        logger.info("已发送采样响应")
    
    async def handle_legacy_message(self, data: dict):
        """处理旧格式消息（非 JSON-RPC）"""
        msg_type = data.get("type", "unknown")
        
        if msg_type == "intent" or msg_type == "text":
            await self.handle_user_intent(data)
        elif msg_type == "query":
            await self.handle_user_query(data)
        elif msg_type == "pong":
            logger.debug("收到心跳响应")
        elif msg_type == "notification":
            logger.info(f"收到通知：{data}")
        else:
            logger.warning(f"未知消息类型：{msg_type}")
    
    # ==================== 工具实现 ====================
    
    async def tool_ask_jarvis(self, args: dict) -> dict:
        """ask_jarvis 工具实现"""
        question = args.get("question", "")
        context = args.get("context", {})
        
        logger.info(f"ask_jarvis: {question}")
        
        # 调用贾维斯处理
        response_text = await self.query_jarvis(question, context)
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": response_text
                }
            ],
            "isError": False
        }
    
    async def tool_execute_task(self, args: dict) -> dict:
        """execute_task 工具实现"""
        task_description = args.get("task_description", "")
        parameters = args.get("parameters", {})
        
        logger.info(f"execute_task: {task_description}")
        
        # 执行任务
        result = await self.forward_to_jarvis(
            str(uuid.uuid4())[:8],
            "mcp_client",
            task_description,
            parameters
        )
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, ensure_ascii=False, indent=2)
                }
            ],
            "isError": False
        }
    
    async def tool_get_status(self) -> dict:
        """get_status 工具实现"""
        status = {
            "name": "贾维斯",
            "status": "online",
            "version": "1.0.0",
            "initialized": self.initialized,
            "capabilities": [
                "自然语言理解",
                "任务执行",
                "信息查询",
                "工具调用"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(status, ensure_ascii=False, indent=2)
                }
            ],
            "isError": False
        }
    
    async def tool_process_intent(self, args: dict) -> dict:
        """process_intent 工具实现 - 异步处理意图"""
        intent = args.get("intent", "")
        user_id = args.get("user_id", "unknown")
        callback_channel = args.get("callback_channel", "webchat")
        
        request_id = str(uuid.uuid4())[:8]
        
        logger.info(f"process_intent [{request_id}]: {intent}")
        
        # 存储请求
        self.pending_requests[request_id] = {
            "request_id": request_id,
            "user_id": user_id,
            "intent": intent,
            "callback_channel": callback_channel,
            "status": "processing",
            "created_at": datetime.now().isoformat()
        }
        
        # 异步处理
        asyncio.create_task(
            self.process_intent_async(request_id, user_id, intent, callback_channel)
        )
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "status": "accepted",
                        "request_id": request_id,
                        "message": "意图已接收，正在后台处理中",
                        "estimated_seconds": 30
                    }, ensure_ascii=False, indent=2)
                }
            ],
            "isError": False
        }
    
    async def process_intent_async(self, request_id: str, user_id: str,
                                    intent: str, callback_channel: str):
        """异步处理意图"""
        try:
            result = await self.forward_to_jarvis(request_id, user_id, intent)
            self.pending_requests[request_id]["status"] = "completed"
            self.pending_requests[request_id]["result"] = result
            
            # 通知用户
            await self.notify_completion(request_id, result, user_id, callback_channel)
            
        except Exception as e:
            logger.error(f"[{request_id}] 处理失败：{e}")
            self.pending_requests[request_id]["status"] = "failed"
            self.pending_requests[request_id]["error"] = str(e)
            await self.notify_failure(request_id, str(e), user_id, callback_channel)
    
    async def forward_to_jarvis(self, request_id: str, user_id: str,
                                 intent: str, session_id: str = None) -> dict:
        """将意图转发给贾维斯处理"""
        logger.info(f"[{request_id}] 转发给贾维斯...")
        
        # 实际实现中这里会调用 OpenClaw 的 API
        # 简化实现：模拟处理
        result = {
            "request_id": request_id,
            "user_id": user_id,
            "intent": intent,
            "jarvis_response": f"贾维斯已处理：「{intent}」",
            "processed_at": datetime.now().isoformat(),
            "status": "success"
        }
        
        return result
    
    async def query_jarvis(self, question: str, context: dict = None) -> str:
        """向贾维斯查询"""
        # 实际实现中这里会调用 OpenClaw
        return f"贾维斯回答：{question}"
    
    async def notify_completion(self, request_id: str, result: dict,
                                 user_id: str, callback_channel: str):
        """通知用户任务完成"""
        notification = {
            "type": "notification",
            "request_id": request_id,
            "status": "completed",
            "data": {
                "message": "✅ 贾维斯已处理完成",
                "result": result.get("jarvis_response", "处理完成"),
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # 发送通知给 MCP 客户端
        if self.ws and self.connected:
            await self.send_json({
                "jsonrpc": "2.0",
                "method": "notifications/message",
                "params": {
                    "level": "info",
                    "data": notification
                }
            })
        
        logger.info(f"[{request_id}] 已通知用户完成")
    
    async def notify_failure(self, request_id: str, error: str,
                              user_id: str, callback_channel: str):
        """通知用户处理失败"""
        if self.ws and self.connected:
            await self.send_json({
                "jsonrpc": "2.0",
                "method": "notifications/message",
                "params": {
                    "level": "error",
                    "data": {
                        "request_id": request_id,
                        "error": error
                    }
                }
            })
    
    # ==================== 发送方法 ====================
    
    async def send_json(self, data: dict):
        """发送 JSON 消息"""
        if self.ws and self.connected:
            message = json.dumps(data, ensure_ascii=False)
            await self.ws.send(message)
            logger.debug(f"发送：{message[:200]}")
    
    async def send_response(self, msg_id: int, result: dict):
        """发送 JSON-RPC 响应"""
        response = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result
        }
        await self.send_json(response)
    
    async def send_error(self, msg_id: int, code: int, message: str):
        """发送 JSON-RPC 错误响应"""
        error = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": code,
                "message": message
            }
        }
        await self.send_json(error)


bridge = MCPXiaoZhiBridge()

async def main():
    logger.info("🤖 贾维斯 MCP 桥接器启动...")
    await bridge.connect()

if __name__ == "__main__":
    asyncio.run(main())
