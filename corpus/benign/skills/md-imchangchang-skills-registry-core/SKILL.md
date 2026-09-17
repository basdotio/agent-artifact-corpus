---
name: python-core
description: Python 核心开发实践，使用 uv 进行项目开发。
created: 2026-02-12
status: stable
---

# Python 开发最佳实践（uv 版）

## 概述

使用 [uv](https://docs.astral.sh/uv/) 进行 Python 项目开发的最佳实践。

**核心理念**：uv 统一工具链，替代 pip + venv + pip-tools + pipx

## 适用场景

- Python 3.10+ 项目开发
- 需要快速依赖管理和环境隔离
- 代码质量和风格统一

## 为什么选择 uv

| 传统工具 | uv 替代方案 | 优势 |
|----------|-------------|------|
| pip + venv | `uv venv` + `uv pip` | 10-100 倍速度，统一命令 |
| pip-tools | `uv pip compile` | 原生支持，更快 |
| pipx | `uv tool` | 工具管理更简单 |
| poetry/pdm | `uv` | 标准 pyproject.toml，无锁定文件 |

## 快速开始

### 1. 安装 uv

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 pip（不推荐，仅作为备选）
pip install uv
```

### 2. 创建项目

```bash
# 创建项目目录
mkdir my-project && cd my-project

# 初始化 uv 项目
uv init

# 或使用 Python 3.11
uv init --python 3.11
```

生成的 `pyproject.toml`：
```toml
[project]
name = "my-project"
version = "0.1.0"
description = "项目描述"
readme = "README.md"
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "ruff>=0.1.0",
    "mypy>=1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
python-version = "3.10"
```

### 3. 管理依赖

```bash
# 添加生产依赖
uv add requests

# 添加开发依赖
uv add --dev pytest ruff mypy

# 添加可选依赖组
uv add --extra web flask django

# 同步依赖（安装 lock 文件中的所有依赖）
uv sync

# 升级依赖
uv add --upgrade requests
```

### 4. 运行代码

```bash
# 自动创建环境并运行
uv run python src/main.py

# 运行模块
uv run python -m my_package

# 运行工具（无需全局安装）
uv run ruff check src/
uv run pytest tests/

# 交互式 Python
uv run python
```

### 5. 工具管理（替代 pipx）

```bash
# 安装全局工具
uv tool install black
uv tool install httpie

# 运行工具
uvx http GET https://api.example.com

# 升级工具
uv tool upgrade black

# 列出已安装工具
uv tool list
```

## 项目结构

```
my-project/
├── pyproject.toml      # 项目配置（uv 核心）
├── uv.lock            # 锁定文件（自动生成）
├── README.md
├── src/
│   └── my_package/
│       ├── __init__.py
│       ├── module.py
│       └── cli.py
├── tests/
│   └── test_module.py
└── docs/
```

**注意**：uv 推荐 `src/` 布局，避免导入问题。

## 核心工作流

### 日常开发

```bash
# 1. 克隆项目后，一键安装所有依赖
uv sync

# 2. 运行代码
uv run python src/main.py

# 3. 添加新依赖
uv add sqlalchemy

# 4. 运行测试
uv run pytest

# 5. 代码检查
uv run ruff check src/
uv run ruff format src/
uv run mypy src/
```

### 锁定文件管理

```bash
# 生成锁定文件（固定所有依赖版本）
uv lock

# 同步到锁定文件的状态
uv sync

# 升级所有依赖并更新锁定文件
uv lock --upgrade
```

## pyproject.toml 完整配置

```toml
[project]
name = "my-project"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.31.0",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
]
web = [
    "flask>=3.0",
    "gunicorn>=21.0",
]

[project.scripts]
my-cli = "my_package.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# uv 配置
[tool.uv]
python-version = "3.10"

# 开发依赖组（uv 特有，比 optional-dependencies 更清晰）
[tool.uv.dev-dependencies]
dev = [
    "pytest>=7.4.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
]

[tool.ruff]
target-version = "py310"
line-length = 100
select = ["E", "F", "W", "I", "N", "UP", "B", "C4", "SIM"]
ignore = ["E501"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

## 代码规范

### 格式化

```bash
# 使用 ruff（uv 内置推荐）
uv run ruff format src/ tests/

# 检查
uv run ruff check src/ tests/

# 自动修复
uv run ruff check --fix src/ tests/
```

### 类型检查

```bash
uv run mypy src/
```

### 测试

```bash
# 运行所有测试
uv run pytest

# 详细输出
uv run pytest -v

# 带覆盖率
uv run pytest --cov=src --cov-report=html
```

## 常见场景

### 场景1：脚本运行

```bash
# 无需创建项目，直接运行脚本
uv run --with requests python script.py

# 多依赖
uv run --with requests --with beautifulsoup4 python scraper.py
```

### 场景2：不同 Python 版本

```bash
# 使用 Python 3.11
uv run --python 3.11 python --version

# 项目中切换版本
uv python install 3.11
uv python pin 3.11
```

### 场景3：构建和发布

```bash
# 构建包
uv build

# 发布到 PyPI（需要配置 token）
uv publish
```

## 迁移指南（从 pip/venv）

### 步骤1：创建 pyproject.toml

```bash
# 在新目录
uv init

# 或在现有项目
uv init --existing
```

### 步骤2：迁移依赖

```bash
# 从 requirements.txt
uv add -r requirements.txt

# 开发依赖
uv add --dev -r requirements-dev.txt

# 删除旧文件
rm requirements.txt requirements-dev.txt
```

### 步骤3：更新工作流

| 旧命令 | 新命令 |
|--------|--------|
| `python -m venv .venv` | `uv venv` |
| `source .venv/bin/activate` | `uv run`（无需激活） |
| `pip install -r requirements.txt` | `uv sync` |
| `pip install package` | `uv add package` |
| `pip list` | `uv pip list` |

## 检查清单

创建 Python 项目时检查：

- [ ] 使用 `uv init` 初始化项目
- [ ] 配置 `pyproject.toml`（依赖、工具）
- [ ] 使用 `uv add` 管理依赖（而非 pip）
- [ ] 使用 `uv run` 运行代码（无需激活环境）
- [ ] 提交 `uv.lock` 锁定文件到版本控制
- [ ] 配置 ruff/mypy 代码检查
- [ ] 使用 `uv tool` 管理 CLI 工具（替代 pipx）

## 参考

- [uv 官方文档](https://docs.astral.sh/uv/)
- [uv GitHub](https://github.com/astral-sh/uv)
