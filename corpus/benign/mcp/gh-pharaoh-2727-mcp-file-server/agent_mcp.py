from pathlib import Path
from fastmcp import FastMCP

mcp = FastMCP("agent_mcp")

BASE_DIR = Path(__file__).resolve().parent / 'sandbox' # 沙箱根目录


def _safe(path: str) -> Path:
    """确保路径在沙箱根目录下"""
    target = (BASE_DIR / path).resolve() # 沙箱目标文件
    if not target.is_relative_to(BASE_DIR):  # 检查路径是否在沙箱根目录下
        raise ValueError(f"Path escapes sandbox: {path}")  # 如果路径在沙箱根目录外，则抛出错误
    return target  # 返回沙箱目标文件


@mcp.tool
def read_file(path: str) -> str:
    """读取 sandbox 内的文件内容。path 用 / 分隔，相对 sandbox 根目录。"""
    MAX_CHARS = 20000  # 单次返回的字符数量上限
    HEAD_CHARS = 8000  # 超出上限时，只保留开头这么多字符
    if not path.strip(): # 如果路径为空
        return "错误：路径为空。请传入相对于 sandbox 根目录的路径（例如 notes.txt）。"
    target = _safe(path)
    if not target.exists():  # 判断文件不存在
        return f"错误：文件不存在（{path}）。可以先调用 list_dir 看看有什么。"
    if target.is_dir():  # 判断是否为目录
        return f"错误：{path} 是目录不是文件，请用 list_dir。"
    try:
        text = target.read_text(encoding="utf-8")
        if not text.strip():
            return f"（{path} 是空文件，或只有空白字符）"
        if len(text) > MAX_CHARS:  # 文件过大，截断后再返回
            return (f"（{path} 共 {len(text)} 字符，超过上限 {MAX_CHARS}，"
                    f"仅显示前 {HEAD_CHARS} 字符）\n{text[:HEAD_CHARS]}")
        return text
    except UnicodeDecodeError:
        return f"错误：{path} 不是 UTF-8 编码（可能是 GBK 等中文编码，或二进制文件）"
    except OSError:
        return f"错误：无法读取文件 {path}。"


@mcp.tool
def list_dir(path: str) -> str:
    """列出 sandbox 内的目录内容。path 用 / 分隔，相对 sandbox 根目录。"""
    if not path.strip(): # 如果路径为空
        return "错误：路径为空。请传入相对于 sandbox 根目录的路径（例如 notes.txt）。"
    target = _safe(path)
    if not target.exists():  # 判断目录不存在
        return f"错误：目录不存在（{path}）。可以先调用 list_dir 看看有什么。"
    if target.is_file():  # 判断是否为文件
        return f"错误：{path} 是文件不是目录，请用 read_file。"
    try:
        items = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except OSError:
        return f"错误：无法读取目录 {path}。"

    if not items:
        return "（空目录）"

    lines = []
    for p in items:
        if p.is_dir():  # 判断是否为目录
            lines.append(f"目录: {p.name}")
        else:
            lines.append(f"文件: {p.name}")
    return "\n".join(lines)


@mcp.tool
def write_file(path: str, content: str) -> str:
    """写入 sandbox 内的文件。path 用 / 分隔，相对 sandbox 根目录。"""
    if not path.strip(): # 如果路径为空
        return "错误：路径为空。请传入相对于 sandbox 根目录的路径（例如 notes.txt）。"
    target = _safe(path)
    try:
        if not target.parent.exists():  # 判断父目录不存在
            return f"错误：父目录不存在（{target.parent.name}）。请先写到 sandbox 根目录，或者用已存在的子目录。"
        if target.is_dir():  # 判断是否为目录
            return f"错误：{path} 是目录不是文件，请用 list_dir。"
        if target.exists():  # 判断文件存在
            return f"错误：文件已存在（{path}）。请先调用 list_dir 看看有什么。"
        target.write_text(content, encoding="utf-8")
        return f"成功：已写入文件 {path}。"
    except OSError:
        return f"错误：无法写入文件 {path}。"


@mcp.tool
def search_content(path: str, keyword: str) -> str:
    """搜索 sandbox 内的文件内容。path 用 / 分隔，相对 sandbox 根目录。"""
    MAX_RESULTS = 50
    if not path.strip(): # 如果路径为空
        return "错误：路径为空。请传入相对于 sandbox 根目录的路径（例如 notes.txt）。"
    if not keyword.strip():
        return "错误：关键字为空。请传入关键字。"
    target = _safe(path)
    if not target.exists():  # 判断文件不存在
        return f"错误：文件不存在（{path}）。可以先调用 list_dir 看看有什么。"
    if target.is_file():  # 判断是否为文件
        files = [target]
    else:
        files = sorted((p for p in target.rglob("*") if p.is_file()), key=lambda p: str(p).lower())
    results = []
    for f in files:
        if len(results) >= MAX_RESULTS:
            break
        try:
            content = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(content.splitlines(), start=1):
            if keyword in line:
                display = line if len(line) <= 200 else line[:200] + f"...（该行共 {len(line)} 字符）"
                results.append(f"{f.relative_to(BASE_DIR)}: {i}: {display}")
                if len(results) >= MAX_RESULTS:
                    break
    if not results:
        return f"没有找到包含「{keyword}」的内容。"
    text = "\n".join(results)
    if len(results) >= MAX_RESULTS:
        text += f"\n（已达上限 {MAX_RESULTS} 条，可能还有更多，请缩小搜索范围）"
    return text


if __name__ == '__main__':
    mcp.run(transport="stdio")
