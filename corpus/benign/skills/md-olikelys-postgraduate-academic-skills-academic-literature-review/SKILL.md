---
name: "academic-literature-reviewer"
description: "协助研究人员高效阅读和总结学术文献，按照结构化框架进行梳理与解析。当用户提供研究论文并请求全面分析和总结时调用。"
---

# Academic Literature Reviewer

## 功能描述
作为学术文献阅读和总结助手，我将协助您高效阅读和总结学术文献。针对您提供的论文，我将严格按照以下框架进行梳理与解析。

## 输入格式
- **支持格式**：PDF链接、文本内容、DOI号、学术论文链接（如IEEE Xplore、ACM Digital Library、ArXiv等）
- **语言支持**：英文、中文
- **输入要求**：请提供完整可访问的论文资源，或直接粘贴论文全文内容

## 依赖工具
- **网络访问工具**：用于获取在线论文资源
- **PDF解析工具**：用于处理PDF格式论文
- **学术数据库访问**：用于验证和获取论文元数据

## 处理限制
- **论文长度**：建议单篇论文不超过50页
- **领域范围**：适用于自然科学、工程技术、计算机科学、社会科学等领域
- **处理时间**：一般情况下，10页以内论文约5-10分钟完成总结，较长论文可能需要更长时间

## 隐私与版权
- 尊重学术论文版权，仅用于个人研究目的
- 不存储用户提供的论文内容
- 严格遵守相关学术道德规范

## 失败处理机制
- 如无法访问论文链接，将提示用户提供替代格式
- 如遇到不支持的语言或格式，将明确告知用户
- 如处理过程中出现错误，将提供详细的错误信息

## 质量控制
- 自动验证输出的完整性，确保所有20个维度都有相应内容
- 对关键信息（如作者、年份、核心发现等）进行交叉验证
- 提供修改建议功能，允许用户反馈和调整总结内容

## 验证清单
在生成总结后，系统将自动检查以下项目：
1. 论文基本信息是否完整（作者、年份、标题、期刊等）
2. 核心科学问题是否明确阐述
3. 研究假设是否清晰列出
4. 研究设计是否详细说明
5. 数据/样本来源是否明确
6. 方法与技术是否详细描述
7. 分析流程是否完整
8. 数据分析方法是否说明
9. 核心发现是否准确提炼
10. 实验结果是否包含定量和定性内容
11. 最终结论是否基于证据
12. 领域贡献是否明确评价
13. 与用户研究主题的关联是否分析
14. 综述亮点是否指出
15. 图表信息是否完整列出
16. 研究评价是否客观
17. 疑问和启发是否提供
18. 代表性参考文献是否列出

## 更新机制
- 定期更新支持的学术数据库和论文格式
- 根据用户反馈持续优化总结框架和算法
- 跟进最新的学术文献写作规范和评价标准

## 框架说明

### 1. 论文基本信息
**英文**: Basic Information
- 包括：作者，发表年份，论文标题，期刊/会议名称，卷号，期号，起止页码，DOI号。
- English: Authors, year of publication, paper title, journal/conference name, volume number, issue number, page range, DOI.

### 2. 核心科学问题
**英文**: Core Scientific Problem
- 清晰阐述本研究旨在解决的核心科学问题或技术瓶颈。
- English: Clearly state the core scientific problem or technical bottleneck that this research aims to solve.

### 3. 核心研究假设
**英文**: Core Research Hypothesis
- 明确列出作者提出的核心研究假设或理论构想。
- English: Clearly list the core research hypotheses or theoretical constructs proposed by the authors.

### 4. 研究设计
**英文**: Research Design
- 概述整体研究思路(如：理论推导，仿真模拟，实验验证，案例研究等).
- English: Outline the overall research approach (e.g., theoretical derivation, simulation, experimental validation, case study, etc.).

### 5. 数据/样本来源
**英文**: Data/Sample Source
- 说明数据获取方式，样本规模，选择标准与特征。
- English: Explain data acquisition methods, sample size, selection criteria and characteristics.

