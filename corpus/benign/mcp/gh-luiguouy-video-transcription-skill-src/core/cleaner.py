"""
文本过滤与标点规范化模块
负责 URL 净化、中文字符空格消除、标点规整及多尺度时间戳格式化
"""

import os
import re
import urllib.request
from typing import List, Any


class TextCleaner:
    @staticmethod
    def extract_url(raw_input: str) -> str:
        """
        从用户可能混杂分享文案的输入中提取有效 URL，并进行短链解析处理；
        若输入为本地存在的音视频文件路径，则直接清洗并返回规范路径。
        示例: "7.28 03/12 S@s.xy cLg:/ 惊呆了！ https://v.douyin.com/ieABC/ 复制此链接..."
        """
        cleaned_input = raw_input.strip().strip('"').strip("'")
        if os.path.isfile(cleaned_input):
            return cleaned_input

        url_pattern = r"(https?://[^\s，。]+)"
        match = re.search(url_pattern, raw_input)
        if not match:
            return cleaned_input

        url = match.group(1).strip()

        # 针对短链（如 v.douyin.com / b23.tv / vt.tiktok.com 等）尝试解析重定向后的完整地址
        if any(short_domain in url for short_domain in ["v.douyin.com", "b23.tv", "t.co", "vt.tiktok.com"]):
            try:
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
                        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
                    )
                }
                req = urllib.request.Request(url, headers=headers, method="HEAD")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    resolved_url = resp.geturl()
                    if resolved_url:
                        return resolved_url
            except Exception:
                # 若网络解析短链失败，回退返回原始提取 URL 交由 yt-dlp 处理
                pass

        return url

    @staticmethod
    def to_fluent_paragraph(segments: List[Any]) -> str:
        """
        清理转写碎片中的多余空格，补全标点符号，整合为通顺自然的单一段落。
        """
        raw_text = "".join([seg.text.strip() for seg in segments if getattr(seg, "text", "").strip()])
        if not raw_text:
            return ""

        # 清除中文字符间的孤立空格（保留英文单词之间自然空格）
        text = re.sub(r"(?<=[\u4e00-\u9fa5])\s+(?=[\u4e00-\u9fa5])", "", raw_text)
        # 合并连续多余的标点
        text = re.sub(r"([，。！？,.!?])\1+", r"\1", text)
        # 英文标点本地化为中文全角标点
        text = text.replace(",", "，").replace("?", "？").replace("!", "！")

        # 保证段落末尾有完整句末标点
        if text and text[-1] not in "。！？":
            text += "。"

        return text

    @staticmethod
    def to_timestamped_lines(segments: List[Any]) -> str:
        """
        输出带有时间分界的行切片（智能支持时/分/秒，兼容长视频）。
        """
        lines = []
        for seg in segments:
            content = getattr(seg, "text", "").strip()
            if not content:
                continue

            start_sec = getattr(seg, "start", 0.0)
            end_sec = getattr(seg, "end", 0.0)

            h_start, rem_start = divmod(start_sec, 3600)
            m_start, s_start = divmod(rem_start, 60)

            h_end, rem_end = divmod(end_sec, 3600)
            m_end, s_end = divmod(rem_end, 60)

            # 若时长超过 1 小时，使用标准 HH:MM:SS.xx 格式，否则使用 MM:SS.xx 格式
            if h_start > 0 or h_end > 0:
                time_tag = f"[{int(h_start):02d}:{int(m_start):02d}:{s_start:05.2f} -> {int(h_end):02d}:{int(m_end):02d}:{s_end:05.2f}]"
            else:
                time_tag = f"[{int(m_start):02d}:{s_start:05.2f} -> {int(m_end):02d}:{s_end:05.2f}]"

            lines.append(f"{time_tag} {content}")

        return "\n".join(lines)
