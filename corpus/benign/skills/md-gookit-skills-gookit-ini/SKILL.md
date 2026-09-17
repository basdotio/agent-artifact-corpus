---
name: gookit-ini
description: Go INI 文件解析和配置管理库。支持读取/写入 INI 数据、结构体映射、变量引用、环境变量解析、多文件加载等。用于 Go 应用配置管理。
author: auto-generated
source: https://github.com/gookit/ini
tags: [go, ini, config, configuration, parser, dotenv]
version: 1.0.0
generated: 2026-01-28
---

# INI OpenCode Skill

Go 编写的 INI 文件解析和配置管理库。

## Quick Start

```bash
go get github.com/gookit/ini/v2
```

```go
package main

import (
    "github.com/gookit/ini/v2"
)

func main() {
    ini.LoadExists("config.ini")
    
    name := ini.String("name")
    age := ini.Int("age")
    val := ini.String("sec1.key")
    
    _ = name
    _ = age
    _ = val
}
```

## 核心功能

### 数据读写

- **读取数据** - 支持 `Int`, `Bool`, `String`, `StringMap` 等类型
- **键路径** - 支持 `section.key` 路径写法
- **数据设置** - 支持 `Set` 方法修改配置

详细用法见 [basic-usage.md](basic-usage.md)

### 高级特性

- **结构体映射** - 自动映射配置到 struct
- **变量引用** - 支持 `%(varName)s` 变量替换
- **环境变量** - 自动解析 `${ENV}` 格式
- **注释保留** - 写入时保留原始注释

详细用法见 [advanced.md](advanced.md)

### Dotenv 支持

从 `.env` 文件加载环境变量：

```go
import "github.com/gookit/ini/v2/dotenv"

dotenv.Load(".", ".env")
val := dotenv.Get("KEY")
```

## 常用场景

| 场景 | 参考文档 |
|------|----------|
| 读取 INI 配置 | [basic-usage.md](basic-usage.md) |
| 写入 INI 配置 | [basic-usage.md](basic-usage.md) |
| 结构体映射 | [advanced.md](advanced.md) |
| 变量引用 | [advanced.md](advanced.md) |
| 环境变量 | [advanced.md](advanced.md) |
| Dotenv 加载 | [advanced.md](advanced.md) |

## 相关链接

- [Godoc](https://pkg.go.dev/github.com/gookit/ini/v2)
- [GitHub](https://github.com/gookit/ini)
- 更多格式支持: [gookit/config](https://github.com/gookit/config)
