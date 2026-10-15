"""MCP 工具定义文件"""
import mcp.types as types
from mcp.server import Server
from src.report.skills.registry import SkillRegistry

def register_tools(server: Server) -> None:
    """向 MCP 服务端注册工具"""
    
    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        """动态发现并列出所有 Skill 插件提供的工具"""
        SkillRegistry.auto_discover()
        all_tools = SkillRegistry.get_all_tools()
        
        mcp_tools_dict = {}
        for tool in all_tools:
            # 如果已经存在同名工具，则跳过（去重）
            if tool.name in mcp_tools_dict:
                continue
                
            # 获取工具的参数 Schema
            schema = {"type": "object", "properties": {}}
            if hasattr(tool, "args_schema") and tool.args_schema:
                schema = tool.args_schema.model_json_schema()
            
            mcp_tools_dict[tool.name] = types.Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=schema
            )
        return list(mcp_tools_dict.values())

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        """执行具体的工具任务"""
        SkillRegistry.auto_discover()
        all_tools = SkillRegistry.get_all_tools()
        
        # 寻找匹配的工具实例
        target_tool = next((t for t in all_tools if t.name == name), None)
        
        if not target_tool:
            raise ValueError(f"未找到工具: {name}")
            
        try:
            # 异步执行工具并返回结果
            result = await target_tool.ainvoke(arguments)
            return [types.TextContent(type="text", text=str(result))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"工具 {name} 执行出错: {str(e)}")]
