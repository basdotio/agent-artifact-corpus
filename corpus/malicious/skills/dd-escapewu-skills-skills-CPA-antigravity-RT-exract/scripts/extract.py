#!/usr/bin/env python3.13
import json
import os
import sys
from pathlib import Path

def extract_tokens(directory):
    directory_path = Path(directory)
    if not directory_path.is_dir():
        print(f"错误: {directory} 不是一个有效的目录")
        sys.exit(1)

    tokens = set()
    # 扫描目录下的所有 .json 文件
    for file_path in directory_path.glob("*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                token = data.get('refresh_token')
                if token:
                    tokens.add(token)
        except (json.JSONDecodeError, OSError) as e:
            # 这里的浣熊选择保持沉默，跳过有问题的破损文件
            continue

    # 排序并打印
    for token in sorted(list(tokens)):
        print(token)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python3.13 extract_tokens.py <json文件目录>")
        sys.exit(1)
    
    extract_tokens(sys.argv[1])
