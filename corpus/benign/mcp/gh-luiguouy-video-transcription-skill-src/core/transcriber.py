"""
语音识别模型流水线模块
基于 faster-whisper 实现懒加载、线程安全锁、防幻觉推理与沙箱回收
"""

import tempfile
import threading
from typing import Optional
from faster_whisper import WhisperModel
from src.config import settings
from src.core.cleaner import TextCleaner
from src.core.extractor import MediaExtractor
from src.schemas import TranscriptionResponse, SegmentItem


from src.core.watermark import VideoCleaner


class TranscriptionPipeline:
    def __init__(self):
        # 懒加载模型实例，避免后台常驻空转浪费显存/内存
        self._model = None
        self._lock = threading.Lock()

    def _get_model(self) -> WhisperModel:
        """按需加载 Whisper 模型（单例懒加载），具备 CUDA 异常时自动平滑降级到 CPU"""
        if self._model is None:
            device = settings.WHISPER_DEVICE
            compute_type = settings.WHISPER_COMPUTE_TYPE

            # 智能设备与计算精度兼容性判断
            if device == "auto":
                try:
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    compute_type = "float16" if device == "cuda" else "int8"
                except ImportError:
                    device = "cpu"
                    compute_type = "int8"

            try:
                self._model = WhisperModel(
                    model_size_or_path=settings.WHISPER_MODEL_SIZE,
                    device=device,
                    compute_type=compute_type,
                    download_root=settings.WHISPER_MODEL_DIR
                )
            except Exception:
                # 若 GPU 缺少 CUDA 12 动态库（如 cublas64_12.dll），自动降级到 CPU
                if device != "cpu":
                    self._model = WhisperModel(
                        model_size_or_path=settings.WHISPER_MODEL_SIZE,
                        device="cpu",
                        compute_type="int8",
                        download_root=settings.WHISPER_MODEL_DIR
                    )
                else:
                    raise
        return self._model

    def execute(
        self,
        raw_url: str,
        output_format: str = "paragraph",
        language: Optional[str] = None,
        auto_remove_watermark: bool = True,
        remove_subtitles: bool = False,
        enhance_quality: bool = False
    ) -> TranscriptionResponse:
        """
        执行完整的“抓取-转码-自动去水印/画质增强-转写-规整”流程（默认持久化保存模式）
        """
        # 1. 过滤并提取纯净 URL
        clean_url = TextCleaner.extract_url(raw_url)

        # 2. 持久化存储管理：保存到本地 downloads 目录，由用户决定删除
        import os
        downloads_dir = os.path.abspath(settings.DOWNLOADS_DIR)
        os.makedirs(downloads_dir, exist_ok=True)

        try:
            wav_path, mp4_path, meta = MediaExtractor.extract_media(clean_url, downloads_dir)
        except Exception as e:
            return TranscriptionResponse(
                status="error",
                format=output_format,
                text="",
                error_message=f"媒体抓取/转码失败: {str(e)}"
            )

        # 3. 全自动创作者水印检测与画面净化/10-bit超清画质增强
        watermark_detected = False
        quality_enhanced = False
        if mp4_path and (auto_remove_watermark or remove_subtitles or enhance_quality):
            cleaned_mp4, wm_hit, enh_hit = VideoCleaner.clean_video(
                input_mp4=mp4_path,
                output_dir=downloads_dir,
                remove_watermark=auto_remove_watermark,
                remove_subtitles=remove_subtitles,
                enhance_quality=enhance_quality
            )
            if cleaned_mp4 != mp4_path:
                mp4_path = cleaned_mp4
                watermark_detected = wm_hit
                quality_enhanced = enh_hit

        # 4. Whisper 语音推理
        try:
            initial_prompt = "这是一段标准中文普通话语音，包含完整的逗号和句号。"
            with self._lock:  # 线程锁：确保同一时间只有一个任务占用模型推理，防止显存溢出
                model = self._get_model()
                segments_gen, info = model.transcribe(
                    audio=wav_path,
                    beam_size=5,
                    language=language,
                    initial_prompt=initial_prompt,
                    vad_filter=True,  # 开启 VAD 静音切除，跳过无声片段加速
                    vad_parameters=dict(min_silence_duration_ms=500),
                    condition_on_previous_text=False  # 关闭上一句关联，彻底压制"复读机"式幻觉
                )
                segments = list(segments_gen)
        except Exception as e:
            return TranscriptionResponse(
                status="error",
                format=output_format,
                text="",
                error_message=f"Whisper 模型推理异常: {str(e)}"
            )

        # 5. 结果结构化封装
        parsed_segments = [
            SegmentItem(
                start=round(s.start, 2),
                end=round(s.end, 2),
                text=s.text.strip()
            )
            for s in segments if s.text.strip()
        ]

        if output_format == "timestamped":
            result_text = TextCleaner.to_timestamped_lines(segments)
        else:
            result_text = TextCleaner.to_fluent_paragraph(segments)

        return TranscriptionResponse(
            status="success",
            title=meta.get("title", "未知标题"),
            duration=round(meta.get("duration", 0.0) or 0.0, 2),
            language=info.language,
            format=output_format,
            text=result_text if result_text else "未能从视频中识别到有效人声。",
            video_path=os.path.abspath(mp4_path) if mp4_path else None,
            audio_path=os.path.abspath(wav_path) if wav_path else None,
            watermark_detected=watermark_detected,
            quality_enhanced=quality_enhanced,
            segments=parsed_segments
        )


# 单例运行引擎（内部懒加载）
pipeline_engine = TranscriptionPipeline()
