#!/bin/bash
# 生成角色设定图（三视图）
# 使用 Vidu reference2image/nano API + q3-fast 模型
# 原创角色使用白底图，复刻角色使用搜索到的人物照片
# 三视图固定使用 16:9 横屏比例

set -e

# 检查环境变量
if [ -z "$VIDU_KEY" ]; then
  echo "=========================================="
  echo "⚠️  未检测到 Vidu API Key"
  echo "=========================================="
  echo ""
  echo "请提供你的 Vidu API Key："
  echo "  export VIDU_KEY=\"你的key\""
  echo ""
  echo "获取方式："
  echo "  1. 访问 https://platform.vidu.cn"
  echo "  2. 注册/登录账号"
  echo "  3. 在控制台获取 API Key"
  echo ""
  exit 1
fi

# 照片目录（复刻角色专用）
PHOTO_DIR="$HOME/.openclaw/workspace/skills/partner-creator/assets/photos"

# 白底图路径（原创角色专用）
BLANK_CANVAS="$HOME/.openclaw/workspace/skills/partner-creator/assets/blank-canvas.jpg"

# 检查是否有参数
MODE="${1:-auto}"  # auto/original/remake

# 根据模式选择参考图
if [ "$MODE" = "original" ]; then
  # 原创角色模式：使用白底图
  if [ ! -f "$BLANK_CANVAS" ]; then
    echo "❌ 未找到白底图: $BLANK_CANVAS"
    exit 1
  fi
  PHOTOS=("$BLANK_CANVAS")
  echo "🎨 原创角色模式：使用白底图"
  
