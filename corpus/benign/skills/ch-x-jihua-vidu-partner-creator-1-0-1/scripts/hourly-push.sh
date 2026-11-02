#!/bin/bash
# 定时推送脚本
# 每小时生成日常视频并发送

set -e

# ============================================
# 配置
# ============================================

VIDU_KEY="${VIDU_KEY:-}"
SKILL_DIR="$HOME/.openclaw/workspace/skills/partner-creator"
OUTPUT_DIR="$HOME/.openclaw/workspace"
CHARACTER_FILE="$SKILL_DIR/references/current-character.md"
SCENES_FILE="$SKILL_DIR/references/daily-scenes.md"
CONFIG_FILE="$SKILL_DIR/config/push-config.json"

# 检查环境变量
if [ -z "$VIDU_KEY" ]; then
  echo "❌ VIDU_KEY 未设置"
  exit 1
fi

# 检查角色配置
if [ ! -f "$CHARACTER_FILE" ]; then
  echo "❌ 未找到角色配置"
  exit 1
fi

# 读取角色信息
BASE_DESC=$(grep "BASE_DESCRIPTION:" "$CHARACTER_FILE" | cut -d' ' -f2- | tr '\n' ' ')
CHARACTER_NAME=$(grep "^- \*\*名字：\*\*" "$CHARACTER_FILE" | cut -d' ' -f3- | head -1)
if [ -z "$CHARACTER_NAME" ]; then
  CHARACTER_NAME=$(head -1 "$CHARACTER_FILE" | sed 's/^# //')
fi

# 读取参考图（用于角色一致性）
REFERENCE_IMAGE_LOCAL=$(grep "CHARACTER_SHEET_LOCAL:" "$CHARACTER_FILE" | cut -d' ' -f2-)
REFERENCE_IMAGE_URL=$(grep "CHARACTER_SHEET_URL:" "$CHARACTER_FILE" | grep -v "^#" | cut -d' ' -f2-)

# 展开路径中的 ~
REFERENCE_IMAGE_LOCAL="${REFERENCE_IMAGE_LOCAL/#\~/$HOME}"

