"""MCP 资源定义文件"""
from mcp.server import Server
import mcp.types as types

def register_resources(server: Server) -> None:
    """向 MCP 服务端注册资源"""
    
    @server.list_resources()
    async def list_resources() -> list[types.Resource]:
        """列出所有可用的资源"""
        return [
            types.Resource(
                uri="skill://list",
                name="可用 Skill 列表",
                description="当前系统中已安装的所有 Skill 插件列表",
                mimeType="text/plain"
            ),
            types.Resource(
                uri="history://recent",
                name="最近报告",
                description="最近生成的报告列表预览",
                mimeType="text/plain"
            )
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        """读取特定资源的内容"""
        if uri == "skill://list":
            # 动态导入以防止循环依赖
            from src.report.skills.registry import SkillRegistry
            SkillRegistry.auto_discover()
            skills = SkillRegistry.list_enabled()
            skill_info = []
            for s in skills:
                meta = s.metadata()
                skill_info.append(f"- {meta.display_name} ({meta.name}): {meta.description}")
            return "\n".join(skill_info) if skill_info else "暂无可用 Skill。"
            
        elif uri == "history://recent":
            return "最近历史记录功能尚未在资源层实现。"
            
        elif uri.startswith("report://"):
            thread_id = uri.replace("report://", "")
            return f"这里将加载 thread_id 为 {thread_id} 的报告内容预览。"
            
        raise ValueError(f"未知的资源 URI: {uri}")
