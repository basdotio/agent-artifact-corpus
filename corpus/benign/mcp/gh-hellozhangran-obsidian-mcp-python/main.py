import os
import glob
from mcp.server.fastmcp import FastMCP

mcp = FastMCP()

# 从环境变量中获取 Obsidian 根目录路径，默认为当前目录
OBSIDIAN_ROOT = os.environ.get("OBSIDIAN_PATH", ".")


@mcp.tool()
def count_markdown_files():
    """获取 Obsidian 库中所有 Markdown 文件的数量"""
    md_files = glob.glob(os.path.join(OBSIDIAN_ROOT, "**/*.md"), recursive=True)
    return len(md_files)


@mcp.tool()
def get_all_markdown_contents():
    """获取 Obsidian 库中所有 Markdown 文件的内容"""
    md_files = glob.glob(os.path.join(OBSIDIAN_ROOT, "**/*.md"), recursive=True)
    result = []
    
    for file_path in md_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 获取相对路径作为文件标识符
                relative_path = os.path.relpath(file_path, OBSIDIAN_ROOT)
                result.append({
                    "file": relative_path,
                    "content": content
                })
        except Exception as e:
            result.append({
                "file": os.path.relpath(file_path, OBSIDIAN_ROOT),
                "error": str(e)
            })
    
    return result


@mcp.tool()
def create_markdown_file(filename, content=""):
    """在 Obsidian 库中创建一个新的 Markdown 文件
    
    Args:
        filename: Markdown 文件名 (不需要 .md 后缀，会自动添加)
        content: 文件的初始内容 (可选)
    """
    # 确保有 .md 后缀
    if not filename.endswith('.md'):
        filename += '.md'
    
    # 创建完整路径
    file_path = os.path.join(OBSIDIAN_ROOT, filename)
    
    # 检查文件是否已存在
    if os.path.exists(file_path):
        return {"success": False, "error": f"文件 {filename} 已存在"}
    
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 创建文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {"success": True, "path": os.path.relpath(file_path, OBSIDIAN_ROOT)}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    print(f"Obsidian MCP 服务已启动，使用路径: {OBSIDIAN_ROOT}")
    mcp.run(transport="stdio")
