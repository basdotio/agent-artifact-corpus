---
name: {{name}}
version: {{version}}
author: {{author}}
description: {{description}}
tags:
{{#each tags}}
  - {{this}}
{{/each}}
---

# {{uppercase name}}

> {{description}}

**Version:** {{version}} | **Author:** {{author}}

---

## 高级特性演示

此示例展示了 USK 的高级功能,包括插件系统、自定义构建流程和性能优化技巧。

{{#if platform.claude}}
### 🎯 Claude 平台 - 完整文档

本示例重点展示:
- 插件系统的使用和开发
- 自定义构建脚本编写
- 性能优化最佳实践
- 缓存策略和增量构建
- 错误处理和调试技巧
{{/if}}

{{#if platform.codex}}
### ⚡ Codex 平台 - 快速参考

核心特性:
- 插件系统使用
- 自定义构建
- 性能优化
{{/if}}

---

## 插件系统

USK 提供了强大的插件系统,允许你在构建过程的不同阶段插入自定义逻辑。

{{#if platform.claude}}
### 插件生命周期

USK 插件系统提供了以下生命周期钩子:

1. **beforeBuild** - 构建开始前
2. **afterConfigLoad** - 配置加载后
3. **beforePlatformBuild** - 单个平台构建前
4. **afterTemplateRender** - 模板渲染后
5. **beforeFileWrite** - 文件写入前
6. **afterFileWrite** - 文件写入后
7. **afterPlatformBuild** - 单个平台构建后
8. **afterBuild** - 所有构建完成后
9. **onError** - 发生错误时

### 内置插件

USK 提供了两个常用的内置插件:

1. **loggerPlugin** - 详细的构建日志
2. **minifyPlugin** - Markdown 内容压缩

### 使用方式

通过编程方式使用插件,在项目中创建 build.js 文件。
{{/if}}

{{#if platform.codex}}
### 插件钩子

- beforeBuild, afterBuild
- beforePlatformBuild, afterPlatformBuild
- afterTemplateRender
- onError

### 内置插件

- loggerPlugin - 构建日志
- minifyPlugin - 内容压缩
{{/if}}

---

## 自定义构建脚本

{{#if platform.claude}}
### 编程式 API

USK 提供了完整的编程式 API,允许完全自定义构建流程。

### 基本示例

创建 build.js 文件使用 USK Builder API 进行自定义构建。

### 高级配置

可以配置:
- 缓存策略
- 并发限制
- 错误处理
- 自定义 helpers
- Partial 注册

### 构建流程控制

完全控制构建流程,包括:
- 条件构建
- 平台选择
- 增量更新
- 自定义输出
{{/if}}

{{#if platform.codex}}
### 编程式 API

使用 SkillBuilder API 自定义构建流程。

### 配置选项

- 缓存策略
- 并发限制
- 自定义 helpers
{{/if}}

---

## 性能优化

{{#if platform.claude}}
### 缓存策略

USK 使用智能缓存系统加速构建:

1. **模板缓存** - 缓存已渲染的模板
2. **文件哈希** - 基于内容的缓存键
3. **依赖追踪** - 自动失效相关缓存
4. **跨平台共享** - 不同平台共享缓存

### 并发构建

默认限制 5 个并发构建,可以根据机器性能调整:
- 单核/双核: concurrency = 2
- 四核: concurrency = 5
- 八核+: concurrency = 10

### 增量构建

Watch 模式下自动使用增量构建:
- 只重新渲染变化的文件
- 保留未变化的输出
- 跳过清理步骤

### 性能监控

使用 verbose 模式查看性能指标:
- 渲染时间
- 文件复制时间
- 总构建时间
- 缓存命中率

### 优化建议

1. 启用缓存 (默认启用)
2. 合理设置并发数
3. 使用 Watch 模式开发
4. 避免不必要的资源文件
5. 优化模板复杂度
{{/if}}

{{#if platform.codex}}
### 性能优化

- 智能缓存系统
- 并发构建 (默认 5)
- 增量更新 (Watch 模式)
- 使用 --verbose 监控性能
{{/if}}

---

## 错误处理

{{#if platform.claude}}
### 错误类型

USK 定义了多种错误类型:
- ConfigValidationError - 配置验证错误
- TemplateEngineError - 模板引擎错误
- BuildError - 构建错误
- CacheError - 缓存错误

### 错误报告

USK 提供详细的错误报告:
- 错误消息和上下文
- 错误代码分类
- 修复建议
- 相关文档链接

### 错误恢复

- 验证错误: 修复配置文件
- 模板错误: 检查 Handlebars 语法
- 构建错误: 查看详细日志
- 缓存错误: 清理缓存重试

### 调试模式

使用 --verbose 启用详细输出:
- 构建步骤详情
- 错误堆栈跟踪
- 性能指标
- 缓存使用情况
{{/if}}

{{#if platform.codex}}
### 错误处理

- 详细的错误报告
- 修复建议
- 使用 --verbose 调试
- 清理缓存重试
{{/if}}

---

## 实战技巧

{{#if platform.claude}}
### 1. 自定义 Helper

注册自定义 Handlebars helper 扩展模板功能。

### 2. 条件构建

根据环境变量或配置条件性构建不同平台。

### 3. 构建钩子

在构建过程中插入自定义逻辑,如:
- 自动生成文档
- 代码质量检查
- 自动部署
- 通知发送

### 4. 缓存管理

合理使用缓存提升性能:
- 开发时启用缓存
- CI/CD 中清理缓存
- 使用 --force 强制重建

### 5. 多环境构建

为不同环境配置不同的构建选项:
- 开发环境: 完整输出
- 生产环境: 压缩优化
- 测试环境: 包含测试数据

### 6. 集成 CI/CD

在 CI/CD 管道中使用 USK:
- 自动验证配置
- 自动构建和测试
- 自动发布
- 性能监控
{{/if}}

{{#if platform.codex}}
### 实战技巧

1. 自定义 Helper 扩展功能
2. 条件构建支持多环境
3. 使用构建钩子自动化
4. 合理使用缓存
5. 集成 CI/CD 流程
{{/if}}

---

## 最佳实践

{{#if platform.claude}}
### 项目结构

推荐的项目结构:
- src/ - 源文件
- templates/ - 模板片段
- scripts/ - 构建脚本
- dist/ - 输出目录
- build.js - 自定义构建
- usk.config.json - 配置文件

### 配置管理

- 使用版本控制管理配置
- 敏感信息使用环境变量
- 为不同环境准备不同配置
- 定期验证配置有效性

### 开发工作流

1. 使用 Watch 模式开发
2. 定期运行 validate 和 doctor
3. 及时提交代码
4. 使用分支管理特性
5. 编写完整的文档

### 性能优化

- 启用缓存机制
- 合理设置并发数
- 避免不必要的资源
- 优化模板复杂度
- 使用增量构建

### 测试策略

- 验证配置文件
- 测试模板渲染
- 检查输出质量
- 性能基准测试
- 跨平台测试
{{/if}}

{{#if platform.codex}}
### 最佳实践

- 合理的项目结构
- 版本控制管理配置
- Watch 模式开发
- 启用缓存优化性能
- 定期验证和诊断
{{/if}}

---

## 进阶主题

{{#if platform.claude}}
### 插件开发

开发自定义插件扩展 USK 功能:
- 实现生命周期钩子
- 访问构建上下文
- 修改构建流程
- 添加自定义功能

### 模板引擎扩展

扩展模板引擎功能:
- 注册自定义 helpers
- 注册 partials
- 自定义渲染选项
- 实现自定义指令

### 缓存系统定制

定制缓存系统行为:
- 自定义缓存键生成
- 配置缓存过期策略
- 实现自定义存储
- 缓存预热

### 构建优化

深度优化构建性能:
- 并行任务调度
- 资源预加载
- 智能依赖分析
- 构建流水线

### 监控和分析

监控和分析构建性能:
- 性能指标收集
- 构建时间分析
- 资源使用监控
- 错误率统计
{{/if}}

{{#if platform.codex}}
### 进阶主题

- 插件开发
- 模板引擎扩展
- 缓存系统定制
- 构建优化
- 监控和分析
{{/if}}

---

## 资源链接

- **USK 仓库**: https://github.com/JiangDing1990/universal-skill-kit
- **插件文档**: 查看 packages/builder/src/plugin/
- **API 文档**: 查看源码和类型定义
- **问题反馈**: https://github.com/JiangDing1990/universal-skill-kit/issues

{{#if platform.claude}}
### 相关示例

1. **basic-skill** - 基础功能入门
2. **multi-platform** - 多平台特性
3. **advanced** (当前) - 高级功能演示

### 学习路径

1. 掌握基础用法 (basic-skill)
2. 学习平台适配 (multi-platform)
3. 深入高级特性 (advanced)
4. 阅读源码理解实现
5. 开发自定义插件
{{/if}}

---

## 许可证

MIT License

---

**Advanced features powered by Universal Skill Kit v{{version}}**

{{#if platform.claude}}
💡 **提示**: 这是高级示例,展示了 USK 的插件系统和自定义构建能力。建议先学习 basic-skill 和 multi-platform 示例。
{{/if}}

{{#if platform.codex}}
💡 **提示**: 高级功能示例。完整文档请查看 Claude 平台版本。
{{/if}}
