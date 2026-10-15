# Export Specification

Deep-read 模式导出的 Obsidian Markdown 格式规范。

## 文件名

```
{第一作者}_{年份}_{关键词}_分析.md
```

示例: `Zhang_2024_CRISPRi-代谢调控_分析.md`

## YAML Frontmatter

```yaml
---
title: "论文完整标题"
first_author: "Smith"
year: 2024
doi: "10.xxx/xxxx"
analysis_date: 2026-07-23
mode: deep-read
tags: [CRISPRi, metabolic engineering, strain engineering]
assessment_boundary: "全文评估，Methods部分完整"
figure_count: 6
figure_discrepancies: 1
major_concerns: 2
---
```

### 字段说明

| 字段 | 必需 | 说明 |
|------|------|------|
| `title` | ✅ | 论文完整标题（原语言） |
| `first_author` | ✅ | 第一作者姓氏 |
| `year` | ✅ | 发表年份 |
| `doi` | ✅ | DOI（如有） |
| `analysis_date` | ✅ | 分析日期 |
| `mode` | ✅ | 固定为 `deep-read` |
| `tags` | ✅ | 2-6 个关键词标签 |
| `assessment_boundary` | 新增 | 输入范围和评估限制 |
| `figure_count` | 新增 | 解读的图表总数 |
| `figure_discrepancies` | 新增 | 存在不一致的图表数量 |
| `major_concerns` | 新增 | MAJOR 发现总数 |

所有新增字段均可选——旧版 deep-read 输出不受影响。

## 章节排序

新版 deep-read 导出按以下顺序排列：

```
---
YAML frontmatter
---

# {论文标题} — Deep-Read 分析

## 评估边界声明 [NEW]

## 1. 核心主张

## 2. 证据链与逻辑骨架

## 2.5 实验结果叙事线 [NEW]
  - 故事弧线
  - 实验步骤推演
  - 叙事逻辑图
  - 关键转折点
  - 可复现性检查清单

## 图表解读 [NEW]
  - 逐图解读（Fig. 1, Fig. 2, ... Table 1, ... Supplementary Fig. S1, ...）
  - 图表-文本一致性汇总表

## 3. 方法严谨性 [UPGRADED]
  - 对照设计
  - 重复与样本量
  - 统计方法
  - 菌株/试剂信息
  - 数据可获取性
  - 实验方法细节
  - 方法严谨性总评

## 4. 新颖性 [DEEPENED]
  - 4a. 方法新颖性（主张 + 证据 + 置信度）
  - 4b. 概念新颖性
  - 4c. 发现新颖性
  - 4d. 资源新颖性

## 5. 隐藏假设与替代解释

## 6. 过度宣称检测

## 7a. 科学重要性 [NEW]

## 7b. 领域推进

## 8. 方法可迁移性

## 9. 概念启发

## 10. 资源可用性

## 11. 空白揭示

## 12. 行动引导（三轴优先级排序）

## 严重问题汇总 [NEW]
  - MAJOR 发现列表（每个附解决方案测试）
  - MINOR 发现列表
```

## 向后兼容

1. **旧版 deep-read 输出**不含新章节，不影响已有 Markdown 文件的阅读
2. **新增字段均为可选**，旧工具消费 frontmatter 时不会因未知字段崩溃
3. **维度编号不变**：dim 3 仍是方法严谨性，dim 4 仍是新颖性
4. **图表解读**放在叙事线之后、严谨性之前的原因：读者先理解故事→再看图表证据→最后评判证据质量。这是自然的信息消费顺序

## 导出流程

1. 组装以上所有章节为完整 Markdown
2. 写入 `{export_dir}/{第一作者}_{年份}_{关键词}_分析.md`
3. `export_dir` 从技能目录下的 `config.json` 读取；为空时先询问用户要存到哪里，写入 config.json 后不再重复询问
4. 不需要额外运行脚本——纯 Markdown 写入即可