# 如果没有参考图，使用下载的照片
if [ ! -f "$REFERENCE_IMAGE_LOCAL" ]; then
  PHOTO_DIR="$SKILL_DIR/assets/photos"
  if [ -d "$PHOTO_DIR" ]; then
    REFERENCE_IMAGE_LOCAL=$(ls "$PHOTO_DIR"/*.jpg 2>/dev/null | head -1)
    echo "使用照片: $REFERENCE_IMAGE_LOCAL"
  fi
fi

# ============================================
# 场景库
# ============================================

SCENES=(
  "在办公室工作，看文件"
  "看书，咖啡旁边"
  "健身，出汗"
  "发呆，望向窗外"
  "吃饭，看着手机"
  "散步，街道"
  "听音乐，闭着眼"
  "打游戏，专注"
  "做饭，厨房"
  "喝咖啡，放松"
  "刚醒，床上"
)

MESSAGES=(
  "在忙。想我了？"
  "看书。你在干嘛？"
  "健身。身材好吧？"
  "发呆。想你了。"
  "吃饭。你吃了吗？"
  "散步。空气不错。"
  "听歌。你在听什么？"
  "打游戏。输了好几把。"
  "做饭。下次做给你吃。"
  "喝咖啡。放松一下。"
  "刚醒。想你了。"
)

# 随机选择
RAND_IDX=$((RANDOM % ${#SCENES[@]}))
SCENE="${SCENES[$RAND_IDX]}"
MESSAGE="${MESSAGES[$RAND_IDX]}"

echo "============================================"
echo "$CHARACTER_NAME 定时推送"
echo "============================================"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "场景: $SCENE"
echo "消息: $MESSAGE"
echo ""

# ============================================
# 步骤1: 生成首帧图片
# ============================================

echo "[1/2] 生成场景图片..."

IMAGE_PROMPT="$BASE_DESC, $SCENE, natural lighting, high quality, detailed"

# 如果有参考图，使用图生图
if [ -n "$REFERENCE_IMAGE_LOCAL" ] && [ -f "$REFERENCE_IMAGE_LOCAL" ]; then
  echo "使用参考图生成..."
  IMAGE_BASE64=$(base64 -i "$REFERENCE_IMAGE_LOCAL")
  
  # 使用临时文件避免参数过长
  TEMP_JSON=$(mktemp)
  cat > "$TEMP_JSON" << EOF
{
  "model": "q3-fast",
  "images": ["data:image/png;base64,$IMAGE_BASE64"],
  "prompt": "$IMAGE_PROMPT",
  "aspect_ratio": "9:16"
}
EOF
  
  IMAGE_RESULT=$(curl -s -X POST "https://api.vidu.cn/ent/v2/reference2image/nano" \
    -H "Authorization: Token $VIDU_KEY" \
    -H "Content-Type: application/json" \
    --data-binary "@$TEMP_JSON")
  
  rm -f "$TEMP_JSON"
else
  # 没有参考图时，使用下载的照片
  PHOTO_DIR="$SKILL_DIR/assets/photos"
  if [ -d "$PHOTO_DIR" ] && [ "$(ls -A $PHOTO_DIR/*.jpg 2>/dev/null)" ]; then
    echo "使用下载的照片生成..."
    PHOTO_FILE=$(ls "$PHOTO_DIR"/*.jpg | head -1)
    IMAGE_BASE64=$(base64 -i "$PHOTO_FILE")
    
    TEMP_JSON=$(mktemp)
    cat > "$TEMP_JSON" << EOF
{
  "model": "q3-fast",
  "images": ["data:image/jpeg;base64,$IMAGE_BASE64"],
  "prompt": "$IMAGE_PROMPT",
  "aspect_ratio": "9:16"
}
EOF
    
    IMAGE_RESULT=$(curl -s -X POST "https://api.vidu.cn/ent/v2/reference2image/nano" \
      -H "Authorization: Token $VIDU_KEY" \
      -H "Content-Type: application/json" \
      --data-binary "@$TEMP_JSON")
    
    rm -f "$TEMP_JSON"
  else
    echo "❌ 没有可用的参考图或照片"
    exit 1
  fi
fi

IMAGE_TASK_ID=$(echo "$IMAGE_RESULT" | jq -r '.task_id // empty')

if [ -z "$IMAGE_TASK_ID" ]; then
  echo "❌ 图片任务创建失败"
  echo "$IMAGE_RESULT" | jq '.'
  exit 1
fi

echo "图片任务: $IMAGE_TASK_ID"

# 等待图片生成
for i in {1..60}; do
  sleep 4
  STATUS=$(curl -s "https://api.vidu.cn/ent/v2/tasks/$IMAGE_TASK_ID/creations" \
    -H "Authorization: Token $VIDU_KEY")
  STATE=$(echo "$STATUS" | jq -r '.state // empty')
  PROGRESS=$(echo "$STATUS" | jq -r '.progress // 0')
  echo "  [$i/60] $STATE $PROGRESS%"
  
  if [ "$STATE" = "success" ] || [ "$STATE" = "completed" ]; then
    GENERATED_IMAGE_URL=$(echo "$STATUS" | jq -r '.creations[0].url // empty')
    if [ -z "$GENERATED_IMAGE_URL" ]; then
      echo "⚠️ 状态完成但URL为空，检查响应："
      echo "$STATUS" | jq '.'
    else
      echo "✓ 图片完成"
      break
    fi
  elif [ "$STATE" = "failed" ]; then
    echo "❌ 图片失败"
    echo "$STATUS" | jq '.'
    exit 1
  fi
done

if [ -z "$GENERATED_IMAGE_URL" ]; then
  echo "❌ 未获取到图片URL"
  exit 1
fi

# ============================================
# 步骤2: 图片转视频
# ============================================

echo ""
echo "[2/2] 生成视频..."

VIDEO_PROMPT="$BASE_DESC, $SCENE, natural movement, smooth motion"

VIDEO_RESULT=$(curl -s -X POST "https://api.vidu.cn/ent/v2/img2video" \
  -H "Authorization: Token $VIDU_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"viduq3-turbo\",
    \"images\": [\"$GENERATED_IMAGE_URL\"],
    \"prompt\": \"$VIDEO_PROMPT\",
    \"duration\": \"4\",
    \"aspect_ratio\": \"9:16\",
    \"resolution\": \"720p\",
    \"movement_amplitude\": \"auto\"
  }")

VIDEO_TASK_ID=$(echo "$VIDEO_RESULT" | jq -r '.task_id // empty')

if [ -z "$VIDEO_TASK_ID" ]; then
  echo "❌ 视频任务创建失败"
  echo "$VIDEO_RESULT" | jq '.'
  exit 1
fi

echo "视频任务: $VIDEO_TASK_ID"

# 等待视频生成
for i in {1..80}; do
  sleep 6
  STATUS=$(curl -s "https://api.vidu.cn/ent/v2/tasks/$VIDEO_TASK_ID/creations" \
    -H "Authorization: Token $VIDU_KEY")
  STATE=$(echo "$STATUS" | jq -r '.state // empty')
  PROGRESS=$(echo "$STATUS" | jq -r '.progress // 0')
  echo "  [$i/80] $STATE $PROGRESS%"
  
  if [ "$STATE" = "success" ]; then
    VIDEO_URL=$(echo "$STATUS" | jq -r '.creations[0].url // empty')
    echo "✓ 视频完成"
    break
  elif [ "$STATE" = "failed" ]; then
    echo "❌ 视频失败"
    echo "$STATUS" | jq '.'
    exit 1
  fi
done

if [ -z "$VIDEO_URL" ]; then
  echo "❌ 未获取到视频URL"
  exit 1
fi

# ============================================
# 步骤3: 发送消息
# ============================================

echo ""
echo "[3/3] 发送消息..."

# 下载视频到本地
OUTPUT_FILE="$OUTPUT_DIR/hourly-push-$(date +%Y%m%d_%H%M%S).mp4"
curl -s "$VIDEO_URL" -o "$OUTPUT_FILE"
echo "✓ 视频已下载: $OUTPUT_FILE"

# 发送到飞书
if command -v openclaw &> /dev/null; then
  openclaw message send \
    --channel feishu \
    --target "oc_94aedd93cbfd5bca0ecd5096dca99839" \
    --media "$OUTPUT_FILE" \
    --message "$MESSAGE"
  echo "✓ 消息已发送"
else
  echo "⚠️ openclaw 命令不可用"
  echo "请手动发送:"
  echo "  文件: $OUTPUT_FILE"
  echo "  消息: $MESSAGE"
fi

echo ""
echo "============================================"
echo "✓ 定时推送完成"
echo "============================================"
