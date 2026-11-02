#!/bin/bash

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

export DANGEROUSLY_OMIT_AUTH=true
npx @modelcontextprotocol/inspector uv --directory "$SCRIPT_DIR" run src/main.py
