"""
媒体抓取与音频提取模块
利用 yt-dlp 与底层 FFmpeg 将网络音视频抓取并统一转码为 16kHz 单声道 WAV
"""

import os
import re
import time
import urllib.request
import subprocess
from typing import Dict, Any, Tuple, Optional
import yt_dlp
from src.config import settings


import threading


class MediaExtractor:
    _cached_browser_info: Optional[Tuple[Optional[str], float]] = None
    _cookie_lock = threading.Lock()

    @staticmethod
    def get_system_default_browser() -> Optional[str]:
        """
        探测当前操作系统设置的默认网页浏览器（Windows 注册表 / 系统配置）
        返回规范的浏览器标识：'chrome', 'edge', 'firefox', 'brave' 等
        """
        import sys
        if sys.platform == "win32":
            try:
                import winreg
                reg_path = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
                    prog_id, _ = winreg.QueryValueEx(key, "ProgId")
                    prog_lower = (prog_id or "").lower()
                    if "chrome" in prog_lower:
                        return "chrome"
                    elif "edge" in prog_lower or "msedge" in prog_lower:
                        return "edge"
                    elif "firefox" in prog_lower:
                        return "firefox"
                    elif "brave" in prog_lower:
                        return "brave"
            except Exception:
                pass
        elif sys.platform == "darwin":
            try:
                import subprocess
                cmd = ["defaults", "read", "com.apple.LaunchServices/com.apple.launchservices.secure", "LSHandlers"]
                out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
                if "chrome" in out.lower():
                    return "chrome"
                elif "edge" in out.lower():
                    return "edge"
                elif "firefox" in out.lower():
                    return "firefox"
            except Exception:
                pass
        return None

    @classmethod
    def _resolve_cookie_options(cls) -> Dict[str, Any]:
        """
        多浏览器（Edge、Chrome、Firefox）智能自动探测与平滑回退
        1. 优先探测当前宿主机系统设置的【默认浏览器】（Default Browser），并将其置于最高优先级；
        2. 若候选浏览器可读取且未被独占锁死，自动配置 cookiesfrombrowser；
        3. 若候选浏览器被占用锁死或读取异常，自动平滑测试下一候选；
        4. 全部落空后平滑回退到本地 cookies.txt；若亦无则免 Cookie 直连，杜绝崩溃。
        5. 内置 60 秒轻量级探测缓存，防止并发批处理时反复探测造成开销。
        """
        now = time.time()
        with cls._cookie_lock:
            if cls._cached_browser_info is not None:
                cached_browser, cache_time = cls._cached_browser_info
                if now - cache_time < 60:
                    options = {}
                    if cached_browser:
                        options["cookiesfrombrowser"] = (cached_browser, None)
                    else:
                        cookie_file = settings.COOKIES_FILE_PATH or os.path.join(os.getcwd(), "cookies.txt")
                        if os.path.exists(cookie_file):
                            options["cookiefile"] = cookie_file
                    return options

            browser_conf = (settings.COOKIES_FROM_BROWSER or "").strip()
            if not browser_conf or browser_conf.lower() in ("auto", "all", "*"):
                # 优先探测当前用户的系统默认浏览器！
                default_browser = cls.get_system_default_browser()
                base_candidates = ["chrome", "edge", "firefox", "brave"]
                if default_browser and default_browser in base_candidates:
                    candidates = [default_browser] + [b for b in base_candidates if b != default_browser]
                else:
                    candidates = base_candidates
            else:
                candidates = [b.strip().lower() for b in browser_conf.split(",") if b.strip()]
                for fallback in ["chrome", "edge", "firefox"]:
                    if fallback not in candidates:
                        candidates.append(fallback)

            from yt_dlp.cookies import extract_cookies_from_browser
            matched_browser = None
            for b in candidates:
                try:
                    extract_cookies_from_browser(b)
                    matched_browser = b
                    break
                except Exception:
                    continue

            cls._cached_browser_info = (matched_browser, now)

            options = {}
            if matched_browser:
                options["cookiesfrombrowser"] = (matched_browser, None)
            else:
                cookie_file = settings.COOKIES_FILE_PATH or os.path.join(os.getcwd(), "cookies.txt")
                if os.path.exists(cookie_file):
                    options["cookiefile"] = cookie_file

            return options

    @classmethod
    def _extract_via_tikwm(cls, url: str, output_dir: str, temp_id: str, proxy: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        TikTok 官方高风控/敏感限制视频备选通道 (TikWM API)
        免登录解析并下载无水印/超清 MP4 原画
        """
        import httpx
        client_kwargs = {"timeout": 30, "verify": False}
        if proxy:
            client_kwargs["proxy"] = proxy

        with httpx.Client(**client_kwargs) as client:
            resp = client.post("https://www.tikwm.com/api/", data={"url": url, "hd": 1})
            data = resp.json()
            if data.get("code") != 0 or not data.get("data"):
                raise ValueError(f"TikWM 解析失败: {data.get('msg', '未知错误')}")

            item = data["data"]
            video_url = item.get("hdplay") or item.get("play") or item.get("wmplay")
            if not video_url:
                raise ValueError("TikWM 未提供有效视频下载直链")

            raw_title = item.get("title") or item.get("content_desc") or f"tiktok_{item.get('id', temp_id)}"
            target_temp_mp4 = os.path.join(output_dir, f"temp_{temp_id}.mp4")

            with client.stream("GET", video_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}) as r:
                r.raise_for_status()
                with open(target_temp_mp4, "wb") as f:
                    for chunk in r.iter_bytes(chunk_size=65536):
                        f.write(chunk)

            meta = {
                "id": str(item.get("id", "")),
                "title": raw_title,
                "duration": item.get("duration", 0),
                "uploader": (item.get("author") or {}).get("nickname") or (item.get("author") or {}).get("unique_id"),
                "uploader_id": (item.get("author") or {}).get("unique_id"),
                "music_info": item.get("music_info", {}),
            }
            return target_temp_mp4, meta

    @classmethod
    def extract_media(cls, url: str, output_dir: str) -> Tuple[str, Optional[str], Dict[str, Any]]:
        """
        通过 yt-dlp 抓取完整 MP4 视频，并借助本地 FFmpeg 转码为 16kHz 单声道 WAV 格式。
        同时将 MP4 原画视频与 WAV 音频持久化保存在指定的 output_dir 目录中。
        返回: (target_wav, target_mp4, meta)
        """
        os.makedirs(output_dir, exist_ok=True)

        import uuid
        temp_id = f"{int(time.time())}_{uuid.uuid4().hex[:6]}"
        out_template = os.path.join(output_dir, f"temp_{temp_id}.%(ext)s")

        # 兼容用户直接传入本地音视频文件路径
        import shutil
        clean_path = url.strip().strip('"').strip("'")
        if os.path.isfile(clean_path):
            safe_title = os.path.splitext(os.path.basename(clean_path))[0]
            safe_title = re.sub(r'[\\/*?:"<>|\r\n\t]', '_', safe_title).strip()[:50]
            target_mp4 = os.path.join(output_dir, f"{safe_title}_{temp_id}.mp4")
            target_wav = os.path.join(output_dir, f"{safe_title}_{temp_id}.wav")

            # 拷贝一份到统一下载持久化目录
            shutil.copy2(clean_path, target_mp4)

            # 提取 16kHz 单声道 WAV
            cmd = [
                "ffmpeg", "-i", target_mp4,
                "-ar", "16000", "-ac", "1",
                "-vn", "-y", target_wav
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # 探测视频时长
            duration = 0.0
            try:
                probe_cmd = [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", target_mp4
                ]
                res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                if res.stdout.strip():
                    duration = float(res.stdout.strip())
            except Exception:
                pass

            meta = {
                "id": temp_id,
                "title": safe_title,
                "duration": duration,
                "uploader": "local_file"
            }
            return target_wav, target_mp4, meta

        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": out_template,
            "merge_output_format": "mp4",
            "socket_timeout": settings.DOWNLOAD_TIMEOUT,
            "quiet": True,
            "no_warnings": True,
            # 现代化 JS 挑战求解器（突破 YouTube 等平台的高强度 bot/n-sig 校验）
            "remote_components": ["ejs:github"],
            "js_runtimes": {"node": {}},
        }

        # 智能代理分流：国内平台（抖音、B站）强制直连，国外平台优先使用 settings 或系统环境变量/系统网络代理
        is_domestic = any(d in url for d in ["douyin.com", "bilibili.com", "b23.tv", "iesdouyin.com"])
        sys_proxies = urllib.request.getproxies()
        discovered_proxy = (
            settings.HTTP_PROXY
            or os.environ.get("HTTP_PROXY")
            or os.environ.get("http_proxy")
            or sys_proxies.get("http")
            or sys_proxies.get("https")
        )

        if is_domestic:
            ydl_opts["proxy"] = ""
            proxy_url = None
        else:
            if discovered_proxy:
                ydl_opts["proxy"] = discovered_proxy
            proxy_url = discovered_proxy

        # 智能多浏览器探测与 Cookies 兼容策略 (Edge / Chrome / Firefox 自动适配与平滑降级)
        cookie_opts = cls._resolve_cookie_options()
        ydl_opts.update(cookie_opts)

        meta = None
        downloaded_file = None

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                meta = ydl.extract_info(url, download=True)
        except Exception as e:
            # 针对 TikTok 的高风控/需要登录受限视频，自动回退到 TikWM 解析服务
            if "tiktok.com" in url or "vt.tiktok" in url:
                try:
                    downloaded_file, meta = cls._extract_via_tikwm(
                        url=url,
                        output_dir=output_dir,
                        temp_id=temp_id,
                        proxy=proxy_url
                    )
                except Exception as fallback_err:
                    raise RuntimeError(f"yt-dlp 提取失败: {e}，且 TikWM 备选通道解析失败: {fallback_err}") from fallback_err
            else:
                raise

        raw_title = (meta or {}).get("title", f"media_{temp_id}")
        safe_title = re.sub(r'[\\/*?:"<>|\r\n\t]', '_', raw_title).strip()[:50]

        # 寻找下载生成的原始视频文件
        if not downloaded_file:
            for ext in ["mp4", "mkv", "webm", "flv"]:
                candidate = os.path.join(output_dir, f"temp_{temp_id}.{ext}")
                if os.path.exists(candidate):
                    downloaded_file = candidate
                    break

            if not downloaded_file:
                for f in os.listdir(output_dir):
                    if f.startswith(f"temp_{temp_id}"):
                        downloaded_file = os.path.join(output_dir, f)
                        break

        target_mp4 = os.path.join(output_dir, f"{safe_title}_{temp_id}.mp4")
        target_wav = os.path.join(output_dir, f"{safe_title}_{temp_id}.wav")

        # 重命名为规范命名的 MP4 视频
        if downloaded_file and os.path.exists(downloaded_file):
            os.rename(downloaded_file, target_mp4)
        else:
            target_mp4 = None

        # 从完整视频提取 16kHz WAV
        input_source = target_mp4 if (target_mp4 and os.path.exists(target_mp4)) else downloaded_file
        if input_source and os.path.exists(input_source):
            cmd = [
                "ffmpeg", "-i", input_source,
                "-ar", "16000", "-ac", "1",
                "-vn", "-y", target_wav
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            raise FileNotFoundError("音频转换失败，未能找到视频目标文件。")

        return target_wav, target_mp4, meta

    # 兼容原接口
    @classmethod
    def extract_audio(cls, url: str, output_dir: str) -> Tuple[str, Dict[str, Any]]:
        wav_path, _, meta = cls.extract_media(url, output_dir)
        return wav_path, meta
