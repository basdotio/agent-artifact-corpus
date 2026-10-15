"""
FastMCP 本地服务入口
通过本地标准输入输出 (stdio) 与宿主 Agent（Cursor / Claude Desktop / Antigravity 等）交互
提供单视频解析及多视频并发批处理工具
"""

import os
import time
import json
from typing import Optional, List, Union
from fastmcp import FastMCP
from src.core.transcriber import pipeline_engine
from src.core.batch_engine import batch_engine
from src.schemas import TranscriptionRequest, BatchTranscriptionRequest, BatchTranscriptionResponse

mcp = FastMCP("Video-Transcription-Skill")


@mcp.tool(
    name="transcribe_media_url",
    description=(
        "网络音视频解析与语音转文字工具。支持输入单个抖音、B站、YouTube、X 等平台视频链接（支持抖音App分享文案），"
        "自动抓取音频并高保真转录。可选输出连贯标点段落 ('paragraph') 或高精度时间戳字幕 ('timestamped')。"
    )
)
def transcribe_media_url(
    url: str,
    output_format: str = "paragraph",
    language: Optional[str] = None,
    auto_remove_watermark: bool = True,
    remove_subtitles: bool = False,
    enhance_quality: bool = False
) -> str:
    """
    参数说明:
    - url: 视频网页地址，支持直接粘贴混有分享文案的抖音链接、B站av/BV号、YouTube等
    - output_format: 'paragraph'（连贯纯文本段落，去除多余空格）或 'timestamped'（分行时间戳切片）
    - language: 语言代码（如 'zh', 'en'），默认 None 为自动识别
    - auto_remove_watermark: 是否全自动检测并消除创作者角标水印（默认开启）
    - remove_subtitles: 是否消除视频底部硬字幕（默认关闭，保持原字幕）
    - enhance_quality: 是否开启 10-bit 超清画质增强管线（含动态降噪、BT.709校色、Lanczos超采与去色带锐化，默认关闭）
    """
    req = TranscriptionRequest(
        url=url,
        output_format=output_format,
        language=language,
        auto_remove_watermark=auto_remove_watermark,
        remove_subtitles=remove_subtitles,
        enhance_quality=enhance_quality
    )
    res = pipeline_engine.execute(
        raw_url=req.url,
        output_format=req.output_format,
        language=req.language,
        auto_remove_watermark=req.auto_remove_watermark,
        remove_subtitles=req.remove_subtitles,
        enhance_quality=req.enhance_quality
    )

    if res.status == "error":
        return f"【转写异常】{res.error_message}"

    media_info_list = []
    if res.video_path:
        tags = []
        if res.watermark_detected:
            tags.append("已自动消除创作者水印")
        if res.quality_enhanced:
            tags.append("已执行 10-bit 超清画质增强")
        wm_tag = f" ({' | '.join(tags)})" if tags else ""
        media_info_list.append(f"【媒体保存】完整视频: {res.video_path}{wm_tag}")
    if res.audio_path:
        media_info_list.append(f"【媒体保存】提取音频: {res.audio_path}")
    media_info = ("\n".join(media_info_list) + "\n") if media_info_list else ""
    header = (
        f"【视频信息】标题: {res.title} | 时长: {res.duration}秒 | 识别语种: {res.language}\n"
        f"{media_info}"
        f"【输出模式】{res.format}\n"
        "----------------------------------------\n"
    )

    final_text = header + res.text

    # 针对长视频/长文本的上下文保护机制：超过 8000 字符时自动落地为本地文件，避免 Agent Context 崩溃
    if len(final_text) > 8000:
        safe_filename = f"transcription_{int(time.time())}.txt"
        safe_path = os.path.abspath(safe_filename)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(final_text)

        return (
            header +
            f"\n【注意】提取文本量较大（全文约 {len(res.text)} 字），"
            f"为防止超长内容中断对话，完整内容已安全导出到本地文件：\n{safe_path}\n"
            "您可以通过文件读取工具查看完整文本。"
        )

    return final_text


@mcp.tool(
    name="batch_transcribe_media_urls",
    description=(
        "批量多视频并发解析与语音转文字工具。支持传入多个视频链接列表或换行分隔的文本，"
        "采用分阶段信号量并发流水线（并发下载 -> 受限画质增强 -> 受限Whisper推理），"
        "最大化系统吞吐并防止显存与CPU过载。返回批量聚合报告与每个任务的落地路径。"
    )
)
def batch_transcribe_media_urls(
    urls: List[str],
    output_format: str = "paragraph",
    language: Optional[str] = None,
    auto_remove_watermark: bool = True,
    remove_subtitles: bool = False,
    enhance_quality: bool = False,
    concurrency: Optional[int] = None
) -> str:
    """
    参数说明:
    - urls: 待处理的视频链接列表（支持抖音分享文案、B站、YouTube等）
    - output_format: 'paragraph' 或 'timestamped'
    - language: 语言代码（如 'zh', 'en'），默认 None 为自动识别
    - auto_remove_watermark: 是否消除创作者角标水印（默认 True）
    - remove_subtitles: 是否消除视频底部硬字幕（默认 False）
    - enhance_quality: 是否开启 10-bit 画质增强（默认 False）
    - concurrency: 最大并发处理任务数（默认由配置决定，一般为 3）
    """
    clean_urls = [u.strip() for u in urls if u and u.strip()]
    if not clean_urls:
        return "【错误】未提供有效的视频链接列表。"

    response: BatchTranscriptionResponse = batch_engine.execute_batch(
        urls=clean_urls,
        output_format=output_format,
        language=language,
        auto_remove_watermark=auto_remove_watermark,
        remove_subtitles=remove_subtitles,
        enhance_quality=enhance_quality,
        max_workers=concurrency
    )

    summary_blocks = [
        f"=== 批量多视频并发处理报告 ===",
        f"【总任务数】{response.total_count} 个 | 【成功】{response.success_count} 个 | 【失败】{response.failed_count} 个 | 【总耗时】{response.elapsed_seconds} 秒\n"
    ]

    for idx, item in enumerate(response.results, 1):
        if item.status == "completed" and item.result:
            tags = []
            if item.result.watermark_detected:
                tags.append("已去水印")
            if item.result.quality_enhanced:
                tags.append("10-bit画质增强")
            tag_str = f" [{', '.join(tags)}]" if tags else ""

            # 简略展示前 150 字避免撑爆上下文
            preview_text = item.result.text[:150] + ("..." if len(item.result.text) > 150 else "")
            summary_blocks.append(
                f"[{idx}] ✅ {item.result.title}{tag_str}\n"
                f"   - 时长: {item.result.duration}s | 语言: {item.result.language}\n"
                f"   - 视频: {item.result.video_path or '未生成'}\n"
                f"   - 音频: {item.result.audio_path or '未生成'}\n"
                f"   - 识别内容摘要: {preview_text}\n"
            )
        else:
            summary_blocks.append(
                f"[{idx}] ❌ 任务失败: {item.title or item.url}\n"
                f"   - 错误信息: {item.error or item.message}\n"
            )

    report_text = "\n".join(summary_blocks)

    # 批处理详细数据安全归档
    timestamp = int(time.time())
    safe_json_path = os.path.abspath(f"batch_transcription_{timestamp}.json")
    try:
        with open(safe_json_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(response.model_dump(), ensure_ascii=False, indent=2))
        report_text += f"\n【批量详细数据归档】完整 JSON 数据已保存至: {safe_json_path}\n"
    except Exception:
        pass

    return report_text


if __name__ == "__main__":
    # 使用标准 stdio 运行，供本地宿主进程直接拉起
    mcp.run()
