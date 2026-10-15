# test_mcp_full.py - 完整 MCP 协议测试
import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-test")

XIAOZHI_MCP_URL = "wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjQyOTgwNCwiYWdlbnRJZCI6MTIzNjk2MSwiZW5kcG9pbnRJZCI6ImFnZW50XzEyMzY5NjEiLCJwdXJwb3NlIjoibWNwLWVuZHBvaW50IiwiaWF0IjoxNzczNDIzNTQxLCJleHAiOjE4MDQ5ODExNDF9.W9oecoRJfH87Zy9bFkodEK4l2VUbnn3uWcIIhEfu2DybszNc4i7gHXCFPdhTFXk4AWKnUBrRpdggxW2W4QwsXw"

class MCPTestClient:
    def __init__(self):
        self.ws = None
        self.request_id = 0
        self.initialized = False
    
    def next_id(self):
        self.request_id += 1
        return self.request_id
    
    async def connect(self):
        logger.info("🔌 连接到 MCP 服务器...")
        self.ws = await websockets.connect(XIAOZHI_MCP_URL)
        logger.info("✅ 已连接")
    
    async def initialize(self):
        """MCP 初始化握手"""
        logger.info("📋 开始 MCP 初始化握手...")
        
        # 等待服务器的 initialize 请求
        msg = await self.ws.recv()
        data = json.loads(msg)
        logger.info(f"收到：{data.get('method')}")
        
        if data.get('method') == 'initialize':
            # 发送初始化响应
            response = {
                "jsonrpc": "2.0",
                "id": data.get('id'),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "logging": {},
                        "prompts": {}
                    },
                    "serverInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                }
            }
            await self.ws.send(json.dumps(response))
            logger.info("✅ 已发送初始化响应")
            
            # 等待 initialized 通知
            msg = await self.ws.recv()
            data = json.loads(msg)
            if data.get('method') == 'notifications/initialized':
                self.initialized = True
                logger.info("✅ MCP 初始化完成")
    
    async def list_tools(self):
        """获取工具列表"""
        logger.info("🔧 获取工具列表...")
        
        request = {
            "jsonrpc": "2.0",
            "id": self.next_id(),
            "method": "tools/list",
            "params": {}
        }
        await self.ws.send(json.dumps(request))
        
        msg = await self.ws.recv()
        data = json.loads(msg)
        
        tools = data.get('result', {}).get('tools', [])
        logger.info(f"✅ 找到 {len(tools)} 个工具:")
        for tool in tools:
            logger.info(f"   - {tool['name']}: {tool.get('description', 'N/A')[:50]}")
        return tools
    
    async def call_tool(self, tool_name: str, args: dict = None):
        """调用工具"""
        logger.info(f"🔨 调用工具：{tool_name}")
        
        request = {
            "jsonrpc": "2.0",
            "id": self.next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": args or {}
            }
        }
        await self.ws.send(json.dumps(request))
        
        msg = await self.ws.recv()
        data = json.loads(msg)
        
        result = data.get('result', {})
        content = result.get('content', [])
        
        logger.info(f"✅ 工具返回:")
        for item in content:
            if item.get('type') == 'text':
                text = item.get('text', '')
                logger.info(f"   {text[:200]}{'...' if len(text) > 200 else ''}")
        
        return result
    
    async def test_all_tools(self):
        """测试所有工具"""
        logger.info("\n" + "="*50)
        logger.info("🧪 开始测试所有工具")
        logger.info("="*50 + "\n")
        
        # 测试 1: get_status
        logger.info("测试 1: get_status")
        await self.call_tool("get_status", {})
        await asyncio.sleep(1)
        
        # 测试 2: ask_jarvis
        logger.info("\n测试 2: ask_jarvis")
        await self.call_tool("ask_jarvis", {"question": "你好，今天天气怎么样？"})
        await asyncio.sleep(1)
        
        # 测试 3: execute_task
        logger.info("\n测试 3: execute_task")
        await self.call_tool("execute_task", {
            "task_description": "帮我写一个 Hello World 程序"
        })
        await asyncio.sleep(1)
        
        # 测试 4: process_intent
        logger.info("\n测试 4: process_intent")
        result = await self.call_tool("process_intent", {
            "intent": "帮我查一下明天的天气",
            "user_id": "test_user_001",
            "callback_channel": "webchat"
        })
        
        logger.info("\n" + "="*50)
        logger.info("🎉 所有工具测试完成!")
        logger.info("="*50)
    
    async def run(self):
        """运行完整测试"""
        try:
            await self.connect()
            await self.initialize()
            await self.list_tools()
            await self.test_all_tools()
            
        except Exception as e:
            logger.error(f"❌ 测试失败：{e}")
            raise
        finally:
            if self.ws:
                await self.ws.close()


async def main():
    client = MCPTestClient()
    await client.run()

if __name__ == "__main__":
    asyncio.run(main())
