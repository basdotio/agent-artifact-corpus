#!/bin/bash
# 日报技能安装脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$HOME/.openclaw/logs"

echo "🦆 日报技能安装脚本"
echo "========================"
echo ""

# 检查前置条件
echo "检查前置条件..."

if ! command -v node &> /dev/null; then
    echo "❌ 未找到 Node.js"
    exit 1
fi
echo "  ✅ Node.js 已安装"

# 创建目录
mkdir -p "$LOG_DIR"
mkdir -p "$SCRIPT_DIR/reports"
echo "  ✅ 目录已创建"

# 设置脚本权限
echo "设置脚本权限..."
chmod +x "$SCRIPT_DIR/scripts/"*.js
chmod +x "$SCRIPT_DIR/tests/"*.sh
echo "  ✅ 脚本已设置为可执行"

# 初始化数据文件
echo "初始化数据文件..."
if [ ! -f "$SCRIPT_DIR/data/daily-data.json" ]; then
    cat > "$SCRIPT_DIR/data/daily-data.json" << 'EOF'
{
  "date": "",
  "calendar": [],
  "todo": [],
  "email": {"received": 0, "sent": 0, "important": []},
  "manual": "",
  "collectedAt": null
}
EOF
fi
echo "  ✅ 数据文件已初始化"

# 添加到 crontab（可选）
echo ""
echo "配置定时任务..."
echo "是否添加每天 18:00 自动生成日报的定时任务？(y/n)"
read -r response

if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    CRON_JOB="0 18 * * * $SCRIPT_DIR/scripts/auto-report.js >> $LOG_DIR/daily-report.log 2>&1"
    
    if crontab -l 2>/dev/null | grep -q "auto-report.js"; then
        echo "  ℹ️  定时任务已存在"
    else
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
        echo "  ✅ 已添加定时任务（每天 18:00）"
    fi
else
    echo "  ℹ️  跳过定时任务配置"
    echo "  手动运行：$SCRIPT_DIR/scripts/collect-data.js"
fi

echo ""
echo "========================"
echo "✅ 安装完成！"
echo ""
echo "使用说明："
echo "  1. 收集数据：$SCRIPT_DIR/scripts/collect-data.js"
echo "  2. 生成日报：$SCRIPT_DIR/scripts/generate-report.js"
echo "  3. 发送微信：$SCRIPT_DIR/scripts/send-report.js"
echo ""
echo "选项："
echo "  --template simple|detailed    选择模板"
echo "  --output markdown|text|weixin 输出格式"
echo "  --save                        保存到文件"
echo "  --send                        发送微信"
echo ""
echo "示例："
echo "  ./scripts/collect-data.js"
echo "  ./scripts/generate-report.js --save --send"
echo ""
