#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apply_cover_text.py — 把 AI 插画处理成卡面底图：裁水印带 → 平方裁切 → 缩放 768 → 暗角渐变 + 标题文字

用法:
    python scripts/apply_cover_text.py <输入图> [输出图=底图.png] [--title "都 市 暗 涌"] [--sub "副标题"]

处理要点:
  * 底部约 9.5% 与右侧约 4.5% 为平台水印区，裁掉
  * 结果固定 768x768
  * 底部暗部渐变 + 标题区柔和暗版，保证白字可读
  * 重影层必须先画、正字后画——ImageDraw 在 RGBA 上是覆盖不是混合，顺序反了字会发花
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

W = H = 768
TITLE = "都 市 暗 涌"
SUB = "她只是想把论文写完"


def pick_font(candidates, size):
    for path in candidates:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def process(src, out, title=TITLE, sub=SUB):
    im = Image.open(src).convert("RGB")
    w0, h0 = im.size
    bottom_cut = int(h0 * 0.095)
    right_cut = int(w0 * 0.045)
    left_cut = int(w0 * 0.015)
    im = im.crop((left_cut, 0, w0 - right_cut, h0 - bottom_cut))
    w1, h1 = im.size
    s = min(w1, h1)
    x0 = (w1 - s) // 2
    im = im.crop((x0, 0, x0 + s, s))
    im = im.resize((W, H), Image.LANCZOS)

    def grad_alpha(y):
        y0, y1, y2 = int(H * 0.65), int(H * 0.795), H
        if y < y0:
            return 0
        if y < y1:
            return int(150 * (y - y0) / (y1 - y0))
        return int(150 + 95 * (y - y1) / (y2 - y1))

    grad = Image.new("L", (1, H), 0)
    gd = ImageDraw.Draw(grad)
    for y in range(H):
        gd.point((0, y), fill=grad_alpha(y))
    grad = grad.resize((W, H))
    im = Image.composite(Image.new("RGB", (W, H), (6, 8, 13)), im, grad).convert("RGBA")

    plate = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(plate)
    pd.rounded_rectangle([140, 582, W - 140, 732], radius=64, fill=(7, 9, 14, 120))
    plate = plate.filter(ImageFilter.GaussianBlur(28))
    im = Image.alpha_composite(im, plate).convert("RGB")

    title_font = pick_font(
        ["C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"], 62
    )
    sub_font = pick_font(["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"], 22)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    td = ImageDraw.Draw(layer)
    bbox = td.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    ty = int(H * 0.795)
    td.text(((W - tw) / 2, ty + 4), title, font=title_font, fill=(236, 241, 247, 30))  # 重影须先画
    td.text(((W - tw) / 2, ty), title, font=title_font, fill=(250, 252, 255, 252),
            stroke_width=3, stroke_fill=(8, 10, 16, 170))
    bbox2 = td.textbbox((0, 0), sub, font=sub_font)
    sw = bbox2[2] - bbox2[0]
    td.text(((W - sw) / 2, ty + 94), sub, font=sub_font, fill=(214, 223, 234, 180),
            stroke_width=2, stroke_fill=(8, 10, 16, 130))
    im = Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")

    im.save(out, "PNG")
    print(f"[输出] {out}（{W}x{H}）")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    title = TITLE
    sub = SUB
    for flag in ("--title", "--sub"):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                sys.exit(f"参数错误: {flag} 后面缺一个值（用 {flag} \"文字\" 传入）")
            if flag == "--title":
                title = args[i + 1]
            else:
                sub = args[i + 1]
            del args[i:i + 2]
    src = args[0]
    out = args[1] if len(args) > 1 else "底图.png"
    process(src, out, title, sub)
