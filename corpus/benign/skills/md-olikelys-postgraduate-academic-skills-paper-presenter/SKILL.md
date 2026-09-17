---
name: "paper-presenter"
description: "帮助基础薄弱的博士生理解论文并准备组会PPT汇报，包括逐部分解析论文、讲解图表、生成问答清单。当用户需要准备论文汇报时调用。"
---

# Paper Presenter (论文汇报助手)

## 功能介绍
This skill helps PhD students with limited academic background understand research papers thoroughly and prepare for group meeting presentations.  
该技能帮助基础薄弱的博士生深入理解研究论文并准备组会汇报。

## 适用场景
- When a PhD student needs to present a research paper in a group meeting
- When a student with limited academic background struggles to understand a complex paper
- When preparing for potential questions from advisors or classmates
- 当博士生需要在组会上汇报研究论文时
- 当基础薄弱的学生难以理解复杂论文时
- 当需要准备导师或同学可能提出的问题时

## 输入格式要求
### 论文内容
- **完整论文**：提供PDF转换的完整文本或直接粘贴论文内容
- **章节划分**：如无法提供完整文本，需明确标注各章节（摘要、引言、方法等）
- **长度限制**：单篇论文建议不超过50页或20,000字
- **语言支持**：支持中英文论文，其他语言需提供英文翻译

### 额外信息（可选）
- 你的专业背景和知识缺口
- 你觉得特别困难的章节或图表
- 汇报时间限制
- 导师的具体要求

## 如何使用
1. Provide the full text of the research paper you need to present
2. Specify any particular sections or figures you find challenging
3. The skill will:
   - Break down the paper from title to figures in simple terms
   - Explain key concepts, methods, and results step by step
   - Generate a list of potential questions from advisors/classmates
4. 提供你需要汇报的完整论文文本
5. 指定你觉得有挑战性的特定章节或图表
6. 该技能将：
   - 用简单的语言从标题到图表逐部分解析论文
   - 逐步解释关键概念、方法和结果
   - 生成导师/同学可能提出的问题清单

## 输入验证机制
1. **完整性检查**：验证论文是否包含核心章节（摘要、方法、结果、结论）
2. **格式验证**：检查输入是否为可解析的文本格式
3. **相关性检查**：确认输入内容为学术研究论文
4. **长度验证**：检查论文长度是否在合理范围内

## 失败处理机制
1. **输入不完整**：提示用户补充缺失的论文部分
2. **格式错误**：指导用户转换为正确的文本格式
3. **超出范围**：明确告知用户当前论文类型不适用
4. **理解困难**：说明无法理解的具体原因，并建议简化问题
5. **技术限制**：如遇极端复杂内容，提供部分解析和进一步建议

## 输出内容
- Detailed explanation of each paper section (Abstract, Introduction, Methods, Results, Discussion, Conclusion)
- Step-by-step breakdown of figures and tables
- Simplified explanation of technical concepts
- List of potential questions and suggested answers
- Tips for effective presentation
- 论文各部分的详细解释（摘要、引言、方法、结果、讨论、结论）
- 图表的逐步解析
- 技术概念的简化解释
- 潜在问题清单及建议回答
- 有效汇报技巧

## 使用示例
**Input:**
"我是一名基础薄弱的博士生，这周组会要汇报这篇论文《Attention Is All You Need》，请帮我理解并准备汇报。"

**Output:**
1. 论文标题解析：《Attention Is All You Need》——注意力机制是构建强大模型的核心
2. 摘要解读：该论文提出了Transformer架构，彻底改变了NLP领域
3. 引言分析：传统序列模型的局限性，Transformer的创新点
4. 方法详解：注意力机制、编码器-解码器结构
5. 结果展示：在机器翻译任务上的性能超越传统模型
6. 图表解释：详细解读注意力热力图、模型架构图
7. 讨论与结论：Transformer的影响和未来方向
8. 潜在问题清单：
   - 导师可能问：Transformer与RNN相比有什么优势？
   - 同学可能问：注意力机制的计算复杂度是多少？
9. 汇报建议：重点突出创新点，简化技术细节

## 输出格式
1. **论文概览**：标题解析和核心贡献总结
2. **章节详解**：按顺序解析各章节（摘要→引言→方法→结果→讨论→结论）
3. **图表解析**：每个图表的详细说明和解读
4. **技术概念简化**：复杂术语的通俗解释
5. **潜在问题清单**：分类列出导师/同学可能的问题及建议回答
6. **汇报技巧**：针对该论文的具体汇报建议

## 依赖工具
1. **大语言模型**：用于理解和解析论文内容
2. **学术知识图谱**：用于验证和补充论文背景信息
3. **图表分析工具**：用于解释复杂图表和数据

## 不适用场景
- **非学术论文**：如新闻报道、博客文章、技术文档
- **过于简短的内容**：如会议摘要（少于3页）
- **非研究型论文**：如综述、评论、方法论介绍
- **非英文/中文论文**：需提供英文翻译
- **代码或实验数据**：单独的代码库或原始数据集

## 极端情况处理
1. **超长论文**：优先解析核心章节，提供重点内容摘要
2. **超复杂技术**：逐步分解，从基础概念开始解释
3. **跨学科内容**：补充必要的跨学科背景知识
4. **有争议的研究**：客观呈现不同观点，避免主观判断

## 验证清单
### 输出完整性
- [ ] 覆盖论文所有核心章节
- [ ] 解析所有关键图表
- [ ] 包含技术概念解释
- [ ] 提供潜在问题清单
- [ ] 包含汇报技巧

### 输出准确性
- [ ] 论文核心观点正确解读
- [ ] 方法描述准确无误
- [ ] 结果解读符合原文
- [ ] 技术概念解释准确
- [ ] 问题清单与论文相关

### 输出易用性
- [ ] 语言通俗易懂，适合基础薄弱学生
- [ ] 结构清晰，易于理解
- [ ] 重点突出，便于汇报
- [ ] 建议实用，可直接采纳

## 注意事项
- The paper content must be provided in full or with clear section divisions
- For optimal results, specify any prior knowledge gaps or specific areas of difficulty
- The skill focuses on helping understanding rather than creating the actual PPT slides
- 必须提供完整论文内容或清晰的章节划分
- 为获得最佳效果，请指定你的知识缺口或具体困难领域
- 该技能专注于帮助理解，而非直接创建PPT幻灯片