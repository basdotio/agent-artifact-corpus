# Python 工具模块

这里是自有 Python 工具的唯一实现。按工具职责拆分模块，公共文件身份/报告能力在 `_artifact_common.py`；不要复制到 scripts、Skill 或旧实现目录。

CLI/MCP → application → registry/runner → launch_tool.py → grea.tools 模块。launch_tool.py 只做包定位和模块启动，支持尚未安装 grea 的可选依赖环境；工具选择仍以 registry 为准。子进程边界保留超时、取消和日志预算。legacy 保留原始 argv、输出和退出码。

模块导入不得解析命令行或写文件。可复用逻辑用函数提供；main 仅负责参数与调用。可选依赖保持独立，不强行装入核心运行时。测试按原输入输出和错误行为验证，修改路径不修改工具 ID。

文件路径迁移见 [映射](../../../schemas/document-path-map.json)，运行方法见 [使用指南](../../../docs/使用指南.md)。
