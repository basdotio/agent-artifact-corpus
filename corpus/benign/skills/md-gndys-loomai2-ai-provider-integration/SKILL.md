---
name: ai-provider-integration
description: 在本仓库内对接 AI 文本/聊天与图像生成的通用流程：新增 Provider、增加模型、调整默认模型与计费规则，或扩展图片生成能力。用于“接入新模型/新厂商/新图片服务”的任务。
---

# AI 文本/图像通用接入

## 概览
提供新增/维护 AI Provider 与模型的统一步骤，确保 types、配置、工厂、路由与计费保持一致。

## 快速开始
1. 先读 `references/repo-touchpoints.md` 找到需改文件。
2. 再读 `references/workflow.md` 选择对应流程（新增 provider / 新模型 / 新图片 provider / Evolink 图片模型）。

## 关键约定
- Chat provider 必须在 `libs/ai/types.ts`、`libs/ai/config.ts`、`libs/ai/providers.ts`、`config/ai.ts` 同步更新。
- Image provider 需同时更新 `libs/ai/types.ts`、`libs/ai/providers.ts`、`libs/ai/image.ts`。
- Evolink 图片走异步任务轮询流程，复用 `libs/ai/evolink.ts` 与 `apps/next-app/app/api/image-generate/route.ts`。

## 常见操作
### 新增 Chat Provider
按 `references/workflow.md` 的“新增文本/聊天 Provider”步骤执行，优先参考 `devdove` 的写法。

### 新增图片 Provider
按 `references/workflow.md` 的“新增图片 Provider（非 Evolink）”步骤执行，统一在 `generateImageResponse` 分发。

### 新增模型/修改默认模型
只改 `config/ai.ts` 或 `config/aiImage.ts`，必要时同步 `config/credits.ts`。

## 参考资料
- `references/repo-touchpoints.md`
- `references/workflow.md`
