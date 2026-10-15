#!/bin/bash
# 自动更新 MCP 客户端配置文件

echo "=========================================="
echo "MCP 客户端配置更新工具"
echo "=========================================="
echo

# 检测操作系统
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    CONFIG_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    CONFIG_FILE="$HOME/.config/Claude/claude_desktop_config.json"
else
    echo "⚠ 未识别的操作系统: $OSTYPE"
    echo "请手动配置 MCP 客户端"
    exit 1
fi

echo "配置文件位置: $CONFIG_FILE"
echo

# 检查配置文件是否存在
if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚠ 配置文件不存在"
    echo "创建新配置文件..."
    mkdir -p "$(dirname "$CONFIG_FILE")"
    echo '{"mcpServers":{}}' > "$CONFIG_FILE"
fi

# 备份现有配置
BACKUP_FILE="${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$CONFIG_FILE" "$BACKUP_FILE"
echo "✓ 已备份到: $BACKUP_FILE"
echo

# 获取当前目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH="$SCRIPT_DIR/venv/bin/python"
SERVER_PATH="$SCRIPT_DIR/server.py"

# 检查文件是否存在
if [ ! -f "$PYTHON_PATH" ]; then
    echo "✗ Python 不存在: $PYTHON_PATH"
    echo "请确保虚拟环境已创建"
    exit 1
fi

if [ ! -f "$SERVER_PATH" ]; then
    echo "✗ 服务器不存在: $SERVER_PATH"
    exit 1
fi

# 获取 VERDI_HOME
if [ -z "$VERDI_HOME" ]; then
    echo "⚠ VERDI_HOME 未设置，使用默认值: /opt/verdi"
    VERDI_HOME="/opt/verdi"
fi

echo "配置信息:"
echo "  Python: $PYTHON_PATH"
echo "  Server: $SERVER_PATH"
echo "  VERDI_HOME: $VERDI_HOME"
echo

# 生成新配置
cat > /tmp/fsdb_mcp_config.json << EOF
{
  "mcpServers": {
    "fsdb": {
      "command": "$PYTHON_PATH",
      "args": [
        "$SERVER_PATH"
      ],
      "env": {
        "VERDI_HOME": "$VERDI_HOME",
        "LD_LIBRARY_PATH": "$VERDI_HOME/share/NPI/lib/linux64:$VERDI_HOME/platform/linux64/bin"
      }
    }
  }
}
EOF

echo "生成的配置:"
cat /tmp/fsdb_mcp_config.json
echo
echo "=========================================="
echo

# 询问是否更新
read -p "是否更新配置文件? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 读取现有配置
    if command -v jq &> /dev/null; then
        # 使用 jq 合并配置
        jq -s '.[0] * .[1]' "$CONFIG_FILE" /tmp/fsdb_mcp_config.json > /tmp/merged_config.json
        mv /tmp/merged_config.json "$CONFIG_FILE"
        echo "✓ 配置已更新（使用 jq 合并）"
    else
        # 直接覆盖（如果没有 jq）
        cp /tmp/fsdb_mcp_config.json "$CONFIG_FILE"
        echo "✓ 配置已更新（直接覆盖）"
        echo "⚠ 建议安装 jq 以保留其他配置: sudo apt install jq"
    fi
    
    echo
    echo "=========================================="
    echo "✅ 配置完成！"
    echo "=========================================="
    echo
    echo "下一步:"
    echo "  1. 重启 Claude Desktop"
    echo "  2. 检查 MCP 服务器是否出现在工具列表中"
    echo "  3. 尝试查询 FSDB 文件"
    echo
    echo "如果遇到问题:"
    echo "  - 查看备份: $BACKUP_FILE"
    echo "  - 检查日志: /tmp/fsdb_server.log"
    echo "  - 运行测试: python test_fsdb.py"
else
    echo
    echo "配置未更新"
    echo "手动配置请参考: mcp-config-example.json"
fi

# 清理临时文件
rm -f /tmp/fsdb_mcp_config.json

echo
echo "=========================================="
