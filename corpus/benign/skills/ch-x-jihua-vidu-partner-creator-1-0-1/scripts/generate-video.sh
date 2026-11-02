#!/bin/bash
# 视频生成脚本
# 使用 Vidu Q2 reference-to-video

set -e

# 检查环境变量
if [ -z "$VIDU_KEY" ]; then
  echo "=========================================="
  echo "⚠️  未检测到 Vidu API Key"
  echo "=========================================="
  echo ""
  echo "请先设置环境变量："
  echo "  export VIDU_KEY=\"vda_你的key\""
  echo ""
  exit 1
fi

# 检查角色配置
CHARACTER_FILE="$HOME/.openclaw/workspace/skills/partner-creator/references/current-character.md"
if [ ! -f "$CHARACTER_FILE" ]; then
  echo "❌ 未找到角色配置，请先创建角色"
  exit 1
fi

# 读取参考图URL
REFERENCE_IMAGE=$(grep "REFERENCE_IMAGE_URL:" "$CHARACTER_FILE" | cut -d' ' -f2)

if [ -z "$REFERENCE_IMAGE" ]; then
  echo "❌ 未找到参考图，请先生成角色三视图"
  exit 1
fi

# 参数
SCENE_DESC="$1"
OUTPUT_PATH="${2:-}"
ASPECT_RATIO="${3:-9:16}"

if [ -z "$SCENE_DESC" ]; then
  echo "Usage: $0 <scene_description> [output_path] [aspect_ratio]"
  echo ""
  echo "Examples:"
  echo "  $0 \"selfie video, waving at camera\""
  echo "  $0 \"looking at camera with smile\" output.mp4 9:16"
  exit 1
fi

# 读取角色基础描述
BASE_DESC=$(grep "BASE_DESCRIPTION:" "$CHARACTER_FILE" | cut -d' ' -f2-)
if [ -z "$BASE_DESC" ]; then
  BASE_DESC="handsome young person"
fi

echo "生成视频..."
echo "场景: $SCENE_DESC"
echo "比例: $ASPECT_RATIO"
echo ""

# 构建 prompt（默认自拍视角）
CONSISTENCY="maintain consistent character appearance with reference image, same face and identity"
SELFIE="selfie video, POV shot, camera held at arm's length, natural movement"
STYLE="high quality, smooth motion, cinematic"

PROMPT="$BASE_DESC, $SCENE_DESC, $SELFIE, $CONSISTENCY, $STYLE"

# 创建任务 - 使用 Q2pro 参考生成
RESULT=$(curl -s -X POST "https://api.vidu.cn/ent/v2/reference2video" \
  -H "Authorization: Token $VIDU_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"viduq2-pro\",
    \"images\": [\"$REFERENCE_IMAGE\"],
    \"prompt\": \"$PROMPT\",
    \"duration\": \"4\",
    \"aspect_ratio\": \"$ASPECT_RATIO\",
    \"resolution\": \"720p\",
    \"movement_amplitude\": \"auto\"
  }")

TASK_ID=$(echo "$RESULT" | jq -r '.task_id // empty')

if [ -z "$TASK_ID" ]; then
  echo "❌ 任务创建失败"
  echo "$RESULT" | jq .
  exit 1
fi

echo "任务ID: $TASK_ID"
echo "等待生成（视频需要几分钟）..."

# 轮询等待
for i in {1..80}; do
  sleep 6
  STATUS=$(curl -s "https://api.vidu.cn/ent/v2/tasks/$TASK_ID/creations" \
    -H "Authorization: Token $VIDU_KEY")
  STATE=$(echo "$STATUS" | jq -r '.state // empty')
  PROGRESS=$(echo "$STATUS" | jq -r '.progress // 0')
  echo "[$i/80] $STATE $PROGRESS%"
  
  if [ "$STATE" = "success" ]; then
    VIDEO_URL=$(echo "$STATUS" | jq -r '.creations[0].url // empty')
    echo "✓ 视频生成完成"
    
    if [ -n "$OUTPUT_PATH" ]; then
      curl -s "$VIDEO_URL" -o "$OUTPUT_PATH"
      echo "✓ 已保存: $OUTPUT_PATH"
    else
      TEMP_FILE=$(mktemp /tmp/partner-video-XXXXXX.mp4)
      curl -s "$VIDEO_URL" -o "$TEMP_FILE"
      echo "✓ 已保存: $TEMP_FILE"
      echo "$TEMP_FILE"
    fi
    exit 0
  elif [ "$STATE" = "failed" ]; then
    echo "❌ 生成失败"
    exit 1
  fi
done

echo "❌ 超时"
exit 1
