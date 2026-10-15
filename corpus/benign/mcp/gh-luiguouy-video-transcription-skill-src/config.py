"""
配置管理模块
基于 Pydantic Settings 实现环境变量自动加载与验证
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Whisper 模型规格: tiny, base, small, medium, large-v3 (本地运行建议 base 或 small)
    WHISPER_MODEL_SIZE: str = "base"
    # 计算设备: "auto", "cuda" (有N卡), "cpu" (无显卡)
    WHISPER_DEVICE: str = "auto"
    # 计算精度: GPU 建议 "float16", CPU 建议 "int8" 或 "default"
    WHISPER_COMPUTE_TYPE: str = "default"
    # 本地模型缓存目录（可选，指定后模型将下载到此目录）
    WHISPER_MODEL_DIR: Optional[str] = None

    # 网络与安全
    DOWNLOAD_TIMEOUT: int = 180
    HTTP_PROXY: Optional[str] = None
    HTTPS_PROXY: Optional[str] = None
    COOKIES_FILE_PATH: Optional[str] = None
    # 直接从浏览器读取 cookies，支持 "auto"（自动依次探测 edge/chrome/firefox）、逗号分隔列表（如 "edge,chrome"）或单一浏览器名
    COOKIES_FROM_BROWSER: Optional[str] = "auto"

    # 媒体文件持久化保存目录（默认保存在 downloads 目录，由用户决定删除）
    DOWNLOADS_DIR: str = "downloads"

    # 并发与资源调度配置
    MAX_CONCURRENT_TASKS: int = 3          # 默认最大并行处理任务数
    MAX_CONCURRENT_DOWNLOADS: int = 4      # 网络 I/O 阶段最大并发数
    MAX_CONCURRENT_RENDERS: int = 1        # 视频滤镜/画质增强阶段最大并发数（防止 CPU 100% 卡顿）
    MAX_CONCURRENT_TRANSCRIBES: int = 1    # Whisper 模型推理阶段最大并发数（防显存/内存 OOM）

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
