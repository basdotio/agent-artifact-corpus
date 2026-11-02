#!/bin/bash
# 媒体类型选择器
# 4次图片 : 1次视频

STATE_FILE="/tmp/partner-media-state.json"

# 初始化
if [ ! -f "$STATE_FILE" ]; then
  echo '{"count": 0}' > "$STATE_FILE"
fi

COUNT=$(cat "$STATE_FILE" | jq -r '.count')
NEW_COUNT=$((COUNT + 1))

# 每5次中，第5次发视频
if [ $((NEW_COUNT % 5)) -eq 0 ]; then
  MEDIA_TYPE="video"
else
  MEDIA_TYPE="image"
fi

# 保存状态
echo "{\"count\": $NEW_COUNT}" > "$STATE_FILE"

echo "$MEDIA_TYPE"
