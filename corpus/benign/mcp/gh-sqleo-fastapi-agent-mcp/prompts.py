"""MCP 提示词模板定义文件"""
from mcp.server import Server
import mcp.types as types

def register_prompts(server: Server) -> None:
    """向 MCP 服务端注册提示词模板"""
    
    @server.list_prompts()
    async def list_prompts() -> list[types.Prompt]:
        """列出所有可用的提示词模板"""
        return [
            types.Prompt(
                name="research_report",
                description="生成调研报告的引导提示词",
                arguments=[
                    types.PromptArgument(
                        name="topic",
                        description="需要调研的主题",
                        required=True
                    )
                ]
            ),
            types.Prompt(
                name="quick_analysis",
                description="快速分析的引导提示词",
                arguments=[
                    types.PromptArgument(
                        name="topic",
                        description="需要分析的主题",
                        required=True
                    )
                ]
            )
        ]

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict | None) -> types.GetPromptResult:
        """获取具体的提示词模板及其填充后的内容"""
        if not arguments:
            arguments = {}
            
        if name == "research_report":
            topic = arguments.get("topic", "未知主题")
            return types.GetPromptResult(
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text=f"请帮我生成一份关于「{topic}」的深度调研报告。"
                        )
                    )
                ]
            )
            
        elif name == "quick_analysis":
            topic = arguments.get("topic", "未知主题")
            return types.GetPromptResult(
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text=f"请快速分析「{topic}」的现状和趋势，500字以内。"
                        )
                    )
                ]
            )
            
        raise ValueError(f"未找到提示词模板: {name}")
