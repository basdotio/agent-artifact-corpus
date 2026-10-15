"""
数据协议定义模块
定义请求体、时间戳分块与响应体数据模型
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class TranscriptionRequest(BaseModel):
    url: str = Field(
        ...,
        description="包含视频链接的字符串（支持抖音App复制的整段文案、B站或YouTube链接）"
    )
    output_format: Literal["paragraph", "timestamped"] = Field(
        default="paragraph",
        description="输出形态: 'paragraph'（带标点的连贯纯文本段落）或 'timestamped'（分行时间戳字幕）"
    )
    language: Optional[str] = Field(
        default=None,
        description="语言代码（如 'zh', 'en'），默认 None 为自动识别"
    )
    auto_remove_watermark: bool = Field(
        default=True,
        description="是否全自动检测并消除创作者角标水印（默认开启）"
    )
    remove_subtitles: bool = Field(
        default=False,
        description="是否消除视频底部硬字幕（默认关闭）"
    )
    enhance_quality: bool = Field(
        default=False,
        description="是否启用 10-bit 高清画质修复与超采增强（默认关闭）"
    )


class SegmentItem(BaseModel):
    start: float = Field(..., description="片段起始时间（秒）")
    end: float = Field(..., description="片段结束时间（秒）")
    text: str = Field(..., description="片段识别文本")


class TranscriptionResponse(BaseModel):
    status: Literal["success", "error"]
    title: Optional[str] = Field(default=None, description="视频标题")
    duration: Optional[float] = Field(default=None, description="视频时长（秒）")
    language: Optional[str] = Field(default=None, description="自动识别或指定的语言")
    format: str = Field(..., description="输出格式 ('paragraph' 或 'timestamped')")
    text: str = Field(..., description="转写生成的全文内容")
    video_path: Optional[str] = Field(default=None, description="本地保存的完整 MP4 视频绝对路径")
    audio_path: Optional[str] = Field(default=None, description="本地保存的音频文件绝对路径")
    watermark_detected: bool = Field(default=False, description="是否在视频中检测到并消除了创作者水印")
    quality_enhanced: bool = Field(default=False, description="是否在视频中执行了 10-bit 高清画质修复与超采增强")
    segments: Optional[List[SegmentItem]] = Field(default=None, description="时间戳字幕切片列表")
    error_message: Optional[str] = Field(default=None, description="异常错误信息")


TaskStatusType = Literal["pending", "downloading", "enhancing", "transcribing", "completed", "failed"]


class BatchItemProgress(BaseModel):
    task_id: str = Field(..., description="任务唯一标识")
    url: str = Field(..., description="原始输入链接或文案")
    title: Optional[str] = Field(default=None, description="解析出的视频标题")
    status: TaskStatusType = Field(default="pending", description="当前阶段状态")
    message: Optional[str] = Field(default=None, description="阶段详情说明")
    result: Optional[TranscriptionResponse] = Field(default=None, description="成功时的转录结果")
    error: Optional[str] = Field(default=None, description="失败时的错误信息")


class BatchTranscriptionRequest(BaseModel):
    urls: List[str] = Field(..., description="待处理的视频链接列表（支持抖音分享文案、B站、YouTube等）")
    output_format: Literal["paragraph", "timestamped"] = Field(
        default="paragraph",
        description="输出形态: 'paragraph' 或 'timestamped'"
    )
    language: Optional[str] = Field(default=None, description="语言代码，默认自动识别")
    auto_remove_watermark: bool = Field(default=True, description="是否全自动检测并消除水印")
    remove_subtitles: bool = Field(default=False, description="是否消除视频底部硬字幕")
    enhance_quality: bool = Field(default=False, description="是否开启 10-bit 画质增强")
    download_only: bool = Field(default=False, description="是否仅执行并发下载与音频提取（跳过模型转录与滤镜增强）")
    max_workers: Optional[int] = Field(default=None, description="最大并发任务数")


class BatchTranscriptionResponse(BaseModel):
    status: Literal["success", "partial_success", "error"]
    total_count: int = Field(..., description="提交的总任务数")
    success_count: int = Field(..., description="成功任务数")
    failed_count: int = Field(..., description="失败任务数")
    results: List[BatchItemProgress] = Field(default_factory=list, description="各任务详细结果与进度")
    elapsed_seconds: float = Field(default=0.0, description="批处理总耗时（秒）")

