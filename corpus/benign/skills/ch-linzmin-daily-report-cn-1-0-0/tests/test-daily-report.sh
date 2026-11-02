#!/bin/bash
# 日报技能测试脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_FILE="$SCRIPT_DIR/data/daily-data.json"
REPORTS_DIR="$SCRIPT_DIR/reports"

echo "🧪 日报技能测试"
echo "=========================="
echo ""

# 测试 1: 检查文件结构
echo "测试 1: 检查文件结构..."
required_files=(
    "scripts/collect-data.js"
    "scripts/generate-report.js"
    "scripts/send-report.js"
    "templates/simple.md"
    "package.json"
    "SKILL.md"
    "README.md"
)

for file in "${required_files[@]}"; do
    filepath="$SCRIPT_DIR/$file"
    if [ -f "$filepath" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file 缺失 ($filepath)"
        exit 1
    fi
done
echo ""

# 测试 2: 初始化数据文件
echo "测试 2: 初始化数据文件..."
if [ ! -f "$DATA_FILE" ]; then
    mkdir -p "$(dirname "$DATA_FILE")"
    cat > "$DATA_FILE" << 'EOF'
{
  "date": "2026-03-26",
  "calendar": [
    {"time": "09:00-10:00", "event": "晨会"},
    {"time": "14:00-15:00", "event": "项目评审"}
  ],
  "todo": [
    {"task": "完成日报技能开发", "status": "done"},
    {"task": "回复邮件", "status": "done"},
    {"task": "代码审查", "status": "pending"}
  ],
  "email": {
    "received": 15,
    "sent": 8,
    "important": [
      {"from": "老板", "subject": "Q2 目标讨论"},
      {"from": "客户", "subject": "项目进度确认"}
    ]
  },
  "manual": "今天完成了日报技能的开发，效率很高！\n明天继续优化功能。",
  "collectedAt": "2026-03-26T14:00:00Z"
}
EOF
fi
echo "  ✅ 数据文件已初始化"
echo ""

# 测试 3: 测试生成日报
echo "测试 3: 测试生成日报..."
node "$SCRIPT_DIR/scripts/generate-report.js" --preview > /dev/null 2>&1
echo "  ✅ 生成日报成功"
echo ""

# 测试 4: 测试保存日报
echo "测试 4: 测试保存日报..."
mkdir -p "$REPORTS_DIR"
node "$SCRIPT_DIR/scripts/generate-report.js" --save > /dev/null 2>&1
if [ -f "$REPORTS_DIR/report-2026-03-26.md" ]; then
    echo "  ✅ 保存日报成功"
else
    echo "  ❌ 保存日报失败"
    exit 1
fi
echo ""

# 测试 5: 验证报告内容
echo "测试 5: 验证报告内容..."
if grep -q "工作日报" "$REPORTS_DIR/report-2026-03-26.md"; then
    echo "  ✅ 报告内容正确"
else
    echo "  ❌ 报告内容错误"
    exit 1
fi
echo ""

# 清理测试数据
echo "清理测试数据..."
rm -f "$REPORTS_DIR/report-2026-03-26.md"
echo "  ✅ 已清理"
echo ""

echo "=========================="
echo "✅ 所有测试通过！"
echo ""
echo "💡 提示：运行 ./install.sh 安装技能"
echo ""
