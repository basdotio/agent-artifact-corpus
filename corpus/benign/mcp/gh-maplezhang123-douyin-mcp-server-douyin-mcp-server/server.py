"""MCP tools for Douyin metadata and transcript extraction."""
from __future__ import annotations
import asyncio
import json
import os
import tempfile
from pathlib import Path
from mcp.server.fastmcp import Context, FastMCP
from .workflow import resolve_video_info, run_verified_workflow, transcribe_cloud_siliconflow, transcribe_local

mcp = FastMCP("Douyin MCP Server")

@mcp.tool()
def get_douyin_download_link(share_link: str) -> str:
    """解析抖音链接；HTTP 失败时自动使用浏览器获取元数据。"""
    try:
        info = resolve_video_info(share_link)
        return json.dumps({"status": "success" if info.get("url") else "metadata-only",
            "video_id": info["video_id"], "title": info["title"], "download_url": info.get("url", ""),
            "parser": info.get("source", "http")}, ensure_ascii=False, indent=2)
    except Exception as exc:
        return json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False)

@mcp.tool()
async def extract_douyin_text(share_link: str, asr_mode: str = "cloud", local_model: str = "small",
                              context: str = "rewrite", ctx: Context = None) -> str:
    """提取文案。cloud 需要 SILICONFLOW_API_KEY；local 是可选离线模式。"""
    if ctx:
        await ctx.info("正在解析链接并提取音频；HTTP 失败会自动使用浏览器")
    try:
        result = await asyncio.to_thread(run_verified_workflow, share_link,
            Path(os.getenv("DOUYIN_OUTPUT_DIR", str(Path.cwd() / "output"))),
            context, local_model, None, None, asr_mode)
        if ctx:
            await ctx.info(f"提取完成；ASR: {result['asr_model']}")
        return result["text"]
    except Exception as exc:
        raise RuntimeError(f"提取抖音视频文本失败：{exc}") from exc

@mcp.tool()
def recognize_audio_file(file_path: str, asr_mode: str = "cloud", model: str = "small") -> str:
    """识别本地音频；默认 SiliconFlow，也可选择本地 Whisper。"""
    source = Path(file_path)
    if not source.is_file():
        return json.dumps({"status": "error", "error": f"音频文件不存在：{source}"}, ensure_ascii=False)
    try:
        with tempfile.TemporaryDirectory(prefix="douyin-asr-") as temp_name:
            transcript = Path(temp_name) / "transcript.md"
            result = (transcribe_local(source, transcript, model) if asr_mode == "local"
                      else transcribe_cloud_siliconflow(source, transcript))
        return json.dumps({"status": "success", "text": result["text"], "engine": result["engine"],
                           "model": result["model"]}, ensure_ascii=False, indent=2)
    except Exception as exc:
        return json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False)

@mcp.tool()
def parse_douyin_video_info(share_link: str) -> str:
    """解析视频 ID、标题、下载地址与解析方式。"""
    return get_douyin_download_link(share_link)

@mcp.resource("douyin://video/{video_id}")
def get_video_info(video_id: str) -> str:
    return get_douyin_download_link(f"https://www.douyin.com/video/{video_id}")

@mcp.prompt()
def douyin_text_extraction_guide() -> str:
    return """# 抖音文案提取
默认使用 SiliconFlow SenseVoice，请设置 SILICONFLOW_API_KEY。
可选的 DeepSeek 整理使用 DEEPSEEK_API_KEY；不配置仍会返回原始逐字稿。
本地模式需安装 local 额外依赖，并设置 DOUYIN_ASR_MODE=local。"""

def main() -> None:
    mcp.run()

if __name__ == "__main__":
    main()
