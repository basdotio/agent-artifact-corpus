#!/bin/bash
# 用法: bash word_count.sh "文件路径" 或 bash word_count.sh --text "文本内容"
# 返回字数统计（纯中文计法）

if [ "$1" = "--text" ]; then
    text="$2"
else
    text=$(cat "$1" 2>/dev/null)
fi

# 统计中文字符+中文标点+字母+数字（忽略空格和纯英文标点）
count=$(echo "$text" | sed 's/ //g' | sed 's/\r//g' | grep -oP '[\x{4e00}-\x{9fff}]|[\x{3000}-\x{303f}]|[\x{ff00}-\x{ffef}]|[a-zA-Z0-9]' | wc -l)

echo "$count"
