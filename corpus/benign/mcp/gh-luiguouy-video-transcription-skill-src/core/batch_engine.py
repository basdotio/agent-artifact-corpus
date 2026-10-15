"""
并发批处理调度引擎模块
基于分阶段信号量 (Staged Semaphores) 实现 I/O、视频渲染与 Whisper 推理的资源分流流水线
"""

import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Callable, Dict, Any

from src.config import settings
from src.core.cleaner import TextCleaner
from src.core.extractor import MediaExtractor
from src.core.watermark import VideoCleaner
from src.core.transcriber import pipeline_engine
from src.schemas import (
    TranscriptionResponse,
    SegmentItem,
    BatchItemProgress,
    BatchTranscriptionResponse,
    TaskStatusType
)


class BatchTranscriptionEngine:
    """
    分阶段并发批处理调度引擎
    第一性原理：I/O (下载)、CPU (视频滤镜/超清增强) 与 GPU (Whisper 模型推理) 资源特性迥异，
    必须采用细粒度分阶段信号量进行算力削峰与流量控制，以获得最大流水线吞吐量，同时杜绝 OOM 与 CPU 假死。
    """

    def __init__(self):
        # 阶段一：网络 I/O 信号量（控制并发下载数量）
        self._io_semaphore = threading.BoundedSemaphore(value=max(1, settings.MAX_CONCURRENT_DOWNLOADS))
        # 阶段二：计算密集型渲染信号量（控制 FFmpeg 10-bit超清滤镜并发数量）
        self._render_semaphore = threading.BoundedSemaphore(value=max(1, settings.MAX_CONCURRENT_RENDERS))
        # 阶段三：显存/内存密集型转录信号量（严格限制 Whisper 并发推理数量）
        self._transcribe_semaphore = threading.BoundedSemaphore(value=max(1, settings.MAX_CONCURRENT_TRANSCRIBES))

    def _update_task(
        self,
        task: BatchItemProgress,
        status: TaskStatusType,
        message: Optional[str] = None,
        result: Optional[TranscriptionResponse] = None,
        error: Optional[str] = None,
        title: Optional[str] = None,
        callback: Optional[Callable[[BatchItemProgress], None]] = None
    ):
        """更新任务内部状态并触发回调通知"""
        task.status = status
        if message is not None:
            task.message = message
        if result is not None:
            task.result = result
        if error is not None:
            task.error = error
        if title is not None:
            task.title = title
        if callback:
            try:
                callback(task)
            except Exception:
                pass

    def process_single_task(
        self,
        task: BatchItemProgress,
        output_format: str = "paragraph",
        language: Optional[str] = None,
        auto_remove_watermark: bool = True,
        remove_subtitles: bool = False,
        enhance_quality: bool = False,
        download_only: bool = False,
        callback: Optional[Callable[[BatchItemProgress], None]] = None
    ) -> BatchItemProgress:
        """
        处理单个视频任务的全流程（带分阶段信号量保护）
        """
        raw_url = task.url
        downloads_dir = os.path.abspath(settings.DOWNLOADS_DIR)
        os.makedirs(downloads_dir, exist_ok=True)

        # 1. 过滤并提取纯净 URL
        try:
            clean_url = TextCleaner.extract_url(raw_url)
        except Exception as e:
            self._update_task(
                task, status="failed",
                message="URL 解析失败",
                error=f"无法从输入中提取有效链接: {str(e)}",
                callback=callback
            )
            return task

        # 2. 阶段一：网络 I/O (下载视频与提取原始音频)
        self._update_task(task, status="downloading", message="正在排队/下载媒体与提取音频...", callback=callback)
        wav_path, mp4_path, meta = None, None, {}
        with self._io_semaphore:
            self._update_task(task, status="downloading", message="正在下载视频及提取 16kHz WAV...", callback=callback)
            try:
                wav_path, mp4_path, meta = MediaExtractor.extract_media(clean_url, downloads_dir)
                title = meta.get("title", "未知标题")
                self._update_task(task, status="downloading", title=title, message="媒体下载与音频提取完成", callback=callback)
            except Exception as e:
                self._update_task(
                    task, status="failed",
                    message="媒体抓取/转码失败",
                    error=f"媒体抓取/转码异常: {str(e)}",
                    callback=callback
                )
                return task

        # 如果开启了“仅下载模式”，在此直接完成，跳过画质增强与语音识别
        if download_only:
            download_resp = TranscriptionResponse(
                status="success",
                title=meta.get("title", task.title or "未知标题"),
                duration=round(meta.get("duration", 0.0) or 0.0, 2),
                language="unknown",
                format=output_format,
                text="[仅下载模式] 视频与音频提取完成，已跳过后续渲染与转写。",
                video_path=os.path.abspath(mp4_path) if mp4_path else None,
                audio_path=os.path.abspath(wav_path) if wav_path else None,
                watermark_detected=False,
                quality_enhanced=False,
                segments=[]
            )
            self._update_task(
                task,
                status="completed",
                title=download_resp.title,
                message="视频与音频下载完成 (仅下载模式)",
                result=download_resp,
                callback=callback
            )
            return task

        # 3. 阶段二：CPU / 编解码密集型（全自动水印检测与画面净化 / 10-bit 超清画质增强）
        watermark_detected = False
        quality_enhanced = False
        if mp4_path and (auto_remove_watermark or remove_subtitles or enhance_quality):
            self._update_task(task, status="enhancing", message="正在排队画质增强/去标算力...", callback=callback)
            with self._render_semaphore:
                self._update_task(task, status="enhancing", message="正在执行 10-bit 超清修复/滤镜渲染...", callback=callback)
                try:
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
                    self._update_task(task, status="enhancing", message="画面处理与超清增强完成", callback=callback)
                except Exception as e:
                    # 滤镜失败不中断语音转写流水线，记录警告降级为原视频
                    self._update_task(task, status="enhancing", message=f"画面处理遇到非致命警告: {str(e)}", callback=callback)

        # 4. 阶段三：显存 / 内存密集型（Whisper 模型语音识别）
        self._update_task(task, status="transcribing", message="正在排队模型推理资源...", callback=callback)
        try:
            with self._transcribe_semaphore:
                self._update_task(task, status="transcribing", message="正在进行本地 Whisper 语音转录...", callback=callback)
                initial_prompt = "这是一段标准中文普通话语音，包含完整的逗号和句号。"
                model = pipeline_engine._get_model()
                segments_gen, info = model.transcribe(
                    audio=wav_path,
                    beam_size=5,
                    language=language,
                    initial_prompt=initial_prompt,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500),
                    condition_on_previous_text=False
                )
                segments = list(segments_gen)
                detected_lang = info.language
        except Exception as e:
            self._update_task(
                task, status="failed",
                message="模型推理失败",
                error=f"Whisper 推理异常: {str(e)}",
                callback=callback
            )
            return task

        # 5. 封装与规范化
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

        response_payload = TranscriptionResponse(
            status="success",
            title=meta.get("title", task.title or "未知标题"),
            duration=round(meta.get("duration", 0.0) or 0.0, 2),
            language=detected_lang,
            format=output_format,
            text=result_text if result_text else "未能从视频中识别到有效人声。",
            video_path=os.path.abspath(mp4_path) if mp4_path else None,
            audio_path=os.path.abspath(wav_path) if wav_path else None,
            watermark_detected=watermark_detected,
            quality_enhanced=quality_enhanced,
            segments=parsed_segments
        )

        self._update_task(
            task,
            status="completed",
            title=response_payload.title,
            message="转写与处理全部完成",
            result=response_payload,
            callback=callback
        )
        return task

    def execute_batch(
        self,
        urls: List[str],
        output_format: str = "paragraph",
        language: Optional[str] = None,
        auto_remove_watermark: bool = True,
        remove_subtitles: bool = False,
        enhance_quality: bool = False,
        download_only: bool = False,
        max_workers: Optional[int] = None,
        progress_callback: Optional[Callable[[BatchItemProgress], None]] = None
    ) -> BatchTranscriptionResponse:
        """
        执行批量并发转录任务
        """
        start_time = time.time()
        effective_workers = max_workers or settings.MAX_CONCURRENT_TASKS

        # 初始化各任务状态
        tasks: List[BatchItemProgress] = []
        for idx, url in enumerate(urls, 1):
            item = BatchItemProgress(
                task_id=f"task_{idx}_{int(time.time()) % 10000}",
                url=url.strip(),
                title=f"视频_{idx}",
                status="pending",
                message="已进入队列等待调度"
            )
            tasks.append(item)
            if progress_callback:
                progress_callback(item)

        results: List[BatchItemProgress] = []
        with ThreadPoolExecutor(max_workers=effective_workers) as executor:
            future_to_task = {
                executor.submit(
                    self.process_single_task,
                    task=t,
                    output_format=output_format,
                    language=language,
                    auto_remove_watermark=auto_remove_watermark,
                    remove_subtitles=remove_subtitles,
                    enhance_quality=enhance_quality,
                    download_only=download_only,
                    callback=progress_callback
                ): t
                for t in tasks
            }

            for future in as_completed(future_to_task):
                task_res = future.result()
                results.append(task_res)

        # 按照原输入顺序重新排序
        task_id_order = {t.task_id: idx for idx, t in enumerate(tasks)}
        results.sort(key=lambda x: task_id_order.get(x.task_id, 0))

        success_cnt = sum(1 for r in results if r.status == "completed")
        failed_cnt = sum(1 for r in results if r.status == "failed")
        elapsed = round(time.time() - start_time, 2)

        if success_cnt == len(results):
            overall_status = "success"
        elif success_cnt > 0:
            overall_status = "partial_success"
        else:
            overall_status = "error"

        return BatchTranscriptionResponse(
            status=overall_status,
            total_count=len(results),
            success_count=success_cnt,
            failed_count=failed_cnt,
            results=results,
            elapsed_seconds=elapsed
        )


# 单例批处理引擎
batch_engine = BatchTranscriptionEngine()
