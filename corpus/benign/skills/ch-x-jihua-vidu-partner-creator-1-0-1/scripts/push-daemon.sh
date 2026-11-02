#!/bin/bash
# 虚拟伴侣定时推送守护进程
# 后台运行，每小时整点推送视频
# 更可靠，无需 cron/launchd

set -e

# ============================================
# 配置
# ============================================

SKILL_DIR="$HOME/.openclaw/workspace/skills/partner-creator"
PID_FILE="$SKILL_DIR/.push-daemon.pid"
LOG_FILE="$SKILL_DIR/push-daemon.log"
LOCK_FILE="$SKILL_DIR/.push-daemon.lock"
CONFIG_FILE="$SKILL_DIR/config/push-config.json"
ENV_FILE="$SKILL_DIR/.env"

# 加载环境变量文件
if [ -f "$ENV_FILE" ]; then
  source "$ENV_FILE"
fi

# 推送间隔（秒），默认1小时
INTERVAL="${PUSH_INTERVAL:-3600}"

# ============================================
# 函数
# ============================================

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 从配置文件读取配置
load_config() {
  if [ -f "$CONFIG_FILE" ]; then
    log "从配置文件加载: $CONFIG_FILE"
    
    # 读取 JSON 配置
    TARGET_USER=$(jq -r '.sender_id // empty' "$CONFIG_FILE")
    TARGET_CHAT=$(jq -r '.chat_id // empty' "$CONFIG_FILE")
    PLATFORM=$(jq -r '.platform // "feishu"' "$CONFIG_FILE")
    ENABLED=$(jq -r '.enabled // true' "$CONFIG_FILE")
    
    log "平台: $PLATFORM"
    log "目标用户: $TARGET_USER"
    log "目标聊天: $TARGET_CHAT"
    log "启用状态: $ENABLED"
  else
    log "⚠️ 配置文件不存在: $CONFIG_FILE"
  fi
  
  # VIDU_KEY 优先从环境变量读取
  if [ -z "$VIDU_KEY" ]; then
    log "⚠️ VIDU_KEY 未设置"
  fi
}

check_running() {
  if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
      return 0  # 已运行
    fi
  fi
  return 1  # 未运行
}

wait_for_next_hour() {
  # 计算到下一个整点的秒数
  local current_minute=$(date +%M)
  local current_second=$(date +%S)
  local seconds_to_next_hour=$(( 3600 - current_minute * 60 - current_second ))
  
  log "等待 $seconds_to_next_hour 秒到下一个整点..."
  sleep "$seconds_to_next_hour"
}

do_push() {
  log "开始推送..."
  
  # 检查锁文件，避免重复执行
  if [ -f "$LOCK_FILE" ]; then
    log "⚠️ 上次推送还在进行中，跳过"
    return
  fi
  
  # 创建锁文件
  touch "$LOCK_FILE"
  
  # 重新加载配置（确保最新）
  load_config
  
  # 检查是否启用
  if [ "$ENABLED" != "true" ]; then
    log "⚠️ 推送已禁用，跳过"
    rm -f "$LOCK_FILE"
    return
  fi
  
  # 设置环境变量供子脚本使用
  export VIDU_KEY="${VIDU_KEY:-}"
  export TARGET_USER="${TARGET_USER:-}"
  export TARGET_CHAT="${TARGET_CHAT:-}"
  export PLATFORM="${PLATFORM:-feishu}"
  
  # 执行推送
  if [ -z "$VIDU_KEY" ]; then
    log "❌ VIDU_KEY 未设置"
  elif [ -z "$TARGET_USER" ]; then
    log "❌ TARGET_USER 未设置"
  else
    "$SKILL_DIR/scripts/hourly-push.sh" >> "$LOG_FILE" 2>&1
    log "✓ 推送完成"
  fi
  
  # 移除锁文件
  rm -f "$LOCK_FILE"
}

signal_handler() {
  log "收到退出信号，停止守护进程..."
  rm -f "$PID_FILE" "$LOCK_FILE"
  exit 0
}

# ============================================
# 主流程
# ============================================

case "${1:-}" in
  start)
    if check_running; then
      echo "守护进程已在运行 (PID: $(cat $PID_FILE))"
      exit 0
    fi
    
    echo "启动守护进程..."
    echo $$ > "$PID_FILE"
    
    # 注册信号处理
    trap signal_handler SIGINT SIGTERM
    
    log "============================================"
    log "虚拟伴侣定时推送守护进程启动"
    log "============================================"
    log "PID: $$"
    log "推送间隔: 每小时整点"
    log "============================================"
    
    # 加载配置
    load_config
    
    # 检查必要配置
    if [ -z "$VIDU_KEY" ]; then
      log "⚠️ VIDU_KEY 未设置，请先 export VIDU_KEY=vda_xxx"
    fi
    if [ -z "$TARGET_USER" ]; then
      log "⚠️ TARGET_USER 未设置，请检查 config/push-config.json"
    fi
    
    # 主循环
    while true; do
      # 等待到下一个整点
      wait_for_next_hour
      
      # 执行推送
      do_push
    done
    ;;
    
  stop)
    if ! check_running; then
      echo "守护进程未运行"
      exit 0
    fi
    
    PID=$(cat "$PID_FILE")
    echo "停止守护进程 (PID: $PID)..."
    kill "$PID" 2>/dev/null || true
    rm -f "$PID_FILE" "$LOCK_FILE"
    echo "✓ 已停止"
    ;;
    
  status)
    if check_running; then
      PID=$(cat "$PID_FILE")
      echo "✓ 守护进程运行中 (PID: $PID)"
      echo ""
      echo "配置:"
      if [ -f "$CONFIG_FILE" ]; then
        cat "$CONFIG_FILE" | jq .
      else
        echo "无配置文件"
      fi
      echo ""
      echo "最近日志:"
      tail -20 "$LOG_FILE" 2>/dev/null || echo "无日志"
    else
      echo "✗ 守护进程未运行"
    fi
    ;;
    
  test)
    echo "测试推送（不启动守护进程）..."
    load_config
    do_push
    ;;
    
  log)
    echo "查看日志（Ctrl+C 退出）..."
    tail -f "$LOG_FILE"
    ;;
    
  restart)
    $0 stop
    sleep 2
    $0 start
    ;;
    
  *)
    echo "虚拟伴侣定时推送守护进程"
    echo ""
    echo "用法:"
    echo "  $0 start    # 启动守护进程（每小时整点推送）"
    echo "  $0 stop     # 停止守护进程"
    echo "  $0 status   # 查看状态"
    echo "  $0 test     # 测试推送（不启动守护进程）"
    echo "  $0 log      # 查看日志"
    echo "  $0 restart  # 重启守护进程"
    echo ""
    echo "配置文件: config/push-config.json"
    echo ""
    echo "环境变量:"
    echo "  VIDU_KEY=vda_xxx      # Vidu API Key"
    echo ""
    echo "示例:"
    echo "  export VIDU_KEY=vda_xxx"
    echo "  $0 start"
    ;;
esac
