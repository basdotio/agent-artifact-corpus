# -*- coding: utf-8 -*-
"""
render_terminal.py
大学通用实验报告专用 - 高保真终端截图生成器 (High-Fidelity Terminal Screenshot Generator)
支持 Cisco CLI / Packet Tracer PC 命令行、Windows CMD、PowerShell、Linux Bash
使用 Pillow 纯代码本地渲染 100% 锐利、绝对无乱码的专业控制台实测图。
"""

import os
import sys
import argparse
from PIL import Image, ImageDraw, ImageFont

def get_font(size, is_bold=False):
    # 常用 Windows / 通用系统等宽字体
    font_candidates = [
        "consola.ttf", "consolab.ttf" if is_bold else "consola.ttf",
        r"C:\Windows\Fonts\consola.ttf",
        r"C:\Windows\Fonts\consolab.ttf" if is_bold else r"C:\Windows\Fonts\consola.ttf",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\msyh.ttc"
    ]
    for font_name in font_candidates:
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            continue
    return ImageFont.load_default()

def render_terminal(output_path, term_type="cisco", title="PC0 - Command Prompt", lines=None, width=900, min_height=420):
    if lines is None:
        lines = [
            "Packet Tracer PC Command Line 1.0",
            "PC> ipconfig",
            "FastEthernet0 IP Address................: 192.168.1.2",
            "Subnet Mask.............................: 255.255.255.0",
            "Default Gateway.........................: 192.168.1.1",
            "",
            "PC> ping 192.168.2.2",
            "Pinging 192.168.2.2 with 32 bytes of data:",
            "Reply from 192.168.2.2: bytes=32 time=9ms TTL=127",
            "Reply from 192.168.2.2: bytes=32 time=8ms TTL=127",
            "Reply from 192.168.2.2: bytes=32 time=8ms TTL=127",
            "Reply from 192.168.2.2: bytes=32 time=9ms TTL=127",
            "",
            "Ping statistics for 192.168.2.2:",
            "    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),",
            "Approximate round trip times in milli-seconds:",
            "    Minimum = 8ms, Maximum = 9ms, Average = 8ms",
            "",
            "PC> _"
        ]
        
    font_size = 15
    line_height = 22
    header_height = 36
    padding_x = 18
    padding_y = 14
    
    calc_height = header_height + padding_y * 2 + len(lines) * line_height
    height = max(min_height, calc_height)
    
    img = Image.new("RGB", (width, height), color=(12, 12, 12))
    draw = ImageDraw.Draw(img)
    
    font_main = get_font(font_size)
    font_title = get_font(13, is_bold=True)
    
    # 标题栏风格
    if term_type == "cisco":
        header_bg = (45, 45, 48)
        title_color = (220, 220, 220)
    elif term_type == "cmd":
        header_bg = (30, 30, 30)
        title_color = (255, 255, 255)
    elif term_type == "powershell":
        header_bg = (1, 36, 86)
        title_color = (255, 255, 255)
    else: # linux
        header_bg = (35, 35, 35)
        title_color = (210, 210, 210)
        
    draw.rectangle([0, 0, width, header_height], fill=header_bg)
    draw.line([0, header_height, width, header_height], fill=(60, 60, 60), width=1)
    
    # 标题文字
    draw.text((16, 9), title, fill=title_color, font=font_title)
    
    # 窗口控制按钮 (右上角)
    btn_y = 12
    draw.rectangle([width - 80, btn_y + 6, width - 68, btn_y + 8], fill=(180, 180, 180)) # 最小化
    draw.rectangle([width - 52, btn_y, width - 40, btn_y + 12], outline=(180, 180, 180), width=1) # 最大化
    draw.line([width - 24, btn_y, width - 14, btn_y + 10], fill=(220, 80, 80), width=2) # 关闭
    draw.line([width - 14, btn_y, width - 24, btn_y + 10], fill=(220, 80, 80), width=2)
    
    # 绘制内容文本
    curr_y = header_height + padding_y
    for line in lines:
        if term_type == "linux" and ("$" in line or "#" in line or "@" in line):
            # 简单 Linux prompt 着色
            parts = line.split("$", 1)
            if len(parts) == 2:
                prompt_part = parts[0] + "$"
                cmd_part = parts[1]
                draw.text((padding_x, curr_y), prompt_part, fill=(0, 210, 100), font=font_main)
                prompt_w = draw.textlength(prompt_part, font=font_main)
                draw.text((padding_x + prompt_w, curr_y), cmd_part, fill=(240, 240, 240), font=font_main)
            else:
                draw.text((padding_x, curr_y), line, fill=(210, 210, 210), font=font_main)
        elif "Error" in line or "Failed" in line or "loss)" in line and "0% loss" not in line:
            draw.text((padding_x, curr_y), line, fill=(240, 80, 80), font=font_main)
        elif "Reply from" in line or "bytes=" in line or "bytes of data" in line:
            draw.text((padding_x, curr_y), line, fill=(180, 230, 180), font=font_main)
        elif line.startswith("PC>") or line.startswith("Router>") or line.startswith("Switch#") or line.startswith("C:\\"):
            draw.text((padding_x, curr_y), line, fill=(255, 255, 255), font=font_main)
        else:
            draw.text((padding_x, curr_y), line, fill=(215, 215, 215), font=font_main)
        curr_y += line_height
        
    # 外边框
    draw.rectangle([0, 0, width - 1, height - 1], outline=(55, 55, 55), width=1)
    
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img.save(output_path)
    print(f"[Success] Rendered high-fidelity terminal shot: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="High-Fidelity Terminal Screenshot Generator")
    parser.add_argument("--type", choices=["cisco", "cmd", "powershell", "linux"], default="cisco", help="Terminal theme style")
    parser.add_argument("--title", default="Command Prompt", help="Window title text")
    parser.add_argument("--commands", help="Comma-separated commands or file path to lines")
    parser.add_argument("--output", required=True, help="Output PNG image path")
    args = parser.parse_args()
    
    lines = None
    if args.commands:
        if os.path.exists(args.commands):
            with open(args.commands, "r", encoding="utf-8") as f:
                lines = [line.rstrip() for line in f]
        else:
            lines = [c.strip() for c in args.commands.split(",")]
            
    render_terminal(args.output, term_type=args.type, title=args.title, lines=lines)

if __name__ == "__main__":
    main()
