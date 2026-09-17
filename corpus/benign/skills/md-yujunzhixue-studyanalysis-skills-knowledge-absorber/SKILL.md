---
name: knowledge-absorber
description: 深度解析链接、文档或代码，生成”全能导师级”的教学笔记（零基础直达精通）。具备”真理锚定”校验能力，自动识别幻觉与过时信息。支持国学风格渲染，自动清理广告和无用内容。
tags: [“learning”,”学习”,”analysis”,”分析”,”documentation”,”文档”,”knowledge-base”,”知识库”,”architecture”,”知识吸收”,”knowledge-absorber”,”verification”,”国学”,”classical-chinese”]
version: 4.5.0
---

# 用法

把链接、文档、图片或代码整理成一份可学习、可搜索、可继续提问的学习成品，并输出：

- `knowledge_card.md`
- `knowledge_card.interactive.html`

只需要一条命令：

```bash
python scripts/run_full_pipeline.py “<链接或本地文件路径>” [“<更多链接或文件路径>”]
```

示例：

```bash
python scripts/run_full_pipeline.py “https://example.com/article”
python scripts/run_full_pipeline.py “E:\资料\AI导论.pdf”
python scripts/run_full_pipeline.py “E:\资料\架构图.png”
python scripts/run_full_pipeline.py “E:\repo\main.py”
python scripts/run_full_pipeline.py “https://example.com/article” “E:\资料\补充说明.pdf”
```

也支持这种自然语言写法：

```bash
python scripts/run_full_pipeline.py “学习这个 https://example.com/article”
```

# 核心流程

本技能采用 **真理锚定协议 (Truth Anchoring Protocol)** 确保内容准确性。

## 第一步：智能摄取 (Content Ingestion)

运行脚本获取干净的内容。脚本会自动清洗 HTML 噪音、广告和无用内容，并处理多模态内容（PDF/OCR）。

**清理机制**：
- 自动移除广告、导航、页脚、社交分享等UI元素
- 过滤包含噪音关键词的短文本（登录、注册、下载、关注等）
- 识别并移除广告容器（通过class/id模式匹配）
- 不保留明显的UI元素和营销内容
- 不保留”谢谢大佬的支持”等打赏提示
- 不保留页面导航和推荐链接

## 第二步：真理锚定 (Truth Anchoring)

**”不要轻信任何文本，哪怕它看起来很专业。”**

在生成内容之前，必须先对摄取的内容进行**准确性校验**。

**验证流程**：
1. **提取核心主张**：识别文中所有关键事实性主张（具体数据、API用法、历史事件、绝对化论断）
2. **联网审计**：调用 `WebSearch` 验证每个主张，搜索必须包含当前年份（2026）以确保时效性
3. **生成校准报告**：构建”红队报告”，标注错误、过时或有争议的内容
4. **显式标注**：在最终输出中明确标注所有不确定或有争议的信息

**验证要求**：
- 每个关键主张都必须经过搜索验证
- 不得直接使用未经验证的原文内容
- 不得忽略明显的时效性问题（如”2020年最新”）
- 不得省略对绝对化论断的验证（”总是”、”从不”、”必须”）
- 不得在发现错误后不标注就直接使用

**标注规范**：
- 过时信息必须标注”[已过时]”
- 有争议内容必须标注”[存在争议]”
- 无法确认的内容必须标注”[待确认]”

## 第三步：生成教学内容

根据清洗后的内容和校准报告，生成多模态输出。

**内容适配**：
- **技术类**：使用现代清爽风格（Apple Design 风格）
- **国学/人文类**：使用水墨国学风格（传统中文字体、水墨背景、印章装饰）

**国学风格触发条件**：
当标题、来源、标签或内容前几段包含以下任一关键词时，自动应用国学风格：
- **经典文献**：论语、庄子、道德经、史记、诗经、易经、孟子、荀子、春秋、左传、礼记、周易、尚书、大学、中庸
- **学派思想**：国学、古文、佛、儒、道、哲学、人文、儒家、道家、佛家、法家、墨家、兵家、禅宗、理学、心学、玄学
- **历史人物**：孔子、老子、孟子、庄子、荀子、墨子、韩非子、朱熹、王阳明、程颐、程颢
- **文学体裁**：古诗、词、赋、骈文、散文、文言文
- **其他**：经史子集、四书五经、诸子百家、传统文化

## 第四步：质量验收 (Quality Assurance)

**交付前必须确认以下项目：**

1. ✅ HTML 包含 `<script>` 搜索逻辑
2. ✅ 国学模式下使用传统中文字体（宋体、思源宋体）和水墨风格
3. ✅ 包含 Mermaid 认知地图
4. ✅ 包含 5-8 个 FAQ
5. ✅ 内容已清理干净（无广告、无UI元素、无打赏提示）
6. ✅ 所有关键主张经过真理锚定验证
7. ✅ 不确定内容有明确标注

**不得出现以下情况**：
- 输出包含广告或营销内容的HTML
- 输出未经验证的事实性主张
- 国学模式下使用现代西文字体
- 省略搜索功能
- 省略Mermaid图表

**若任一项不符合要求，必须重新生成。**

# 输出位置与文件

脚本会在 `outputs/knowledge_YYYYMMDD_*` 下生成一个输出文件夹，且最终只保留两个文件：

- `knowledge_card.md`
- `knowledge_card.interactive.html`

# 导师模式（交互 HTML 可选）

导师模式需要本地 relay 才能在浏览器里调用模型：

- `python scripts/mentor_relay.py`（默认 `http://127.0.0.1:8760`）

如果只是阅读/搜索正文，不需要启动 relay。

# 支持的输入

- URL 链接
- PDF / Word / Markdown / TXT
- PNG / JPG / JPEG / WEBP
- Python / JavaScript / TypeScript / Java / C / C++ / Go / Rust 等代码文件
- 一次传入多个链接或文件
