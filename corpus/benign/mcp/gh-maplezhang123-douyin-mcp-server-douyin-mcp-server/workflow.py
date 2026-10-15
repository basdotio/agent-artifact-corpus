"""Douyin extraction workflow shared by the CLI, WebUI and MCP server."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import ffmpeg
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1"}
CAPTURE_SCRIPT = Path(__file__).with_name("capture_douyin.js")
SILICONFLOW_ASR_URL = "https://api.siliconflow.cn/v1/audio/transcriptions"
SILICONFLOW_ASR_MODEL = "FunAudioLLM/SenseVoiceSmall"
ProgressCallback = Optional[Callable[[str], None]]


def _progress(callback: ProgressCallback, message: str) -> None:
    if callback:
        callback(message)


def source_url(share_text: str) -> str:
    match = re.search(r"https?://[^\s<>]+", share_text)
    if not match:
        raise ValueError("无法解析视频 ID：未找到有效的抖音链接")
    return match.group(0).rstrip("。),，]}>\"'")


def extract_video_id(text: str) -> str:
    for pattern in (r"/video/(\d+)", r"[?&]modal_id=(\d+)", r"[?&]aweme_id=(\d+)", r"[?&]item_ids=(\d+)"):
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    match = re.search(r"\b(\d{16,22})\b", text)
    return match.group(1) if match else ""


def parse_share_url_http(share_text: str) -> dict:
    """Resolve a share URL with the fast legacy HTTP parser."""
    share_url = source_url(share_text)
    share_response = requests.get(share_url, headers=HEADERS, allow_redirects=True, timeout=20)
    share_response.raise_for_status()
    video_id = extract_video_id(share_response.url) or extract_video_id(share_url)
    if not video_id:
        raise ValueError("无法解析视频 ID")
    response = requests.get(f"https://www.iesdouyin.com/share/video/{video_id}", headers=HEADERS, timeout=30)
    response.raise_for_status()
    match = re.search(r"window\._ROUTER_DATA\s*=\s*(.*?)</script>", response.text, re.DOTALL)
    if not match:
        raise ValueError("HTTP 页面中没有 _ROUTER_DATA")
    try:
        loader = json.loads(match.group(1).strip())["loaderData"]
        page = loader.get("video_(id)/page") or loader.get("note_(id)/page")
        item = page["videoInfoRes"]["item_list"][0]
        video_url = item["video"]["play_addr"]["url_list"][0].replace("playwm", "play")
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("HTTP 页面中没有可用的 videoInfoRes") from exc
    title = re.sub(r'[\\/:*?"<>|]', "_", item.get("desc", "").strip())
    return {"url": video_url, "title": title or f"douyin_{video_id}", "video_id": video_id,
            "resolved_url": share_response.url, "source": "http"}


def run_browser_capture(url: str, audio_path: Optional[Path]) -> dict:
    if not CAPTURE_SCRIPT.is_file():
        raise RuntimeError("浏览器采集脚本不存在，请重新安装项目")
    node = os.getenv("DOUYIN_NODE_PATH", "").strip() or shutil.which("node")
    if not node:
        raise RuntimeError("未检测到 Node.js，请安装 Node.js 18+ 并重新打开终端")
    env = os.environ.copy()
    env.update({"DOUYIN_CAPTURE_URL": url, "DOUYIN_AUDIO_PATH": str(audio_path) if audio_path else "",
                "DOUYIN_DOWNLOAD_AUDIO": "1" if audio_path else "0"})
    try:
        process = subprocess.run([node, str(CAPTURE_SCRIPT)], capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", env=env, timeout=180)
    except FileNotFoundError as exc:
        raise RuntimeError("配置的 Node.js 路径不可用") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("浏览器采集超时，请检查网络后重试") from exc
    match = re.search(r"DOUYIN_CAPTURE_JSON=(\{.*\})", process.stdout or "")
    if not match:
        detail = (process.stderr or process.stdout or "无输出").strip()
        raise RuntimeError(f"浏览器采集未返回结果：{detail[-500:]}")
    result = json.loads(match.group(1))
    if not result.get("ok"):
        raise RuntimeError(result.get("error") or "浏览器采集失败")
    return result


def resolve_video_info(share_text: str) -> dict:
    try:
        return parse_share_url_http(share_text)
    except Exception as exc:
        url = source_url(share_text)
        result = run_browser_capture(url, None)
        return {"url": "", "title": result.get("title", ""),
                "video_id": result.get("video_id") or extract_video_id(result.get("final_url", url)),
                "resolved_url": result.get("final_url", url), "source": "browser", "http_error": str(exc)}


def download_video(video_info: dict, destination: Path) -> None:
    response = requests.get(video_info["url"], headers=HEADERS, stream=True, timeout=60)
    response.raise_for_status()
    with destination.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                handle.write(chunk)
    if not destination.stat().st_size:
        raise RuntimeError("音频抓取失败：下载的视频为空")


def extract_audio(video_path: Path, audio_path: Path) -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("未检测到 ffmpeg，请安装后重新打开终端")
    try:
        ffmpeg.input(str(video_path)).output(str(audio_path), vn=None, acodec="aac", audio_bitrate="128k").run(
            capture_stdout=True, capture_stderr=True, overwrite_output=True)
    except (ffmpeg.Error, FileNotFoundError) as exc:
        detail = getattr(exc, "stderr", b"")
        if isinstance(detail, bytes):
            detail = detail.decode("utf-8", errors="replace")
        raise RuntimeError(f"ffmpeg 提取音频失败：{detail or exc}") from exc


def probe_audio(audio_path: Path) -> dict:
    if not audio_path.is_file() or not audio_path.stat().st_size:
        raise RuntimeError("音频为空")
    if not shutil.which("ffprobe"):
        raise RuntimeError("未检测到 ffmpeg/ffprobe，请安装后重新打开终端")
    try:
        probe = ffmpeg.probe(str(audio_path))
        duration = float(probe.get("format", {}).get("duration", 0))
    except (ffmpeg.Error, FileNotFoundError, ValueError) as exc:
        raise RuntimeError(f"ffprobe 校验音频失败：{exc}") from exc
    if duration <= 0:
        raise RuntimeError("音频为空或时长无效")
    return {"duration": duration, "size": audio_path.stat().st_size,
            "format_name": probe.get("format", {}).get("format_name", "")}


def convert_for_cloud(source_path: Path, mp3_path: Path) -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("未检测到 ffmpeg，请安装后重新打开终端")
    try:
        ffmpeg.input(str(source_path)).output(str(mp3_path), acodec="libmp3lame", audio_bitrate="64k", ac=1, ar=16000).run(
            capture_stdout=True, capture_stderr=True, overwrite_output=True)
    except (ffmpeg.Error, FileNotFoundError) as exc:
        raise RuntimeError(f"转换云端 ASR 音频失败：{exc}") from exc


def split_cloud_audio(audio_path: Path, target_dir: Path, segment_duration: int = 1800) -> list[Path]:
    info = probe_audio(audio_path)
    if info["duration"] <= 3500 and info["size"] <= 45 * 1024 * 1024:
        return [audio_path]
    parts, start = [], 0.0
    while start < info["duration"]:
        part = target_dir / f"segment_{len(parts):03d}.mp3"
        try:
            ffmpeg.input(str(audio_path), ss=start, t=segment_duration).output(
                str(part), acodec="libmp3lame", audio_bitrate="64k", ac=1, ar=16000).run(
                capture_stdout=True, capture_stderr=True, overwrite_output=True)
        except ffmpeg.Error as exc:
            raise RuntimeError(f"切分云端 ASR 音频失败：{exc}") from exc
        parts.append(part)
        start += segment_duration
    return parts


def transcribe_single_siliconflow(audio_path: Path, api_key: str) -> str:
    try:
        with audio_path.open("rb") as audio_file:
            response = requests.post(SILICONFLOW_ASR_URL, headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (audio_path.name, audio_file, "audio/mpeg"), "model": (None, SILICONFLOW_ASR_MODEL)}, timeout=180)
    except requests.RequestException as exc:
        raise RuntimeError(f"SiliconFlow 网络请求失败：{exc}") from exc
    if response.status_code in (401, 403):
        raise RuntimeError("SiliconFlow API Key 无效")
    if response.status_code != 200:
        raise RuntimeError(f"SiliconFlow 请求失败（HTTP {response.status_code}）：{response.text[:300]}")
    try:
        text = str(response.json().get("text", "")).strip()
    except (ValueError, AttributeError) as exc:
        raise RuntimeError("SiliconFlow 返回了无法解析的数据") from exc
    if not text:
        raise RuntimeError("ASR 返回空结果")
    return text


def _write_transcript(path: Path, text: str) -> None:
    path.write_text(f"# 原始逐字稿\n\n{text}\n", encoding="utf-8")


def transcribe_cloud_siliconflow(audio_path: Path, transcript_path: Path, api_key: Optional[str] = None) -> dict:
    key = (api_key or os.getenv("SILICONFLOW_API_KEY", "")).strip()
    if not key:
        raise RuntimeError("SiliconFlow API Key 未填写（请设置 SILICONFLOW_API_KEY）")
    with tempfile.TemporaryDirectory(prefix="douyin-cloud-asr-") as temp_name:
        temp_dir = Path(temp_name)
        cloud_mp3 = temp_dir / "speech.mp3"
        convert_for_cloud(audio_path, cloud_mp3)
        parts = split_cloud_audio(cloud_mp3, temp_dir)
        texts = [transcribe_single_siliconflow(part, key) for part in parts]
    final_text = "\n".join(text.strip() for text in texts if text.strip()).strip()
    if not final_text:
        raise RuntimeError("ASR 返回空结果")
    _write_transcript(transcript_path, final_text)
    return {"engine": "siliconflow", "model": SILICONFLOW_ASR_MODEL, "segment_count": len(texts),
            "character_count": len(final_text), "text": final_text}


def local_model_path(model_name: str, hub: Optional[Path] = None) -> Optional[Path]:
    root = Path(hub or os.getenv("DOUYIN_MODEL_HUB") or os.getenv("HF_HOME") or Path.home() / ".cache" / "huggingface" / "hub")
    repo = root / f"models--Systran--faster-whisper-{model_name}"
    ref = repo / "refs" / "main"
    if ref.is_file():
        snapshot = repo / "snapshots" / ref.read_text(encoding="utf-8").strip()
        if snapshot.is_dir():
            return snapshot
    return None


def transcribe_local(audio_path: Path, transcript_path: Path, model_name: str = "small") -> dict:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("本地 Whisper 未安装，请运行 uv sync --extra local") from exc
    model_source: str | Path = local_model_path(model_name) or model_name
    try:
        model = WhisperModel(str(model_source), device=os.getenv("DOUYIN_WHISPER_DEVICE", "cpu"),
            compute_type=os.getenv("DOUYIN_WHISPER_COMPUTE_TYPE", "int8"), download_root=os.getenv("DOUYIN_MODEL_HUB") or None)
        segments, info = model.transcribe(str(audio_path), vad_filter=True)
        texts = [segment.text.strip() for segment in segments if segment.text.strip()]
    except Exception as exc:
        raise RuntimeError("本地 Whisper 加载或识别失败。可设置 DOUYIN_MODEL_HUB，或联网让模型自动下载。"
                           f"详情：{exc}") from exc
    text = "".join(texts).strip()
    if not text:
        raise RuntimeError("ASR 返回空结果")
    _write_transcript(transcript_path, text)
    return {"engine": "faster-whisper", "model": model_name, "language": getattr(info, "language", None),
            "segment_count": len(texts), "character_count": len(text), "text": text}


def organize_with_deepseek(transcript: str, title: str, purpose: str = "rewrite", api_key: Optional[str] = None) -> dict:
    key = (api_key or os.getenv("DEEPSEEK_API_KEY", "") or os.getenv("DOUYIN_DEEPSEEK_API_KEY", "")).strip()
    if not key:
        raise RuntimeError("DeepSeek API Key 未填写")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    try:
        response = requests.post(f"{os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com').rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [
                {"role": "system", "content": "忠实保留原意，只去口水词和重复，修正明显同音字，补充标点与分段。不要虚构，只输出整理后的文案。"},
                {"role": "user", "content": f"标题：{title}\n用途：{purpose}\n\n逐字稿：\n{transcript}"}]},
            timeout=float(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "90")))
        response.raise_for_status()
        payload = response.json()
        text = payload["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        raise RuntimeError(f"DeepSeek 文案整理失败：{exc}") from exc
    if not text:
        raise RuntimeError("DeepSeek 返回了空文案")
    return {"model": model, "text": text, "usage": payload.get("usage", {})}


def run_verified_workflow(share_text: str, output_base: str | Path, purpose: str = "rewrite",
        model_name: str = "small", siliconflow_api_key: Optional[str] = None,
        deepseek_api_key: Optional[str] = None, asr_mode: Optional[str] = None,
        progress: ProgressCallback = None) -> dict:
    mode = (asr_mode or os.getenv("DOUYIN_ASR_MODE", "cloud")).strip().lower()
    if mode not in {"cloud", "local"}:
        raise ValueError("DOUYIN_ASR_MODE 只能是 cloud 或 local")
    url, stages, http_error, browser_result = source_url(share_text), [], "", {}
    started = datetime.now().astimezone()
    with tempfile.TemporaryDirectory(prefix="douyin-workflow-") as temp_name:
        temp_dir, temp_audio = Path(temp_name), Path(temp_name) / "audio.m4a"
        _progress(progress, "正在解析链接")
        try:
            video_info = parse_share_url_http(share_text)
            stages.append({"stage": "parse", "status": "http-ok"})
            video_path = temp_dir / f"{video_info['video_id']}.mp4"
            _progress(progress, "正在下载音频")
            download_video(video_info, video_path)
            extract_audio(video_path, temp_audio)
            stages.extend(({"stage": "download", "status": "video-ok"}, {"stage": "audio", "status": "ffmpeg-ok"}))
        except Exception as exc:
            http_error = str(exc)
            _progress(progress, "正在启动浏览器降级")
            stages.append({"stage": "parse", "status": "browser-fallback"})
            browser_result = run_browser_capture(url, temp_audio)
            video_info = {"url": "", "title": browser_result.get("title", ""),
                "video_id": browser_result.get("video_id") or extract_video_id(browser_result.get("final_url", url)),
                "resolved_url": browser_result.get("final_url", url), "source": "browser"}
            stages.extend(({"stage": "download", "status": "browser-audio-ok"}, {"stage": "audio", "status": "direct-audio"}))
        video_id = video_info.get("video_id") or datetime.now().strftime("%Y%m%d-%H%M%S")
        output_dir = Path(output_base) / video_id
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_path = output_dir / "audio.m4a"
        shutil.copy2(temp_audio, audio_path)

    audio_probe = probe_audio(audio_path)
    transcript_path = output_dir / "transcript-raw.md"
    if mode == "cloud":
        _progress(progress, "正在上传 SenseVoice")
        asr = transcribe_cloud_siliconflow(audio_path, transcript_path, siliconflow_api_key)
        stages.append({"stage": "asr", "status": "siliconflow-ok"})
    else:
        _progress(progress, "正在运行本地 Whisper")
        asr = transcribe_local(audio_path, transcript_path, model_name)
        stages.append({"stage": "asr", "status": "local-ok"})
    raw_text, final_text = asr["text"], asr["text"]
    organizer, organizer_error = {"model": "none", "usage": {}}, ""
    deepseek_key = (deepseek_api_key or os.getenv("DEEPSEEK_API_KEY", "") or os.getenv("DOUYIN_DEEPSEEK_API_KEY", "")).strip()
    if deepseek_key:
        _progress(progress, "正在整理文案")
        try:
            organizer = organize_with_deepseek(raw_text, video_info.get("title", ""), purpose, deepseek_key)
            final_text = organizer["text"]
            stages.append({"stage": "organize", "status": "deepseek-ok"})
        except Exception as exc:
            organizer_error = f"DeepSeek 文案整理失败：{exc}"
            stages.append({"stage": "organize", "status": "deepseek-failed-raw-kept"})
    else:
        stages.append({"stage": "organize", "status": "skipped-no-key"})
    copy_path = output_dir / "copy.md"
    copy_path.write_text(f"# 提取后的文案\n\n{final_text}\n", encoding="utf-8")
    metadata = {"source_url": url, "resolved_url": video_info.get("resolved_url", url),
        "video_id": video_info.get("video_id", ""), "title": video_info.get("title", ""),
        "captured_at": started.isoformat(timespec="seconds"), "source": video_info.get("source", "http")}
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    elapsed = (datetime.now().astimezone() - started).total_seconds()
    report = {"workflow_version": 5, "status": "completed", "elapsed_seconds": round(elapsed, 2), "stages": stages,
        "http_error": http_error, "organizer_error": organizer_error, "audio_probe": audio_probe,
        "asr": {key: value for key, value in asr.items() if key != "text"}, "organizer": organizer,
        "artifacts": {"audio": str(audio_path), "transcript_raw": str(transcript_path), "copy": str(copy_path), "metadata": str(metadata_path)}}
    report_path = output_dir / "run-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _progress(progress, "完成")
    return {"video_info": video_info, "text": final_text, "raw_text": raw_text,
        "organized_text": final_text if final_text != raw_text else "", "asr_mode": mode, "asr_model": asr["model"],
        "elapsed_seconds": round(elapsed, 2), "output_path": str(output_dir), "run_report_path": str(report_path),
        "organizer_error": organizer_error, "status": "completed"}
