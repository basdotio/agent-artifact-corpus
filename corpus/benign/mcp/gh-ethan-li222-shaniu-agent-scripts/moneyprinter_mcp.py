"""Local stdio MCP entrypoint; stdout is reserved for MCP protocol messages."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from shaniu.config import Settings
from shaniu.moneyprinter import MoneyPrinterTools, ToolError
from shaniu.storage import Store

load_dotenv(ROOT / '.env')
settings = Settings(moneyprinter_enabled=True, moneyprinter_url=os.getenv('SHANIU_MPT_URL', 'http://127.0.0.1:8080'))
adapter = MoneyPrinterTools(settings, Store(Path(os.getenv('SHANIU_MCP_DATABASE', str(ROOT / 'data/moneyprinter-mcp.sqlite3')))))
mcp = FastMCP('Shaniu MoneyPrinterTurbo')


async def invoke(name, arguments):
    try:
        return await adapter.call('mcp-local', name, arguments)
    except ToolError as error:
        # No upstream response bodies or credentials enter tool errors.
        raise ValueError(str(error)) from None


@mcp.tool()
async def moneyprinter_health() -> dict:
    """检查本机 MoneyPrinterTurbo API 是否已启动及接口是否兼容。"""
    return await invoke('moneyprinter_health', {})


@mcp.tool()
async def moneyprinter_create(kind: str, subject: str, script: str = '', terms: str = '', aspect: str = '9:16', subtitles: bool = True, voice: str = 'zh-CN-XiaoxiaoNeural-Female', voice_rate: float = 1) -> dict:
    """明确要求制作时提交 video/audio/subtitle 任务。视频默认只传主题，由 MoneyPrinter 模型生成文案与搜索词；音频和字幕需要 script。

    只返回提交状态。不要自动重试提交；用 status 查询完成状态。
    subtitles 控制视频字幕，aspect 支持 9:16、16:9、1:1。
    """
    return await invoke('moneyprinter_create', dict(kind=kind, subject=subject, script=script, terms=terms, aspect=aspect, subtitles=subtitles, voice=voice, voice_rate=voice_rate))


@mcp.tool()
async def moneyprinter_enhance(task_id: str, style: str = 'clean', subtitles: bool = True, sound_effects: bool = True) -> dict:
    """用户明确要求时，对已完成的视频提交动效增强任务。普通版保留，status 的 enhancement 字段返回增强进度。"""
    return await invoke('moneyprinter_enhance', dict(task_id=task_id, style=style, subtitles=subtitles, sound_effects=sound_effects))


@mcp.tool()
async def moneyprinter_status(task_id: str) -> dict:
    """查询此 MCP 服务提交的任务进度、成功/失败及完成后的文件链接。"""
    return await invoke('moneyprinter_status', dict(task_id=task_id))


@mcp.tool()
async def moneyprinter_tasks() -> dict:
    """列出此 MCP 服务最近提交的任务 ID；可用 status 查询具体任务。"""
    return await invoke('moneyprinter_tasks', {})


if __name__ == '__main__':
    mcp.run(transport='stdio')
