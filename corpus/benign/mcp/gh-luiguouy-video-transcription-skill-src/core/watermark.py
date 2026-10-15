"""
全自动视频水印检测与画面净化模块
基于 PyAV + NumPy 时域静止特征与时间线黑边自适应检测，结合 FFmpeg 原生滤镜执行秒级智能消除
"""

import os
import re
import subprocess
from typing import Optional, Tuple, List, Dict, Any, Union
import av
import numpy as np


class WatermarkDetector:
    @staticmethod
    def detect_watermark_timeline(video_path: str) -> List[Dict[str, Any]]:
        """
        基于时间线黑边与画面比例跳变，多段自适应检测视频各时间段的水印。
        返回: [{'box': (x, y, w, h), 't_start': float, 't_end': float}, ...]
        """
        try:
            container = av.open(video_path)
            if not container.streams.video:
                return []

            stream = container.streams.video[0]
            width = stream.width
            height = stream.height
            if width <= 0 or height <= 0:
                return []

            duration = float(stream.duration * stream.time_base) if stream.duration else 60.0
            if duration <= 2.0:
                return []

            # 1. 沿时间线粗测黑边变化（步长 1.0s），检测画面比例分段
            step = 1.0
            ts_list = np.arange(0.5, duration, step)
            history = []
            for ts in ts_list:
                try:
                    container.seek(int(ts / stream.time_base), stream=stream)
                    for frame in container.decode(stream):
                        arr = frame.to_ndarray(format="gray")
                        top_black = len(np.where(arr[0:min(120, height // 4), :].max(axis=1) < 15)[0])
                        history.append((ts, top_black))
                        break
                except Exception:
                    continue

            if not history:
                return []

            # 聚合成稳定分段
            segments = []
            seg_start = 0.0
            curr_black = history[0][1]
            for ts, b in history[1:]:
                if abs(b - curr_black) > 10:
                    segments.append((seg_start, ts, curr_black))
                    seg_start = ts
                    curr_black = b
            segments.append((seg_start, duration, curr_black))

            # 2. 对每个片段采样检测静态水印
            timeline_boxes = []
            for t_start, t_end, top_black in segments:
                seg_dur = t_end - t_start
                if seg_dur < 2.0:
                    continue

                sample_count = min(6, max(3, int(seg_dur // 5)))
                sample_ts = np.linspace(t_start + 0.5, t_end - 0.5, sample_count)
                frames = []
                for ts in sample_ts:
                    try:
                        container.seek(int(ts / stream.time_base), stream=stream)
                        for frame in container.decode(stream):
                            frames.append(frame.to_ndarray(format="gray"))
                            break
                    except Exception:
                        continue

                if len(frames) < 3:
                    continue

                arr_3d = np.array(frames)
                # 扫描区域：右上角（考虑当前分段顶部黑边偏移）
                y_s = max(0, top_black)
                y_e = min(height, top_black + int(height * 0.16))
                x_s = int(width * 0.55)
                x_e = width - 4

                if y_e <= y_s or x_e <= x_s:
                    continue

                roi = arr_3d[:, y_s:y_e, x_s:x_e]
                # 统计持续高亮（>=190）的像素
                bright_frames = np.sum(roi > 190, axis=0) >= max(2, len(frames) // 2)
                row_counts = np.sum(bright_frames, axis=1)

                # 聚类连续密集行（有效行阈值 20 像素）
                is_dense = row_counts >= 20
                clusters = []
                c_start = None
                for i, d in enumerate(is_dense):
                    if d and c_start is None:
                        c_start = i
                    elif not d and c_start is not None:
                        if i - c_start >= 8:
                            clusters.append((c_start, i - 1))
                        c_start = None
                if c_start is not None and len(is_dense) - c_start >= 8:
                    clusters.append((c_start, len(is_dense) - 1))

                for c_y_min, c_y_max in clusters:
                    h = c_y_max - c_y_min
                    if 8 <= h <= 65:
                        text_slice = bright_frames[c_y_min:c_y_max+1, :]
                        col_counts = np.sum(text_slice, axis=0)
                        valid_cols = np.where(col_counts >= 2)[0]
                        if len(valid_cols) >= 30:
                            c_x_min, c_x_max = valid_cols.min(), valid_cols.max()
                            w = c_x_max - c_x_min
                            if 25 <= w <= int(width * 0.48):
                                pad_x, pad_y = 8, 4
                                clean_x = max(1, x_s + c_x_min - pad_x)
                                clean_y = max(1, y_s + c_y_min - pad_y)
                                clean_w = min(width - clean_x - 2, w + pad_x * 2)
                                clean_h = min(height - clean_y - 2, h + pad_y * 2)

                                timeline_boxes.append({
                                    'box': (int(clean_x), int(clean_y), int(clean_w), int(clean_h)),
                                    't_start': round(float(t_start), 2),
                                    't_end': round(float(t_end), 2)
                                })
                                break

            return timeline_boxes
        except Exception:
            return []

    @staticmethod
    def detect_static_watermark(video_path: str) -> Optional[Tuple[int, int, int, int]]:
        """
        向后兼容接口：全自动检测视频静态创作者水印单框。
        如果存在多段，则返回首个检测到的有效水印框。
        """
        boxes = WatermarkDetector.detect_watermark_timeline(video_path)
        if boxes:
            return boxes[0]['box']
        return None


class VideoCleaner:
    @staticmethod
    def build_filter_chain(
        watermark_box: Optional[Union[Tuple[int, int, int, int], List[Dict[str, Any]]]] = None,
        remove_subtitles: bool = False,
        video_width: int = 0,
        video_height: int = 0,
        enhance_quality: bool = False,
    ) -> List[str]:
        """
        构建严格符合图像处理黄金顺序的滤镜链：
        升位 (10-bit) -> 瑕疵消除 (delogo, 支持 timeline) -> 细节降噪 (atadenoise) -> 调色 (eq) ->
        自适应超采 (scale+lanczos+bt709) -> 去色带 (deband) -> 亮度微锐化 (unsharp) -> 8-bit 输出
        """
        filters: List[str] = []

        if enhance_quality:
            # 1. 强制升至 10-bit 内部管道，防止后续复杂的计算导致色带断层 (Banding)
            filters.append("format=yuv420p10le")

        # 2. 瑕疵优先在最纯净的原始分辨率上消除（避免被放大或降噪涂抹后边缘扩散）
        if watermark_box:
            if isinstance(watermark_box, list):
                # 时间线分段 delogo 模式
                for item in watermark_box:
                    x, y, w, h = item['box']
                    t_s = item.get('t_start')
                    t_e = item.get('t_end')
                    if t_s is not None and t_e is not None:
                        filters.append(f"delogo=x={x}:y={y}:w={w}:h={h}:enable='between(t,{t_s},{t_e})':show=0")
                    else:
                        filters.append(f"delogo=x={x}:y={y}:w={w}:h={h}:show=0")
            elif isinstance(watermark_box, tuple):
                x, y, w, h = watermark_box
                filters.append(f"delogo=x={x}:y={y}:w={w}:h={h}:show=0")

        if remove_subtitles and video_width > 0 and video_height > 0:
            sub_y = int(video_height * 0.82)
            sub_h = int(video_height * 0.16)
            filters.append(f"delogo=x=10:y={sub_y}:w={video_width - 20}:h={sub_h}:show=0")

        if enhance_quality:
            # 3. 在原始分辨率做动态细节降噪（atadenoise 避免 hqdn3d 的运动鬼影与涂抹）
            filters.append("atadenoise=0a=0.08:0b=0.08:1a=0.06:1b=0.06")
            # 4. 在干净画面上微调对比度与饱和度，避免暗部噪点被提亮放大
            filters.append("eq=contrast=1.05:saturation=1.05")
            # 5. 长宽自适应超采插值（最大宽1920，短边偶数自适应）+ BT.709 高清色彩空间校正
            filters.append("scale='min(1920,iw*2)':'-2':flags=lanczos:in_color_matrix=auto:out_color_matrix=bt709")
            # 6. 消除插值放大产生的微弱台阶纹
            filters.append("deband=1thr=0.03:2thr=0.03:range=16:blur=true")
            # 7. 纯亮度反锐化掩模，不锐化色度，防止边缘产生白色 halo 光晕
            filters.append("unsharp=5:5:0.8:3:3:0.0")
            # 8. 末端平滑降阶为通用 8-bit YUV420P，兼顾 10-bit 中间运算防色带优势与 100% 播放兼容性
            filters.append("format=yuv420p")

        return filters

    @staticmethod
    def clean_video(
        input_mp4: str,
        output_dir: str,
        remove_watermark: bool = True,
        remove_subtitles: bool = False,
        enhance_quality: bool = False,
    ) -> Tuple[str, bool, bool]:
        """
        执行视频画面净化与画质增强。
        返回: (最终视频路径, 是否实际检测并消除了水印, 是否实际执行了画质增强)
        """
        if not os.path.exists(input_mp4):
            return input_mp4, False, False

        watermark_detected = False
        wm_boxes = None
        if remove_watermark:
            timeline_res = WatermarkDetector.detect_watermark_timeline(input_mp4)
            if timeline_res:
                wm_boxes = timeline_res
                watermark_detected = True

        vw, vh = 0, 0
        if remove_subtitles:
            try:
                container = av.open(input_mp4)
                stream = container.streams.video[0]
                vw, vh = stream.width, stream.height
            except Exception:
                pass

        filter_list = VideoCleaner.build_filter_chain(
            watermark_box=wm_boxes,
            remove_subtitles=remove_subtitles,
            video_width=vw,
            video_height=vh,
            enhance_quality=enhance_quality,
        )

        # 如果既没有检测到水印，也没有要求去字幕，且未开启增强，直接保留原视频
        if not filter_list:
            return input_mp4, False, False

        # 构造输出文件名（去掉可能存在的后缀时间戳，保持文件名清爽）
        raw_name = os.path.splitext(os.path.basename(input_mp4))[0]
        base_name = re.sub(r'_\d{9,12}$', '', raw_name)
        # 若原文件名自带 _clean，则先规范化
        clean_base = re.sub(r'_clean$', '', base_name)
        suffix = "_clean_enhanced.mp4" if enhance_quality else "_clean.mp4"
        output_mp4 = os.path.join(output_dir, f"{clean_base}{suffix}")

        vf_str = ",".join(filter_list)
        if enhance_quality:
            # 启用慢速高保真 x264 编码，输出通用 yuv420p 兼顾全设备播放
            cmd = [
                "ffmpeg", "-i", input_mp4,
                "-vf", vf_str,
                "-c:v", "libx264",
                "-preset", "slow",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "copy",
                "-y", output_mp4
            ]
        else:
            # 快速仅去水印模式
            cmd = [
                "ffmpeg", "-i", input_mp4,
                "-vf", vf_str,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "21",
                "-c:a", "copy",
                "-y", output_mp4
            ]

        try:
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0 and os.path.exists(output_mp4):
                return output_mp4, watermark_detected, enhance_quality
        except Exception:
            pass

        return input_mp4, False, False
