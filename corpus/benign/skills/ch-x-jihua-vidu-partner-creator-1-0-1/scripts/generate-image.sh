#!/bin/bash
# 图片生成脚本（统一使用 reference2image/nano）
# 模型: q3-fast
# 原创角色使用白底图，复刻角色使用搜索到的照片

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
SCENE_DESC="$1"
OUTPUT_PATH="${2:-}"
ASPECT_RATIO="${3:-9:16}"
REFERENCE_IMAGE="${4:-}"  # 可选：参考图路径，不传则使用白底图

if [ -z "$SCENE_DESC" ]; then
  echo "Usage: $0 <scene_description> [output_path] [aspect_ratio] [reference_image]"
  echo ""
  echo "Arguments:"
  echo "  scene_description - 场景描述"
  echo "  output_path       - 输出路径（可选，默认临时文件）"
  echo "  aspect_ratio      - 比例（可选，默认 9:16）"
  echo "  reference_image   - 参考图路径（可选，不传则使用白底图）"
  echo ""
  echo "Examples:"
  echo "  # 原创角色（自动使用白底图）"
  echo "  $0 \"清纯男大学生, 温柔笑容, anime style\""
  echo ""
  echo "  # 复刻角色（使用搜索到的照片）"
  echo "  $0 \"角色描述\" output.jpg 9:16 /path/to/reference.jpg"
  exit 1
fi

# 检查角色配置
CHARACTER_FILE="$HOME/.openclaw/workspace/skills/partner-creator/references/current-character.md"

# 如果没有传入参考图，检查配置文件中的参考图
if [ -z "$REFERENCE_IMAGE" ]; then
  if [ -f "$CHARACTER_FILE" ]; then
    CONFIG_REF=$(grep "REFERENCE_IMAGE_LOCAL:" "$CHARACTER_FILE" | cut -d' ' -f2)
    if [ -n "$CONFIG_REF" ] && [ -f "$CONFIG_REF" ]; then
      REFERENCE_IMAGE="$CONFIG_REF"
      echo "使用配置中的参考图: $REFERENCE_IMAGE"
    fi
  fi
fi

# 如果还是没有参考图，使用白底图（原创角色）
if [ -z "$REFERENCE_IMAGE" ]; then
  BLANK_CANVAS="$HOME/.openclaw/workspace/skills/partner-creator/assets/blank-canvas.jpg"
  if [ -f "$BLANK_CANVAS" ]; then
    REFERENCE_IMAGE="$BLANK_CANVAS"
    echo "使用白底图（原创角色模式）"
  else
    echo "❌ 未找到白底图: $BLANK_CANVAS"
    echo "请先保存白底图到该路径"
    exit 1
  fi
fi

echo "生成图片..."
echo "场景: $SCENE_DESC"
echo "比例: $ASPECT_RATIO"
echo "参考图: $REFERENCE_IMAGE"
echo ""

# 将参考图转为 base64
BASE64_DATA=$(base64 -i "$REFERENCE_IMAGE" | tr -d '\n')

# 读取角色基础描述（如果有配置文件）
BASE_DESC=""
if [ -f "$CHARACTER_FILE" ]; then
  BASE_DESC=$(grep "BASE_DESCRIPTION:" "$CHARACTER_FILE" | cut -d' ' -f2-)
fi

if [ -z "$BASE_DESC" ]; then
  BASE_DESC=""  # 不添加默认描述，让用户完全控制
fi

# 构建 prompt
if [ -n "$BASE_DESC" ]; then
  PROMPT="$BASE_DESC, $SCENE_DESC"
else
  PROMPT="$SCENE_DESC"
fi

# 创建请求 JSON
REQUEST_JSON=$(jq -n \
  --arg model "q3-fast" \
  --arg images "data:image/jpeg;base64,$BASE64_DATA" \
  --arg prompt "$PROMPT" \
  --arg aspect_ratio "$ASPECT_RATIO" \
  '{
    model: $model,
    images: [$images],
    prompt: $prompt,
    aspect_ratio: $aspect_ratio
  }')

# 创建任务
echo "正在创建任务..."
RESULT=$(curl -s -X POST "https://api.vidu.cn/ent/v2/reference2image/nano" \
  -H "Authorization: Token $VIDU_KEY" \
  -H "Content-Type: application/json" \
  --data-binary "$REQUEST_JSON")

TASK_ID=$(echo "$RESULT" | jq -r '.task_id // empty')

if [ -z "$TASK_ID" ]; then
  echo "❌ 任务创建失败"
  echo "$RESULT" | jq . 2>/dev/null || echo "$RESULT"
  exit 1
fi

echo "任务ID: $TASK_ID"
echo "等待生成..."

# 轮询等待
for i in {1..60}; do
  sleep 3
  STATUS=$(curl -s "https://api.vidu.cn/ent/v2/tasks/$TASK_ID/creations" \
    -H "Authorization: Token $VIDU_KEY")
  
  STATE=$(echo "$STATUS" | jq -r '.state // empty' 2>/dev/null)
  PROGRESS=$(echo "$STATUS" | jq -r '.progress // 0' 2>/dev/null)
  echo "[$i/60] $STATE $PROGRESS%"
  
  if [ "$STATE" = "success" ]; then
    IMAGE_URL=$(echo "$STATUS" | jq -r '.creations[0].url // empty' 2>/dev/null)
    echo "✓ 图片生成完成"
    echo "URL: $IMAGE_URL"
    
    if [ -n "$OUTPUT_PATH" ]; then
      curl -s "$IMAGE_URL" -o "$OUTPUT_PATH"
      echo "✓ 已保存: $OUTPUT_PATH"
    else
      TEMP_FILE=$(mktemp /tmp/partner-XXXXXX.png)
      curl -s "$IMAGE_URL" -o "$TEMP_FILE"
      echo "✓ 已保存: $TEMP_FILE"
      echo "$TEMP_FILE"
    fi
    exit 0
  elif [ "$STATE" = "failed" ]; then
    echo "❌ 生成失败"
    echo "$STATUS" | jq . 2>/dev/null
    exit 1
  fi
done

echo "❌ 超时"
exit 1