elif [ "$MODE" = "remake" ]; then
  # 复刻角色模式：使用搜索到的照片
  if [ ! -d "$PHOTO_DIR" ] || [ -z "$(ls -A $PHOTO_DIR/*.jpg $PHOTO_DIR/*.png $PHOTO_DIR/*.webp 2>/dev/null)" ]; then
    echo "❌ 未找到人物照片"
    echo "请先使用 search-images-tavily.mjs 搜索并下载角色照片"
    exit 1
  fi
  
  # 收集所有照片
  PHOTOS=()
  for ext in jpg png webp jpeg JPG PNG WEBP JPEG; do
    for photo in "$PHOTO_DIR"/*."$ext"; do
      if [ -f "$photo" ]; then
        PHOTOS+=("$photo")
      fi
    done
  done
  echo "📷 复刻角色模式：使用 ${#PHOTOS[@]} 张参考照片"
  
else
  # 自动模式：优先使用照片，没有则用白底图
  if [ -d "$PHOTO_DIR" ] && [ -n "$(ls -A $PHOTO_DIR/*.jpg $PHOTO_DIR/*.png $PHOTO_DIR/*.webp 2>/dev/null)" ]; then
    PHOTOS=()
    for ext in jpg png webp jpeg JPG PNG WEBP JPEG; do
      for photo in "$PHOTO_DIR"/*."$ext"; do
        if [ -f "$photo" ]; then
          PHOTOS+=("$photo")
        fi
      done
    done
    echo "📷 自动模式：使用 ${#PHOTOS[@]} 张参考照片"
  elif [ -f "$BLANK_CANVAS" ]; then
    PHOTOS=("$BLANK_CANVAS")
    echo "🎨 自动模式：使用白底图（原创角色）"
  else
    echo "❌ 未找到参考图或白底图"
    echo "请先下载照片或创建白底图"
    exit 1
  fi
fi

PHOTO_COUNT=${#PHOTOS[@]}

echo "============================================"
echo "生成角色设定图（三视图）"
echo "============================================"
echo "检测到 $PHOTO_COUNT 张参考照片"
echo ""

# 固定提示词
PROMPT="Character reference sheet with 4 views: 1) Frontal close-up portrait showing clear face and facial features, head facing camera directly, eyes looking at viewer. 2) Full body front view standing. 3) Full body side view standing. 4) Full body back view standing. All views show same person with identical appearance, hairstyle and clothing. Clean white background. Photorealistic style. No text, no labels, no watermarks."

echo "转换图片为 base64..."

# 构建 JSON 数据并写入临时文件
TEMP_JSON=$(mktemp)

# 开始构建 JSON（使用 q3-fast 模型）
echo -n '{"model":"q3-fast","images":[' > "$TEMP_JSON"

first=true
for photo in "${PHOTOS[@]}"; do
  # 检测图片类型
  FILE_EXT="${photo##*.}"
  FILE_EXT_LOWER=$(echo "$FILE_EXT" | tr '[:upper:]' '[:lower:]')
  
  # 确定MIME类型
  case "$FILE_EXT_LOWER" in
    png) MIME_TYPE="image/png" ;;
    webp) MIME_TYPE="image/webp" ;;
    gif) MIME_TYPE="image/gif" ;;
    *) MIME_TYPE="image/jpeg" ;;
  esac
  
  echo "  转换: $(basename $photo) -> $MIME_TYPE"
  
  # 转为 base64
  b64=$(base64 -i "$photo" | tr -d '\n')
  if [ "$first" = true ]; then
    echo -n "\"data:$MIME_TYPE;base64,$b64\"" >> "$TEMP_JSON"
    first=false
  else
    echo -n ",\"data:$MIME_TYPE;base64,$b64\"" >> "$TEMP_JSON"
  fi
done

# 完成 JSON
echo -n "],\"prompt\":\"$PROMPT\",\"aspect_ratio\":\"16:9\"}" >> "$TEMP_JSON"

echo ""
echo "✓ 图片转换完成（$(wc -c < "$TEMP_JSON" | xargs) bytes）"
echo ""

echo "生成设定图..."
echo "提示词: $PROMPT"
echo ""

# 创建任务（使用文件传输）
echo "上传到 Vidu..."
RESULT=$(curl -s -X POST "https://api.vidu.cn/ent/v2/reference2image/nano" \
  -H "Authorization: Token $VIDU_KEY" \
  -H "Content-Type: application/json" \
  --data-binary "@$TEMP_JSON")

# 清理临时文件
rm -f "$TEMP_JSON"

TASK_ID=$(echo "$RESULT" | jq -r '.task_id // empty')

if [ -z "$TASK_ID" ]; then
  echo "❌ 任务创建失败"
  echo "$RESULT" | jq . 2>/dev/null || echo "$RESULT"
  exit 1
fi

echo "任务ID: $TASK_ID"
echo "等待生成..."

# 轮询等待
for i in {1..90}; do
  sleep 3
  STATUS=$(curl -s "https://api.vidu.cn/ent/v2/tasks/$TASK_ID/creations" \
    -H "Authorization: Token $VIDU_KEY")
  STATE=$(echo "$STATUS" | jq -r '.state // empty')
  PROGRESS=$(echo "$STATUS" | jq -r '.progress // 0')
  
  # 进度条
  printf "\r[$i/90] %s %3s%%  " "$STATE" "$PROGRESS"
  
  if [ "$STATE" = "success" ]; then
    echo ""
    IMAGE_URL=$(echo "$STATUS" | jq -r '.creations[0].url // empty')
    echo ""
    echo "✓ 设定图生成完成"
    echo "URL: $IMAGE_URL"
    
    # 保存到文件
    OUTPUT_PATH="$HOME/.openclaw/workspace/skills/partner-creator/assets/character-sheet.png"
    curl -s "$IMAGE_URL" -o "$OUTPUT_PATH"
    echo "✓ 已保存: $OUTPUT_PATH"
    
    # 更新配置文件
    CONFIG_FILE="$HOME/.openclaw/workspace/skills/partner-creator/references/current-character.md"
    if [ -f "$CONFIG_FILE" ]; then
      # 添加设定图URL
      if ! grep -q "CHARACTER_SHEET_URL:" "$CONFIG_FILE"; then
        echo "" >> "$CONFIG_FILE"
        echo "---" >> "$CONFIG_FILE"
        echo "" >> "$CONFIG_FILE"
        echo "## 设定图" >> "$CONFIG_FILE"
        echo "" >> "$CONFIG_FILE"
        echo "CHARACTER_SHEET_URL: $IMAGE_URL" >> "$CONFIG_FILE"
        echo "" >> "$CONFIG_FILE"
        echo "CHARACTER_SHEET_LOCAL: $OUTPUT_PATH" >> "$CONFIG_FILE"
      else
        sed -i.bak "s|CHARACTER_SHEET_URL: .*|CHARACTER_SHEET_URL: $IMAGE_URL|" "$CONFIG_FILE"
        sed -i.bak "s|CHARACTER_SHEET_LOCAL: .*|CHARACTER_SHEET_LOCAL: $OUTPUT_PATH|" "$CONFIG_FILE"
      fi
      echo "✓ 已更新配置文件"
    fi
    
    # 输出URL供后续使用
    echo ""
    echo "---"
    echo "CHARACTER_SHEET_URL: $IMAGE_URL"
    echo "CHARACTER_SHEET_LOCAL: $OUTPUT_PATH"
    
    exit 0
  elif [ "$STATE" = "failed" ]; then
    echo ""
    echo "❌ 生成失败"
    echo "$STATUS" | jq .
    exit 1
  fi
done

echo ""
echo "❌ 超时"
exit 1
