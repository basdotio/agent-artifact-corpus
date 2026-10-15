#!/usr/bin/env python3
"""
【小北Aiven】公众号创作技能 V2.0 —— 发布脚本

功能：
  1. 读取 Markdown，渲染为「罗辑思维风格」微信 HTML
  2. 自动追加固定结尾引导块
  3. 处理封面图（本地路径 / 网络 URL / 默认），自动压缩到 ≤64KB
  4. 发布到微信公众号草稿箱
  5. 本地保存 HTML 预览
  6. 自动回读校验（确认无中文乱码）

用法：
  python publish.py <md文件> "<标题>" [作者] [封面图路径或URL]

凭证来源（按优先级）：
  1. 环境变量 WX_APPID / WX_SECRET
  2. 配置文件 ~/.workbuddy/.wx_config  （JSON: {"AppID": "...", "AppSecret": "..."}）

运行环境：必须使用带 Pillow 的 python
  /Users/aiven/.workbuddy/binaries/python/envs/default/bin/python
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ----------------------------------------------------------------------------
# 配置
# ----------------------------------------------------------------------------
CONFIG_PATH = Path.home() / ".workbuddy" / ".wx_config"

# 默认封面（永久素材 media_id）
DEFAULT_THUMB_MEDIA_ID = "rRdlQ0gFDUx_rxXZcd7Vh4cgyHLNLqgWfV3_KjsFLstFqZpk2clh1UIjbNSqQmvm"

AUTHOR = "小北Aiven"

ORANGE = "#e36c09"
FONT_FAMILY = ('-apple-system, BlinkMacSystemFont, "PingFangSC-Light", '
               '"PingFang SC", "Microsoft YaHei", sans-serif')


def load_credentials():
    """按优先级读取 AppID / AppSecret"""
    appid = os.environ.get("WX_APPID")
    secret = os.environ.get("WX_SECRET")
    if appid and secret:
        return appid, secret
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return cfg.get("AppID") or cfg.get("appid"), cfg.get("AppSecret") or cfg.get("secret")
        except Exception as e:
            print(f"⚠️ 读取配置文件失败: {e}")
    print("❌ 未找到微信凭证。请设置环境变量 WX_APPID / WX_SECRET，")
    print(f"   或在 {CONFIG_PATH} 写入 {{\"AppID\": \"...\", \"AppSecret\": \"...\"}}")
    sys.exit(1)


# ----------------------------------------------------------------------------
# 微信 API
# ----------------------------------------------------------------------------
def get_access_token(appid, secret):
    r = subprocess.run(
        ["curl", "-s",
         f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={secret}"],
        capture_output=True, text=True)
    data = json.loads(r.stdout)
    if "access_token" not in data:
        print(f"❌ 获取 access_token 失败: {data}")
        sys.exit(1)
    return data["access_token"]


def download_image(url):
    import tempfile
    ext = ".png" if ".png" in url.lower() else ".jpg"
    tmp = tempfile.mktemp(suffix=ext)
    subprocess.run(["curl", "-s", "-L", "-o", tmp, url], capture_output=True, text=True, timeout=60)
    if os.path.exists(tmp) and os.path.getsize(tmp) > 1000:
        print(f"✅ 图片下载成功")
        return tmp
    print("⚠️ 图片下载失败，改用默认封面")
    return None


def compress_cover(input_path):
    """裁剪为 900x383 并压缩到 <=64KB"""
    import tempfile
    from PIL import Image

    tmp = tempfile.mktemp(suffix=".jpg")
    img = Image.open(input_path)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")

    # 先按 2.35:1 居中裁剪，避免变形
    w, h = img.size
    target_ratio = 900 / 383
    new_h = int(w / target_ratio)
    if new_h <= h:
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))
    img = img.resize((900, 383), Image.Resampling.LANCZOS)

    for q in [95, 90, 85, 80, 75, 70, 65, 60, 55, 50]:
        img.save(tmp, "JPEG", quality=q, optimize=True)
        if os.path.getsize(tmp) / 1024 <= 64:
            break
    return tmp


def upload_cover(path_or_url, token):
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        print("🌐 检测到网络图片，正在下载...")
        local = download_image(path_or_url)
        if not local:
            return DEFAULT_THUMB_MEDIA_ID
        path_or_url = local

    print("🖼️ 正在裁剪并压缩封面...")
    tmp = compress_cover(path_or_url)
    print(f"✅ 封面压缩完成: {os.path.getsize(tmp)/1024:.1f}KB")

    try:
        r = subprocess.run(
            ["curl", "-s", "-X", "POST",
             f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image",
             "-F", f"media=@{tmp}"],
            capture_output=True, text=True)
        resp = json.loads(r.stdout)
        if "media_id" in resp:
            print(f"✅ 封面上传成功")
            return resp["media_id"]
        print(f"⚠️ 封面上传失败: {resp}，改用默认封面")
        return DEFAULT_THUMB_MEDIA_ID
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ----------------------------------------------------------------------------
# Markdown → 微信 HTML（罗辑思维风格）
# ----------------------------------------------------------------------------
ENDING_HTML = '''
<div style="text-align:center;padding:35px 25px;background:#f9f9f9;border-radius:8px;margin-top:45px;">
    <p style="color:#666;font-size:15px;line-height:2.2;margin:0 0 12px 0;"><strong>谢谢你看到这里~~</strong></p>
    <p style="color:#666;font-size:14px;line-height:2;margin:0 0 12px 0;">这里不只聊 AI，也陪你一起慢慢成长。</p>
    <p style="color:#666;font-size:14px;line-height:2;margin:0 0 12px 0;"><strong>如果今天的内容对你有启发，欢迎点赞、在看、转发三连支持～</strong></p>
    <p style="color:#666;font-size:14px;line-height:2;margin:0 0 12px 0;">怕错过更新？记得点击「小北学AI」名片，设为星标⭐，我们下次准时相见。</p>
    <p style="color:#666;font-size:14px;line-height:2;margin:0 0 12px 0;"><strong>愿我们眼里有光，心中有方向，在 AI 与成长的路上，一路同行。</strong></p>
    <p style="color:#888;font-size:12px;line-height:1.8;margin:12px 0 0 0;">/ 作者：小北Aiven</p>
    <p style="color:#888;font-size:12px;line-height:1.8;margin:0;">/ 交流合作可联系邮箱：tong1025619710@126.com</p>
</div>'''


def process_inline(text):
    """行内格式：加粗、斜体、图片"""
    text = re.sub(r'\*\*(.*?)\*\*', f'<strong style="color:{ORANGE};font-weight:bold;">\\1</strong>', text)

    def img_replace(m):
        alt, url = m.group(1).strip(), m.group(2).strip()
        style = ('display:block;margin:32px auto;max-width:100%;border-radius:6px;'
                 'box-shadow:0 2px 8px rgba(0,0,0,0.10);text-align:center;line-height:0;')
        return f'<img src="{url}" alt="{alt}" style="{style}" />'

    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', img_replace, text)
    text = re.sub(r'(?<!\*)\*([^*\[\]]+?)\*(?!\*)', r'<em>\1</em>', text)
    return text


def render_md(md_file):
    content = Path(md_file).read_text(encoding="utf-8")

    # 移除 front matter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2]

    paragraphs, buf = [], []
    for line in content.split("\n"):
        line = line.rstrip()
        if line.strip():
            buf.append(line)
        elif buf:
            paragraphs.append("\n".join(buf))
            buf = []
    if buf:
        paragraphs.append("\n".join(buf))

    parts = []
    for idx, para in enumerate(paragraphs):
        para = para.strip()
        if not para:
            continue

        # 显式标题
        if para.startswith("## "):
            t = process_inline(para[3:].strip())
            parts.append(
                f'<div style="margin:40px 0 30px 0;">'
                f'<p style="font-size:19px;font-weight:bold;color:#1a1a1a;'
                f'border-left:5px solid {ORANGE};padding-left:14px;margin:0;line-height:1.7;">{t}</p></div>')
            continue

        # 引用块 / 首段 → 引言块
        if para.startswith("> ") or idx == 0:
            t = process_inline(para[2:].strip() if para.startswith("> ") else para)
            parts.append(
                f'<blockquote style="background:#f2f2f2;border-left:5px solid {ORANGE};'
                f'padding:16px 20px;margin:28px 0;font-size:15px;color:#333;line-height:2;'
                f'text-align:justify;">{t}</blockquote>')
            continue

        # 普通段落
        t = process_inline(para)
        parts.append(
            f'<p style="margin:24px 0;line-height:2;color:#333;font-size:15px;'
            f'text-align:justify;">{t}</p>')

    parts.append(ENDING_HTML)
    return (f'<section style="font-family:{FONT_FAMILY};line-height:2;font-size:15px;'
            f'color:#333;padding:0 5px;">{"".join(parts)}</section>')


# ----------------------------------------------------------------------------
# 发布 + 校验
# ----------------------------------------------------------------------------
def create_draft(token, title, content, thumb_media_id):
    plain = re.sub(r"<[^>]+>", "", content).replace("\n", " ").strip()
    digest = plain[:54] + "..." if len(plain) > 54 else plain

    data = {"articles": [{
        "title": title,
        "author": AUTHOR,
        "digest": digest,
        "content": content,
        "content_source_url": "",
        "thumb_media_id": thumb_media_id,
        "need_open_comment": 1,
        "only_fans_can_comment": 0,
    }]}

    # 【防乱码条件 1】ensure_ascii=False
    with open("/tmp/draft.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    # 【防乱码条件 2】--data-binary   【条件 3】charset=utf-8
    r = subprocess.run(
        ["curl", "-s", "-X", "POST",
         f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}",
         "-H", "Content-Type: application/json; charset=utf-8",
         "--data-binary", "@/tmp/draft.json"],
        capture_output=True, text=True)
    return json.loads(r.stdout)


def verify_draft(token, media_id):
    with open("/tmp/get.json", "w", encoding="utf-8") as f:
        json.dump({"media_id": media_id}, f, ensure_ascii=False)
    r = subprocess.run(
        ["curl", "-s", "-X", "POST",
         f"https://api.weixin.qq.com/cgi-bin/draft/get?access_token={token}",
         "-H", "Content-Type: application/json; charset=utf-8",
         "--data-binary", "@/tmp/get.json"],
        capture_output=True, text=True)
    if "\\u" in r.stdout:
        print("⚠️ 警告：响应中存在 \\u 转义，可能乱码")
    d = json.loads(r.stdout)
    if "news_item" in d:
        it = d["news_item"][0]
        print("\n📋 回读校验：")
        print(f"   标题：{it['title']}")
        print(f"   作者：{it.get('author')}")
        print(f"   摘要：{it.get('digest')}")
        print(f"   正文：{len(it['content'])} 字符")
        print(f"   封面：{it.get('thumb_media_id','')[:24]}...")
        print("   ✅ 校验通过，无中文乱码" if "\\u" not in r.stdout else "   ⚠️ 存在转义")
        return it
    print(f"⚠️ 回读失败: {d}")
    return None


def main():
    if len(sys.argv) < 3:
        print("用法: python publish.py <md文件> \"<标题>\" [作者] [封面图路径或URL]")
        sys.exit(1)

    md_file = sys.argv[1]
    title = sys.argv[2]
    cover = sys.argv[4] if len(sys.argv) > 4 else None

    appid, secret = load_credentials()

    print(f"📝 渲染: {md_file}")
    print(f"📌 标题: {title}")
    html = render_md(md_file)

    # 本地保存预览
    preview = Path(md_file).with_name(Path(md_file).stem + "_draft_preview.html")
    preview.write_text(
        f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>{title}</title></head>'
        f'<body style="max-width:680px;margin:0 auto;padding:24px;background:#fff;">{html}</body></html>',
        encoding="utf-8")
    print(f"✅ 已生成预览: {preview}")

    print("🔑 获取 access_token...")
    token = get_access_token(appid, secret)

    thumb = upload_cover(cover, token) if cover else DEFAULT_THUMB_MEDIA_ID
    if not cover:
        print("ℹ️ 未提供封面，使用默认封面")

    print("📤 发布到草稿箱...")
    result = create_draft(token, title, html, thumb)

    if "media_id" in result:
        mid = result["media_id"]
        print(f"✅ 发布成功! Media ID: {mid}")
        verify_draft(token, mid)
    else:
        print(f"❌ 发布失败: {result}")
        sys.exit(1)


if __name__ == "__main__":
    main()
