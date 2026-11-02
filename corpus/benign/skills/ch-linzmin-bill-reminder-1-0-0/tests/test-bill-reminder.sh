#!/bin/bash
# 账单提醒技能测试脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_FILE="$SCRIPT_DIR/data/bills.json"

echo "🧪 账单提醒技能测试"
echo "=========================="
echo ""

# 测试 1: 检查数据目录
echo "测试 1: 检查数据文件..."
if [ -f "$DATA_FILE" ]; then
    echo "  ✅ 数据文件存在"
else
    echo "  ❌ 数据文件不存在"
    exit 1
fi
echo ""

# 测试 2: 验证 JSON 格式
echo "测试 2: 验证 JSON 格式..."
if jq empty "$DATA_FILE" 2>/dev/null; then
    echo "  ✅ JSON 格式正确"
else
    echo "  ❌ JSON 格式错误"
    exit 1
fi
echo ""

# 测试 3: 检查必需字段
echo "测试 3: 检查数据结构..."
if jq -e '.bills and .paymentHistory' "$DATA_FILE" >/dev/null 2>&1; then
    echo "  ✅ 数据结构正确"
else
    echo "  ❌ 数据结构错误"
    exit 1
fi
echo ""

# 测试 4: 测试添加账单
echo "测试 4: 测试添加账单..."
node "$SCRIPT_DIR/scripts/add-bill.js" "测试账单" 100 15 monthly 3
echo "  ✅ 添加账单成功"
echo ""

# 测试 5: 测试查看账单
echo "测试 5: 测试查看账单..."
node "$SCRIPT_DIR/scripts/list-bills.js"
echo "  ✅ 查看账单成功"
echo ""

# 测试 6: 测试标记还款
echo "测试 6: 测试标记还款..."
node "$SCRIPT_DIR/scripts/mark-paid.js" 1 "测试还款"
echo "  ✅ 标记还款成功"
echo ""

# 测试 7: 测试删除账单
echo "测试 7: 测试删除账单..."
node "$SCRIPT_DIR/scripts/remove-bill.js" 1
echo "  ✅ 删除账单成功"
echo ""

# 清理测试数据
echo "清理测试数据..."
echo '{"bills":[],"paymentHistory":[]}' > "$DATA_FILE"
echo "  ✅ 已清理"
echo ""

echo "=========================="
echo "✅ 所有测试通过！"
echo ""
