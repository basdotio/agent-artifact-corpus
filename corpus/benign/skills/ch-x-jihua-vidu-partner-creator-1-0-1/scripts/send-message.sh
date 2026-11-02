#!/bin/bash
# 通用消息发送脚本
# 自动从配置文件读取平台和目标信息

set -e

# ============================================
# 配置
# ============================================

SKILL_DIR="$HOME/.openclaw/workspace/skills/partner-creator"
CONFIG_FILE="$SKILL_DIR/config/push-config.json"

# ============================================
# 参数
# ============================================

MEDIA_FILE="${1:-}"
MESSAGE="${2:-}"
# 可选：覆盖配置文件中的目标
OVERRIDE_TARGET="${3:-}"

# ============================================
# 帮助
# ============================================

if [ -z "$MEDIA_FILE" ] || [ -z "$MESSAGE" ]; then
  echo "用法: $0 <media_file> <message> [target]"
  echo ""
  echo "配置文件: config/push-config.json"
  echo ""
  echo "配置格式:"
  echo '  {'
  echo '    "platform": "feishu|telegram|discord|whatsapp|signal|imessage",'
  echo '    "chat_id": "目标聊天ID",'
  echo '    "sender_id": "用户ID"'
  echo '  }'
  echo ""
  echo "示例:"
  echo "  $0 video.mp4 \"早安\""
  exit 1
fi

# ============================================
# 检查文件
# ============================================

if [ ! -f "$MEDIA_FILE" ]; then
  echo "❌ 文件不存在: $MEDIA_FILE"
  exit 1
fi

# ============================================
# 读取配置
# ============================================

if [ ! -f "$CONFIG_FILE" ]; then
  echo "❌ 配置文件不存在: $CONFIG_FILE"
  echo ""
  echo "请先创建配置文件:"
  echo "  mkdir -p $SKILL_DIR/config"
  echo "  cat > $CONFIG_FILE << EOF"
  echo '  {'
  echo '    "platform": "feishu",'
  echo '    "chat_id": "oc_xxx",'
  echo '    "sender_id": "ou_xxx"'
  echo '  }'
  echo "  EOF"
  exit 1
fi

# 从配置文件读取
PLATFORM=$(jq -r '.platform // "feishu"' "$CONFIG_FILE")
CHAT_ID=$(jq -r '.chat_id // empty' "$CONFIG_FILE")
SENDER_ID=$(jq -r '.sender_id // empty' "$CONFIG_FILE")

echo "============================================"
echo "发送消息"
echo "============================================"
echo "平台: $PLATFORM"
echo "聊天: $CHAT_ID"
echo "用户: $SENDER_ID"
echo "文件: $MEDIA_FILE"
echo "消息: $MESSAGE"
echo ""

# ============================================
# 构建目标
# ============================================

if [ -n "$OVERRIDE_TARGET" ]; then
  TARGET="$OVERRIDE_TARGET"
else
  case "$PLATFORM" in
    feishu)
      # 飞书群聊使用 chat:chat_id
      if [ -n "$CHAT_ID" ]; then
        TARGET="chat:$CHAT_ID"
      else
        TARGET="user:$SENDER_ID"
      fi
      ;;
      
    telegram|discord|whatsapp|signal|imessage|wechat)
      if [ -n "$CHAT_ID" ]; then
        TARGET="$PLATFORM:$CHAT_ID"
      else
        TARGET="$PLATFORM:$SENDER_ID"
      fi
      ;;
      
    *)
      echo "❌ 不支持的平台: $PLATFORM"
      echo "支持的平台: feishu, telegram, discord, whatsapp, signal, imessage, wechat"
      exit 1
      ;;
  esac
fi

# ============================================
# 发送消息
# ============================================

echo "发送到 $PLATFORM: $TARGET"

# 使用 OpenClaw CLI 发送
openclaw message send \
  --channel "$PLATFORM" \
  --target "$TARGET" \
  --message "$MESSAGE" \
  --media "$MEDIA_FILE"

SEND_RESULT=$?

echo ""
echo "---"
echo "STATUS: $([ $SEND_RESULT -eq 0 ] && echo 'SUCCESS' || echo 'FAILED')"

exit $SEND_RESULT
