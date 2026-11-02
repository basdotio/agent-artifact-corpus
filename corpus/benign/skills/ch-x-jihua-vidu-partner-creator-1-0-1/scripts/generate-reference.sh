#!/bin/bash
# 生成角色三视图
# 使用 Vidu text-to-image 生成角色参考图

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

# 参数
CHARACTER_DESC="$1"
STYLE="${2:-anime}"  # anime / realistic

if [ -z "$CHARACTER_DESC" ]; then
  echo "Usage: $0 <character_description> [style]"
  echo ""
  echo "Arguments:"
  echo "  character_description  - 角色外形描述"
  echo "  style                  - anime / realistic (default: anime)"
  echo ""
  echo "Example:"
  echo "  $0 \"handsome young Chinese man, long black hair in ponytail, brown eyes, athletic build\""
  exit 1
fi

echo "============================================"
echo "生成角色三视图"
echo "============================================"
echo "描述: $CHARACTER_DESC"
echo "风格: $STYLE"
echo ""

# 构建 prompt
if [ "$STYLE" = "realistic" ]; then
  STYLE_KEYWORDS="realistic style, photorealistic, detailed skin texture, cinematic lighting"
else
  STYLE_KEYWORDS="anime style, detailed illustration, clean lines, vibrant colors"
fi

PROMPT="$CHARACTER_DESC, character design sheet, three-view reference image, front view, side view, back view, head close-up shot, white background, full body standing pose, no text, no watermark, $STYLE_KEYWORDS, high quality character design"

echo "生成中..."

# 创建任务
RESULT=$(curl -s -X POST "https://api.vidu.cn/ent/v2/text2image" \
  -H "Authorization: Token $VIDU_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"q3-fast\",
    \"prompt\": \"$PROMPT\",
    \"aspect_ratio\": \"16:9\"
  }")

TASK_ID=$(echo "$RESULT" | jq -r '.task_id // empty')

if [ -z "$TASK_ID" ]; then
  echo "❌ 任务创建失败"
  echo "$RESULT" | jq .
  exit 1
fi

echo "任务ID: $TASK_ID"
echo "等待生成..."

# 轮询等待
for i in {1..60}; do
  sleep 4
  STATUS=$(curl -s "https://api.vidu.cn/ent/v2/tasks/$TASK_ID/creations" \
    -H "Authorization: Token $VIDU_KEY")
  STATE=$(echo "$STATUS" | jq -r '.state // empty')
  PROGRESS=$(echo "$STATUS" | jq -r '.progress // 0')
  echo "[$i/60] $STATE $PROGRESS%"
  
  if [ "$STATE" = "success" ]; then
    IMAGE_URL=$(echo "$STATUS" | jq -r '.creations[0].url // empty')
    echo ""
    echo "✓ 三视图生成完成"
    echo "URL: $IMAGE_URL"
    
    # 保存到文件
    OUTPUT_DIR="$HOME/.openclaw/workspace/skills/partner-creator/assets"
    curl -s "$IMAGE_URL" -o "$OUTPUT_DIR/reference.png"
    echo "✓ 已保存: $OUTPUT_DIR/reference.png"
    
    # 输出URL供配置使用
    echo ""
    echo "---"
    echo "REFERENCE_IMAGE_URL: $IMAGE_URL"
    
    exit 0
  elif [ "$STATE" = "failed" ]; then
    echo "❌ 生成失败"
    exit 1
  fi
done

echo "❌ 超时"
exit 1
