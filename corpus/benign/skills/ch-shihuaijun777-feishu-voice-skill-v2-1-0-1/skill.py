#!/usr/bin/env python3
"""
飞书语音气泡发送技能
使用 edge-tts 生成语音，通过飞书发送语音气泡消息
"""

import argparse
import os
import sys
import tempfile
import subprocess
import json
import requests
import asyncio
import edge_tts

# 默认配置
DEFAULT_OPEN_ID = "ou_xxxxxxxxxxxxxxxx"
DEFAULT_APP_ID = "cli_xxxxxxxxxxxxxxxx"
DEFAULT_APP_SECRET = "********************************"
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"

# 飞书 API 地址
FEISHU_BASE_URL = "https://open.feishu.cn/open-apis"
FEISHU_UPLOAD_URL = f"{FEISHU_BASE_URL}/drive/v1/medias/upload_all"
FEISHU_SEND_MSG_URL = f"{FEISHU_BASE_URL}/im/v1/messages"


def get_tenant_access_token(app_id: str, app_secret: str) -> str:
    """获取 tenant_access_token"""
    url = f"{FEISHU_BASE_URL}/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    data = {"app_id": app_id, "app_secret": app_secret}
    
    response = requests.post(url, headers=headers, json=data, timeout=30)
    response.raise_for_status()
    result = response.json()
    
    if result.get("code") != 0:
        raise Exception(f"获取 token 失败: {result.get('msg')}")
    
    return result["tenant_access_token"]


async def generate_speech(text: str, voice: str, output_path: str):
    """使用 edge-tts 生成语音"""
    print(f"[TTS] 正在生成语音，音色: {voice}")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    print(f"[TTS] 语音已生成: {output_path}")


def convert_to_opus(input_path: str, output_path: str):
    """使用 ffmpeg 将音频转换为 opus 格式（48kHz, 64kbps）"""
    print(f"[FFmpeg] 正在转换音频格式: {input_path} -> {output_path}")
    
    cmd = [
        "ffmpeg",
        "-y",                    # 覆盖输出文件
        "-i", input_path,        # 输入文件
        "-ar", "48000",          # 采样率 48kHz
        "-ac", "1",              # 单声道
        "-b:a", "64k",           # 比特率 64kbps
        "-c:a", "libopus",       # 使用 opus 编码器
        output_path              # 输出文件
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"ffmpeg 转换失败: {result.stderr}")
    
    print(f"[FFmpeg] 转换完成: {output_path}")


def upload_file(file_path: str, token: str, app_id: str) -> str:
    """上传文件到飞书，获取 file_key"""
    print(f"[Upload] 正在上传文件: {file_path}")
    
    url = FEISHU_UPLOAD_URL
    headers = {"Authorization": f"Bearer {token}"}
    
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)
    
    with open(file_path, "rb") as f:
        files = {
            "file": (file_name, f, "audio/opus")
        }
        data = {
            "file_name": file_name,
            "parent_type": "message_attachment",
            "parent_id": app_id,
            "size": str(file_size)
        }
        
        response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
    
    response.raise_for_status()
    result = response.json()
    
    if result.get("code") != 0:
        raise Exception(f"文件上传失败: {result.get('msg')}")
    
    file_key = result["data"]["file_key"]
    print(f"[Upload] 上传成功，file_key: {file_key}")
    return file_key


def send_voice_message(token: str, receive_id: str, file_key: str, msg_type: str = "audio") -> str:
    """发送语音气泡消息"""
    print(f"[Send] 正在发送语音消息给: {receive_id}")
    
    url = FEISHU_SEND_MSG_URL
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    # 接收者类型，open_id 为用户
    receive_id_type = "open_id"
    
    payload = {
        "receive_id": receive_id,
        "receive_id_type": receive_id_type,
        "msg_type": msg_type,
        "content": json.dumps({"file_key": file_key})
    }
    
    params = {"receive_id_type": receive_id_type}
    
    response = requests.post(url, headers=headers, json=payload, params=params, timeout=30)
    response.raise_for_status()
    result = response.json()
    
    if result.get("code") != 0:
        raise Exception(f"消息发送失败: {result.get('msg')}")
    
    message_id = result.get("data", {}).get("message_id", "")
    print(f"[Send] 消息发送成功，message_id: {message_id}")
    return message_id


def close_browser_processes():
    """关闭浏览器相关进程"""
    print("[Cleanup] 正在关闭浏览器进程...")
    try:
        # 尝试关闭常见浏览器进程
        browsers = ["chrome", "msedge", "firefox", "iexplore"]
        for browser in browsers:
            subprocess.run(
                f"taskkill /F /IM {browser}.exe",
                capture_output=True,
                text=False
            )
    except Exception as e:
        print(f"[Cleanup] 关闭浏览器进程时出现警告: {e}")


def main():
    parser = argparse.ArgumentParser(description="飞书语音气泡发送工具")
    parser.add_argument("--text", required=True, help="要转换的文本内容")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help=f"音色名称（默认: {DEFAULT_VOICE}）")
    parser.add_argument("--open-id", default=DEFAULT_OPEN_ID, help=f"目标用户 open_id（默认: {DEFAULT_OPEN_ID}）")
    parser.add_argument("--app-id", default=DEFAULT_APP_ID, help=f"飞书 App ID（默认: {DEFAULT_APP_ID}）")
    parser.add_argument("--app-secret", default=DEFAULT_APP_SECRET, help="飞书 App Secret")
    parser.add_argument("--keep-temp", action="store_true", help="保留临时文件（不删除）")
    
    args = parser.parse_args()
    
    temp_dir = None
    mp3_path = None
    opus_path = None
    
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="feishu_voice_")
        mp3_path = os.path.join(temp_dir, "voice.mp3")
        opus_path = os.path.join(temp_dir, "voice.opus")
        
        print("=" * 50)
        print("飞书语音气泡发送工具")
        print("=" * 50)
        print(f"文本内容: {args.text}")
        print(f"音色: {args.voice}")
        print(f"目标用户: {args.open_id}")
        print("-" * 50)
        
        # Step 1: 生成语音
        asyncio.run(generate_speech(args.text, args.voice, mp3_path))
        
        # Step 2: 转换格式
        convert_to_opus(mp3_path, opus_path)
        
        # Step 3: 获取 token
        print("[Auth] 正在获取飞书访问令牌...")
        [REDACTED_SECRET], args.app_secret)
        
        # Step 4: 上传文件
        file_key = upload_file(opus_path, token, args.app_id)
        
        # Step 5: 发送消息
        message_id = send_voice_message(token, args.open_id, file_key)
        
        print("-" * 50)
        print(f"✅ 发送成功！message_id: {message_id}")
        print("=" * 50)
        
        # 关闭浏览器进程
        close_browser_processes()
        
        return 0
        
    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        return 1
        
    finally:
        # 清理临时文件
        if not args.keep_temp and temp_dir and os.path.exists(temp_dir):
            import shutil
            try:
                shutil.rmtree(temp_dir)
                print(f"[Cleanup] 已清理临时目录: {temp_dir}")
            except Exception as e:
                print(f"[Cleanup] 清理临时文件失败: {e}")


if __name__ == "__main__":
    sys.exit(main())
