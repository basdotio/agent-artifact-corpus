#!/bin/bash
# 账单提醒技能安装脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$HOME/.openclaw/logs"

echo "🦆 账单提醒技能安装脚本"
echo "========================"
echo ""

# 检查前置条件
echo "检查前置条件..."

if ! command -v node &> /dev/null; then
    echo "❌ 未找到 Node.js"
    exit 1
fi
echo "  ✅ Node.js 已安装"

# 创建日志目录
mkdir -p "$LOG_DIR"
echo "  ✅ 日志目录已创建"

# 设置脚本权限
echo "设置脚本权限..."
chmod +x "$SCRIPT_DIR/scripts/"*.js
chmod +x "$SCRIPT_DIR/tests/"*.sh
echo "  ✅ 脚本已设置为可执行"
echo ""

# 初始化数据文件
echo "初始化数据文件..."
if [ ! -f "$SCRIPT_DIR/data/bills.json" ]; then
    echo '{"bills":[],"paymentHistory":[]}' > "$SCRIPT_DIR/data/bills.json"
fi
echo "  ✅ 数据文件已初始化"
echo ""

# 添加到 crontab
echo "配置定时任务..."
CRON_JOB="0 9 * * * $SCRIPT_DIR/scripts/check-bills.js >> $LOG_DIR/bill-reminder.log 2>&1"

if crontab -l 2>/dev/null | grep -q "check-bills.js"; then
    echo "  ℹ️  定时任务已存在"
else
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "  ✅ 已添加定时任务（每天 9:00 检查账单）"
fi
echo ""

# 显示使用说明
echo "========================"
echo "✅ 安装完成！"
echo ""
echo "使用说明："
echo "  1. 添加账单："
echo "     $SCRIPT_DIR/scripts/add-bill.js \"信用卡\" 5000 15"
echo ""
echo "  2. 查看账单："
echo "     $SCRIPT_DIR/scripts/list-bills.js"
echo ""
echo "  3. 标记还款："
echo "     $SCRIPT_DIR/scripts/mark-paid.js <序号>"
echo ""
echo "  4. 删除账单："
echo "     $SCRIPT_DIR/scripts/remove-bill.js <序号>"
echo ""
echo "定时任务："
echo "  每天 9:00 自动检查账单并发送提醒"
echo "  日志：$LOG_DIR/bill-reminder.log"
echo ""
echo "测试："
echo "  $SCRIPT_DIR/tests/test-bill-reminder.sh"
echo ""
