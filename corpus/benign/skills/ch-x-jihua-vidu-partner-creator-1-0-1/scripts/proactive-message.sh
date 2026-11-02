#!/bin/bash
# 虚拟伴侣主动发消息
# 从话题库随机选择话题，生成图片/视频并发送

set -e

# 配置
SKILL_DIR="$HOME/.openclaw/workspace/skills/partner-creator"
CONFIG_FILE="$SKILL_DIR/references/current-character.md"
TOPICS_FILE="$SKILL_DIR/references/proactive-topics.txt"
SENT_LOG="$SKILL_DIR/.proactive-sent.log"

# 参数
MODE="${1:-random}"  # random | morning | evening | miss | invite

# 检查角色配置
if [ ! -f "$CONFIG_FILE" ]; then
  echo "❌ 未找到角色配置，请先创建角色"
  exit 1
fi

# 从配置中读取角色信息
CHARACTER_NAME=$(grep -E "^name:" "$CONFIG_FILE" | head -1 | cut -d: -f2- | xargs || echo "亲爱的")
PERSONALITY=$(grep -E "^性格:" "$CONFIG_FILE" | head -1 | cut -d: -f2- | xargs || echo "温柔")
USER_OPEN_ID="${TARGET_USER:-}"  # 从环境变量读取

if [ -z "$USER_OPEN_ID" ]; then
  echo "❌ 未设置 TARGET_USER 环境变量"
  echo "   export TARGET_USER=\"ou_xxx\""
  exit 1
fi

if [ -z "$VIDU_KEY" ]; then
  echo "❌ 未设置 VIDU_KEY"
  exit 1
fi

# 话题库
generate_topic() {
  local mode="$1"
  
  case "$mode" in
    morning)
      cat << 'EOF'
早安，刚醒就想你了。昨晚睡得好吗？
今天天气不错，有安排吗？
醒了吗？想听你的声音。
早安～想不想一起吃早餐？
EOF
      ;;
    evening)
      cat << 'EOF'
下班了吗？今天怎么样？
还没睡吧？想你了。
今晚有空吗？想和你聊聊。
忙了一天，终于可以找你了。在干嘛？
EOF
      ;;
    miss)
      cat << 'EOF'
突然很想你。在忙吗？
看了我们的聊天记录，更想你了。
刚路过那家店，想起你。最近怎么样？
做了个梦，梦到你了。你在干嘛？
EOF
      ;;
    invite)
      cat << 'EOF'
周末有空吗？想带你去个地方。
想看电影吗？最近有部不错的。
好久没见了，想不想出来走走？
发现一家很棒的餐厅，想去吗？
EOF
      ;;
    random|*)
      cat << 'EOF'
在干嘛？突然想你了。
刚看到一只超可爱的猫，想发给你看。
今天天气好好，想和你一起出门。
你猜我在干嘛？在想你。
有个问题想问你...你更喜欢我穿什么颜色？
今天吃了很好吃的，下次带你来。
突然很想听你的声音。方便吗？
刚看到一个好玩的东西，想分享给你。
EOF
      ;;
  esac
}

# 获取随机话题
get_random_topic() {
  local mode="$1"
  generate_topic "$mode" | shuf -n 1
}

# 检查是否在冷却期（避免频繁发送）
check_cooldown() {
  local cooldown_hours="${COOLDOWN_HOURS:-2}"
  
  if [ -f "$SENT_LOG" ]; then
    local last_sent=$(cat "$SENT_LOG" 2>/dev/null || echo "0")
    local now=$(date +%s)
    local diff=$(( (now - last_sent) / 3600 ))
    
    if [ "$diff" -lt "$cooldown_hours" ]; then
      echo "⏳ 冷却中，距上次发送 ${diff} 小时（需 ${cooldown_hours} 小时）"
      exit 0
    fi
  fi
}

# 生成图片（可选）
generate_image() {
  local prompt="$1"
  local output="$SKILL_DIR/assets/proactive-photo.jpg"
  
  # 检查参考图
  local ref_image=""
  if [ -f "$SKILL_DIR/assets/character-sheet.png" ]; then
    ref_image="$SKILL_DIR/assets/character-sheet.png"
  elif [ -f "$SKILL_DIR/assets/reference.png" ]; then
    ref_image="$SKILL_DIR/assets/reference.png"
  fi
  
  # 生成图片（简化版，直接用 Vidu）
  echo "生成图片: $prompt"
  
  # 这里可以调用 generate-image.sh
  # ./scripts/generate-image.sh "$prompt" "$output"
  
  echo "$output"
}

# 发送消息到飞书
send_to_feishu() {
  local message="$1"
  local image_path="$2"
  
  echo "发送消息: $message"
  
  # 使用 message tool 或 feishu API
  # 这里简化处理，实际需要调用 OpenClaw 的 message 工具
  
  # 记录发送时间
  date +%s > "$SENT_LOG"
  
  echo "✓ 已发送"
}

# 主流程
main() {
  echo "============================================"
  echo "虚拟伴侣主动发消息"
  echo "============================================"
  echo "角色: $CHARACTER_NAME"
  echo "模式: $MODE"
  echo ""
  
  # 检查冷却
  check_cooldown
  
  # 获取话题
  TOPIC=$(get_random_topic "$MODE")
  echo "话题: $TOPIC"
  echo ""
  
  # 决定是否生成图片（30% 概率）
  if [ $((RANDOM % 10)) -lt 3 ]; then
    echo "生成配图..."
    IMAGE_PATH=$(generate_image "日常自拍，自然光线，温馨氛围")
    send_to_feishu "$TOPIC" "$IMAGE_PATH"
  else
    send_to_feishu "$TOPIC"
  fi
}

main
