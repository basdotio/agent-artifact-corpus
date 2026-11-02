#!/bin/bash
# 发送视频到飞书
# 用法: ./send-feishu-video.sh <视频路径> <消息> [目标用户ID]

set -e

VIDEO_PATH="$1"
MESSAGE="${2:-在想我吗？}"
TARGET_USER="${3:-ou_537917854bef050cf5ae3357942fe58f}"

if [ ! -f "$VIDEO_PATH" ]; then
  echo "❌ 视频文件不存在: $VIDEO_PATH"
  exit 1
fi

# 飞书应用配置
APP_ID="cli_a92d113664389bca"
APP_SECRET=[REDACTED_SECRET]

echo "============================================"
echo "发送视频到飞书"
echo "============================================"
echo "视频: $VIDEO_PATH"
echo "消息: $MESSAGE"
echo "目标: $TARGET_USER"
echo ""

# 步骤1: 获取 access_token
echo "[1/3] 获取 access_token..."

TOKEN_RESULT=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d "{
    \"app_id\": \"$APP_ID\",
    \"app_secret\": \"$APP_SECRET\"
  }")

ACCESS_TOKEN=$(echo "$TOKEN_RESULT" | jq -r '.tenant_access_token // empty')

if [ -z "$ACCESS_TOKEN" ]; then
  echo "❌ 获取 access_token 失败"
  echo "$TOKEN_RESULT" | jq '.'
  exit 1
fi

echo "✓ access_token 已获取"

# 步骤2: 上传视频
echo ""
echo "[2/3] 上传视频..."

UPLOAD_RESULT=$(curl -s -X POST "https://open.feishu.cn/open-apis/im/v1/files" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file_type=mp4" \
  -F "file_name=video.mp4" \
  -F "file=@$VIDEO_PATH")

FILE_KEY=$(echo "$UPLOAD_RESULT" | jq -r '.data.file_key // empty')

if [ -z "$FILE_KEY" ]; then
  echo "❌ 上传视频失败"
  echo "$UPLOAD_RESULT" | jq '.'
  exit 1
fi

echo "✓ 视频已上传: $FILE_KEY"

# 步骤3: 发送消息
echo ""
echo "[3/3] 发送消息..."

SEND_RESULT=$(curl -s -X POST "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"receive_id\": \"$TARGET_USER\",
    \"msg_type\": \"media\",
    \"content\": \"{\\\"file_key\\\":\\\"$FILE_KEY\\\"}\"
  }")

if echo "$SEND_RESULT" | jq -e '.code == 0' > /dev/null 2>&1; then
  MESSAGE_ID=$(echo "$SEND_RESULT" | jq -r '.data.message_id // empty')
  echo "✓ 消息已发送: $MESSAGE_ID"
  
  # 发送文字消息
  if [ -n "$MESSAGE" ]; then
    sleep 1
    curl -s -X POST "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"receive_id\": \"$TARGET_USER\",
        \"msg_type\": \"text\",
        \"content\": \"{\\\"text\\\":\\\"$MESSAGE\\\"}\"
      }" > /dev/null
    echo "✓ 文字消息已发送: $MESSAGE"
  fi
else
  echo "❌ 发送消息失败"
  echo "$SEND_RESULT" | jq '.'
  exit 1
fi

echo ""
echo "============================================"
echo "✓ 完成"
echo "============================================"
