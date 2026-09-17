---
name: code-shorters
description: 自动化代码模块化重构工具。用于检测、分类和重构超过130行的代码文件。支持 Rust, Python, C++, JavaScript, Markdown。使用 Git 策略管理版本，自动串行调用语言专项子skill，一键完成所有重构任务。
---

# Code Shorters (代码精简与模块化)

自动化代码模块化重构工具，用于将大型代码文件拆分为符合"130行铁律"的模块化结构。

## 概述

此 Skill 是一个**主调度器**，负责：
1. 扫描代码仓库并统计行数（包含注释）
2. 按行数分类：130-250行（警告）和 ≥250行（关键）
3. 检测编程语言（后缀名 + 内容特征分析）
4. 检查 Git 环境状态（仓库存在性 + 未提交修改）
5. 计算复杂度并生成优先级评分
6. 自动串行调用对应的语言专项子skill
7. 生成可视化重构报告（Markdown/HTML）

## 触发时机

当用户需要：
- 批量重构项目中的长文件
- 检查代码库的模块化健康度
- 按行数和复杂度对文件分类
- 一键完成多个文件的重构任务

## 工作流程

### 步骤 1：Git 环境检查

首先验证 Git 仓库状态，确保版本安全：

```bash
# 执行 Git 检查
python scripts/git_checker.py
```

**检查规则**：
1. 当前目录必须是 Git 仓库（检测 `.git` 目录）
2. 不能有未提交的修改（`git status --porcelain` 检测）
3. 未通过检查则**立即退出**，不执行任何修改

### 步骤 2：递归扫描目录

扫描指定目录（默认当前目录），识别所有代码文件：

```bash
# 执行扫描
python scripts/main_analyzer.py --path . --recursive
```

**扫描支持的语言后缀**：
- Rust: `.rs`
- Python: `.py`
- C++: `.cpp`, `.h`, `.hpp`
- JavaScript/TypeScript: `.js`, `.ts`, `.jsx`, `.tsx`
- Markdown: `.md`

### 步骤 3：行数统计（包含注释）

计算每个文件的总行数，**包含注释行和代码行**：

**语言特定注释规则**：
- Rust: `//`, `/* */`
- Python: `#`, `"""""`
- C++: `//`, `/* */`
- JS: `//`, `/* */`
- MD: `<!-- -->`

### 步骤 4：复杂度检测与优先级排序

集成多语言 lint 工具计算复杂度：

| 语言 | Lint 工具 | 命令 |
|------|-----------|-------|
| Rust | cargo clippy | `cargo clippy --message-format=json` |
| Python | pylint | `pylint --output-format=json` |
| C++ | cpplint | `cpplint --output-format=json5` |
| JavaScript | eslint | `eslint --format=json` |

**优先级评分公式**：
```
Priority Score = (行数 × 0.4) + (复杂度 × 0.3) + (嵌套深度 × 0.2) + (函数数量 × 0.1)
```

### 步骤 5：生成分类报告

生成 JSON 格式的分类报告：

```json
{
  "warning_files": [
    {"path": "src/parser.rs", "language": "rust", "lines": 145, "priority": 58.0},
    {"path": "lib/database.rs", "language": "rust", "lines": 189, "priority": 75.6}
  ],
  "critical_files": [
    {"path": "src/main.rs", "language": "rust", "lines": 320, "priority": 128.0},
    {"path": "server/handler.rs", "language": "rust", "lines": 412, "priority": 164.8}
  ],
  "statistics": {
    "total_files": 5,
    "warning_count": 2,
    "critical_count": 2
  }
}
```

### 步骤 6：自动串行调用子 Skill

按照优先级顺序，自动调用对应的语言专项子skill：

```bash
# 批处理模式（方案 B）
python scripts/batch_refactor.py
```

## 子技能路由

当 `code-shorters` 主 Skill 调用此 Skill 时：

| 检测到的语言 | 调用的子 Skill | 子 Skill 路径 |
|--------------|---------------|--------------|
| Rust (.rs) | rust-shorter | `code-shorters/rust-shorter/` |
| Python (.py) | python-shorter | `code-shorters/python-shorter/` |
| C++ (.cpp/.h) | cpp-shorter | `code-shorters/cpp-shorter/` |
| JS/TS (.js/.ts) | js-shorter | `code-shorters/js-shorter/` |
| Markdown (.md) | md-shorter | `code-shorters/md-shorter/` |

## 工具说明

### git_checker.py

Git 环境检查工具。

### language_detector.py

多层级语言检测工具。

### line_counter.py

精确的行数统计工具（包含注释）。

### complexity_detector.py

多语言复杂度检测工具。

### report_generator.py

可视化报告生成器。

### batch_refactor.py

批处理重构调度器。

### main_analyzer.py

主入口脚本。

## 配置选项

### 扫描配置

```bash
--path <directory>        # 指定扫描路径（默认当前目录）
--recursive              # 递归扫描子目录
--exclude <pattern>      # 排除文件/目录
--include-only <lang>    # 只扫描指定语言
```

### 复杂度配置

```bash
--no-complexity          # 跳过复杂度检测
--linter-path <path>     # 指定 lint 工具路径
```

### 输出配置

```bash
--output-dir <directory>  # 输出报告目录
--report-format <format>  # 报告格式：markdown 或 html
```

## 常见问题

### Q: 如何处理未安装 lint 工具的情况？

**A:** 显示警告信息并继续执行，仅按行数排序。

### Q: 如何确保重构后的代码能编译？

**A:** 每个子skill都会在重构后自动验证。

### Q: Git 策略如何保证版本安全？

**A:** 重构前检查 Git 状态，重构后自动提交。