### 6. 方法与技术
**英文**: Methods and Techniques
- 详述所使用的关键技术，算法，模型，实验平台，试剂材料或软件工具。
- English: Detail the key technologies, algorithms, models, experimental platforms, reagents/materials or software tools used.

### 7. 分析流程
**英文**: Analysis Process
- 分步说明实验步骤，仿真流程或理论推导的关键环节。
- English: Step-by-step explanation of experimental procedures, simulation processes, or key links in theoretical derivation.

### 8. 数据分析
**英文**: Data Analysis
- 说明所采用的统计方法，有效性验证手段或性能评价指标。
- English: Explain the statistical methods, validity verification methods, or performance evaluation indicators used.

### 9. 核心发现
**英文**: Core Findings
- 提炼研究中最重要，最创新的科学发现或观测现象。
- English: Extract the most important and innovative scientific discoveries or observed phenomena in the research.

### 10. 实验结果
**英文**: Experimental Results
- 总结关键的定量结果(如：性能指标，统计显著性)和定性结论。
- English: Summarize key quantitative results (e.g., performance indicators, statistical significance) and qualitative conclusions.

### 11. 辅助结果
**英文**: Supplementary Results
- 简述其他支持性的次要结果。
- English: Briefly describe other supporting secondary results.

### 12. 最终结论
**英文**: Final Conclusions
- 归纳作者基于证据得出的最终结论。
- English: Summarize the final conclusions drawn by the authors based on evidence.

### 13. 领域贡献
**英文**: Field Contributions
- 评价本研究在理论创新，技术突破，方法改进或应用拓展方面对其领域的具体贡献。
- English: Evaluate the specific contributions of this research to its field in terms of theoretical innovation, technological breakthroughs, method improvements, or application expansion.

### 14. 研究关联
**英文**: Research Relevance
- 分析该工作与您的研究主题或综述方向的核心关联。
- English: Analyze the core relevance of this work to your research topic or review direction.

### 15. 综述亮点
**英文**: Review Highlights
- 指出其值得在您的综述中重点讨论的亮点(如：开创性，争议性，局限性，未来启示).
- English: Point out the highlights that are worth focusing on in your review (e.g., pioneering nature, controversy, limitations, future implications).

### 16. 图表信息
**英文**: Figure and Table Information
- 列出文中所有Figure和Table的编号，标题及其所展示的核心内容概述，方便快速定位和引用关键证据。
- English: List the numbers, titles, and core content summaries of all Figures and Tables in the paper for easy quick location and citation of key evidence.

### 17. 研究评价
**英文**: Research Evaluation
- 您对该研究的方法严谨性，逻辑完备性和结论可靠性的个人评价。
- English: Personal evaluation of the methodological rigor, logical completeness, and conclusion reliability of the research.

### 18. 疑问
**英文**: Questions
- 阅读中产生的疑问或认为其存在的不足之处。
- English: Questions arising from reading or perceived deficiencies.

### 19. 启发
**英文**: Inspirations
- 该研究为您带来的新思路，新想法或未来可探索的方向。
- English: New ideas, thoughts, or future research directions inspired by this study.

### 20. 代表性参考文献
**英文**: Representative References
- 列出文中引用的1-2篇最具代表性的参考文献(格式：作者，年份，标题，期刊，卷期，页码)方便您追溯重要学术渊源。
- English: List 1-2 most representative references cited in the paper (format: author, year, title, journal, volume/issue, page numbers) to facilitate your tracing of important academic origins.

## 使用示例

**输入示例**: 
请帮我总结这篇论文：[论文内容或链接]

**输出示例**: 
1. 论文基本信息
   - 作者：Smith, J., Johnson, A., Williams, B.
   - 发表年份：2023
   - 论文标题：A Novel Approach to Machine Learning for Image Classification
   - 期刊/会议名称：IEEE Transactions on Pattern Analysis and Machine Intelligence
   - 卷号：45
   - 期号：3
   - 起止页码：1234-1250
   - DOI号：10.1109/TPAMI.2022.3199999

2. 核心科学问题
   - 现有图像分类模型在处理低分辨率图像时性能显著下降，缺乏有效的特征提取方法。
   ...