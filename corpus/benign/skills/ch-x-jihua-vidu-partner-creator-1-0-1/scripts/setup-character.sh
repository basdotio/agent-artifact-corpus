#!/bin/bash
# 角色初始化脚本
# 根据角色名搜索信息并生成设定

set -e

# 参数
CHARACTER_NAME="$1"
VIDU_KEY="${VIDU_KEY:-}"

if [ -z "$CHARACTER_NAME" ]; then
  echo "Usage: $0 <character_name>"
  echo ""
  echo "Example:"
  echo "  $0 \"孙策\""
  echo "  $0 \"魏无羡\""
  echo "  $0 \"原创: 25岁温柔男性，黑色短发，蓝色眼睛\""
  exit 1
fi

echo "============================================"
echo "角色初始化: $CHARACTER_NAME"
echo "============================================"
echo ""

# 检查是否原创角色
if [[ "$CHARACTER_NAME" == *"原创"* ]] || [[ "$CHARACTER_NAME" == *"原创:"* ]]; then
  echo "检测到原创角色，跳过搜索..."
  IS_ORIGINAL=true
else
  echo "搜索角色信息..."
  IS_ORIGINAL=false
  
  # 这里需要调用搜索工具
  # Agent 会处理这部分
fi

echo ""
echo "============================================"
echo "请 Agent 完成以下步骤："
echo "============================================"
echo ""
echo "1. 使用搜索工具搜索角色信息："
echo "   - tavily search \"$CHARACTER_NAME 角色设定\""
echo "   - tavily search \"$CHARACTER_NAME 外貌形象\""
echo "   - tavily search \"$CHARACTER_NAME 性格特点\""
echo ""
echo "2. 根据搜索结果，生成角色设定文件："
echo "   ~/.openclaw/workspace/skills/partner-creator/references/current-character.md"
echo ""
echo "3. 生成角色三视图："
echo "   export VIDU_KEY=\"vda_xxx\""
echo "   ./scripts/generate-reference.sh \"角色外形描述\" [anime/realistic]"
echo ""
echo "4. 将三视图URL写入配置文件："
echo "   REFERENCE_IMAGE_URL: [生成的URL]"
echo "   BASE_DESCRIPTION: [角色基础描述]"
echo ""
echo "============================================"

# 输出配置路径
echo ""
echo "配置文件路径:"
echo "  $HOME/.openclaw/workspace/skills/partner-creator/references/current-character.md"
