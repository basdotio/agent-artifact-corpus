---
name: badminton-playwright-mobile-qa
description: Use when writing or updating mobile-first Playwright coverage for the badminton H5 flow, including home CTA, upload readiness, candidate clip selection, processing progress, report rendering, history, compare, and error recovery.
---

# Badminton Playwright Mobile QA

## 何时使用

当任务涉及前端主流程自动化验证时使用：

- 新增或修改 Playwright E2E
- 验证首页到上传、候选片段选择、处理中、报告页渲染
- 调整 mock API、fixture 数据、移动端交互选择器

## 先读什么

当前 Playwright 已经接入且是移动端优先，不需要从零搭建。先读：

- `frontend/playwright.config.ts`
- `frontend/e2e/home-and-upload.spec.ts`
- `frontend/e2e/processing.spec.ts`
- `frontend/e2e/report-history-compare.spec.ts`
- `frontend/e2e/error.spec.ts`
- `frontend/e2e/support/mockApi.ts`

真实约束：

- 默认项目是 `mobile-chromium`
- 使用 iPhone 13 viewport
- 测试自启 Vite dev server
- mock 覆盖 `/api` 与 `/artifacts`

## 工作顺序/决策顺序

1. 先确认要覆盖的是哪条真实用户路径，再决定补新 spec、补场景 builder，还是只更新 mock/fixture。
2. 优先让测试围绕可见行为断言，再回头补稳定选择器；不要先盯 DOM 结构和 className。
3. 如果 spec 文件开始重复 setup、fixture JSON 或多段相似路径，先抽共享 helper / scenario builder 再加场景。
4. mock 数据要始终贴近真实 contracts；契约变化应先修共享形状，再修断言。
5. 最终说明要能回答“测的是哪条用户路径”“为什么足够”这两个问题。

## 核心规则

1. 先测真实用户路径，不测实现细节。
2. selector 优先级：
   - `getByRole`
   - 可读名称
   - 稳定 `testid`（只有在 role/name 不稳定时）
3. 默认优先 mock API，保持稳定与可重复，不把真实 backend 当 E2E 前提。
4. 测试要体现当前真实主流程：
   - 首页 CTA
   - 上传前就绪检查
   - 上传并粗扫片段
   - 用户确认候选片段
   - 处理中步骤反馈
   - 报告页/历史/对比页渲染
   - `taskId` 深链进入 `/analyses/:taskId/processing`、`/analyses/:taskId/report`、`/analyses/:taskId/comparison`
5. 当共享契约变化时，要同步更新：
   - `frontend/e2e/support/mockApi.ts`
   - fixtures
   - 断言文案或状态
6. 复用优先：优先扩展已有 mock API、fixture builder、共享 helper 和通用断言，不要在 spec 中平行复制 setup。
7. 模块拆分优先：shared mock、scenario builder、data factory、页面级断言应按职责拆开，不要让单个 spec 同时背负所有数据准备与所有流程。
8. 文件体量控制：
   - 单个 spec 文件通常接近 250 行就要考虑按场景拆分
   - fixture builder、mock helper 超过约 200 行应按页面或流程拆分
9. 不要把 CSS 结构、类名、内部 state 当断言主目标，也不要把大段内联 JSON 当默认写法。

## 截图 / 壳层回归补充规则

- 页面重排后，除了流程断言，还要验证顶部栏、底部 Tab、主 CTA 是否在滚动时保持稳定。
- 对移动端产品壳层，优先断言“主滚动发生在 `main`，而不是 `window`”。
- 当页面进入空态、错误态或结果页时，也要检查是否仍然保留了错误的长文档流布局。
- 如果任务明确要求产品化或截图 review，至少覆盖首页、上传准备、选片页、处理中、报告、历史、对比、错误其中的关键页面。
- 当首屏观感是风险点时，补截图或视觉快照，而不是只断言链接和文案存在。

## 何时联动其他 skills

- `mobile-ui-interaction-design`：需要把 Playwright 验证进一步用于截图 review、视觉层级复核和 UI polish 时
- `badminton-h5-product-ui`：页面产品化后需要补测试
- `badminton-analysis-flow`：上传、选片、处理状态变化
- `shared-contracts-and-adapters`：mock 数据需要跟共享契约同步
- `repo-delivery-baseline`：需要决定是否补跑整个前端测试路径

## 何时读取 examples/

确认要覆盖的用户路径后再读对应 example：

- `examples/homepage-to-upload.spec-example.md`：首页到上传准备路径变化时读
- `examples/candidate-clip-selection.spec-example.md`：候选片段选择或推荐逻辑变化时读
- `examples/report-page-rendering.spec-example.md`：报告页渲染与核心卡片断言变化时读
- `examples/fixed-shell-scroll-assertions.md`：需要验证固定导航、独立滚动和 CTA 可见性时读

## 任务完成后的输出要求

最终交付说明至少要写清：

- 新增或修改了哪些 Playwright 场景
- 覆盖的是哪条真实用户路径
- 是否更新了 mock API 或 fixtures
- 如果只做了局部验证，要明确哪些主流程还没覆盖
