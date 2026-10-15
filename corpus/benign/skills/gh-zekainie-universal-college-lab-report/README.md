# 🎓 Universal-College-Lab-Report (大学通用实验报告生成器 Skill)

<div align="center">

![GitHub License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python Version](https://img.shields.io/badge/python-3.8%2B-brightgreen.svg)
![Agent Support](https://img.shields.io/badge/Agent-Antigravity%20%7C%20Claude%20%7C%20Cursor%20%7C%20Windsurf-orange.svg)
![Layout](https://img.shields.io/badge/Layout-B4%20Booklet%20%7C%20A4%20Standard-purple.svg)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-green.svg)

**告别 Word 排版崩溃，拯救每一个深夜调格式破防的理工科大学生！**  
**一键生成出版级大学实验报告、防悬空留白实体大框、高保真终端实测图与深度思考题解答。**

[快速上手](#-极速上手-30-秒跑通) • [核心黑科技](#-核心排版黑科技) • [模板规范](#-版面结构规范) • [Agent Skill 导入](#-ai-agent-skill-一键导入) • [百校共建](#-全国高校模板共建计划)

</div>

---

## 😫 你是否也经历过这样的 Word 折磨？

写实验报告 20 分钟，调 Word 格式 2 小时：
- ❌ **表格半截悬空**：双栏排版时表格只占上半截，下半截大片尴尬留白，怎么拖动都填不满；
- ❌ **分页跳栏崩溃**：多塞一行代码或一张图，后面所有栏位瞬间雪崩、错位跨页；
- ❌ **截图发虚发糊**：手机拍照或普通截图像素模糊、字符发毛，被老师批“态度不端正”；
- ❌ **代码排版丑陋**：直接复制进 Word 没有等宽字体、行间距炸裂、缩进混乱；
- ❌ **双面折页对不齐**：学校要求 B4 双面印刷中缝骑马钉装订，页码和正反面完全对不上。

---

## ✨ 为什么选择 Universal-College-Lab-Report？

本项目将严谨的 **OpenXML 底层排版几何算法** 与 **现代 AI Agent 架构** 深度结合，打造全自动、零错位、开箱即用的实验报告生成方案：

```
                    【你的讲义 / 代码 / 截图需求】
                                  │
                                  ▼
      ┌───────────────────────────────────────────────────────┐
      │       Universal-College-Lab-Report 排版引擎            │
      ├───────────────────────────┬───────────────────────────┤
      │ • 实体大框全高容器算法    │ • Pillow 纯代码终端高保真 │
      │ • 中缝折页独立页脚计算    │ • Consolas 灰底蓝条代码块  │
      │ • 微段落防粘连阻断控制    │ • 课后思考题深度题解逻辑  │
      └───────────────────────────┴───────────────────────────┘
                                  │
                                  ▼
              ┌───────────────────┴───────────────────┐
              ▼                                       ▼
       【.docx 源码格式】                       【无损印刷级 .pdf】
     （完全符合高校官方规范）                  （严格 3 物理张 / 6 页）
```

### 🌟 核心特性一览
1. **实体大框全高容器（Full-Height Container）**：
   独创 OpenXML 容器表格高度锁定算法（`<w:trHeight w:val="11200" w:hRule="atLeast"/>`），即使内容简短，外框也自动贯穿到底边距，彻底消除悬空留白，视觉沉稳大气。
2. **100% 锐利高保真终端截图渲染（Zero Blurriness）**：
   内置纯 Python (Pillow) 矢量级终端渲染引擎，一键生成 Cisco Packet Tracer 8.0、Windows CMD、PowerShell、Linux Bash 等窗口截图，文字边缘极致清晰，杜绝乱码。
3. **中缝折页独立页码系统**：
   完美契合高校工科 B4 横向双面印刷标准，左右栏独立精准生成 `第 1 页` 至 `第 6 页`。
4. **个人隐私 100% 安全（交互式主动提问）**：
   代码库中**零硬编码任何个人隐私**！首次使用时主动询问姓名、学号等信息，并在本地 `.labreport_config.json`（已加入 `.gitignore`）安全保存，绝不上传云端。
5. **本校开箱即用 + 全国高校通用**：
   内置对**四川轻化工大学（SUSE）**计算机与理工科官方规范的最佳实践，同时支持一键覆盖任意高校（清华、浙大、电子科大、大连理工等）名称与学院！

---

## 🚀 极速上手 (30 秒跑通)

### 1. 环境准备
确保已安装 Python 3.8+，然后安装轻量依赖：
```bash
git clone https://github.com/ZeKaiNie/universal-college-lab-report.git
cd universal-college-lab-report
pip install -r requirements.txt
```

### 2. 初始化你的学籍信息（仅需一次）
运行交互式向导，回答姓名、学号、学校等信息（保存在本地）：
```bash
python scripts/init_config.py
```
> 💡 *信息仅保存在你电脑的本地配置文件中，Git 不会提交，安全无忧！*

### 3. 一键生成示例实验报告
运行以下命令，即可生成完整的出版级 Word 与 PDF：
```bash
python scripts/builder.py --config templates/example_network_lab.json --out-docx output.docx --out-pdf output.pdf
```

### 4. 检查与验收
运行自动化质检脚本，校验页数（严格 3 张/6 页）并导出高清预览图：
```bash
python scripts/qa_inspector.py --pdf output.pdf --output-dir preview/
```

---

## 🤖 AI Agent Skill 一键导入

本仓库符合标准的 **Agent Skill 规范**，支持无缝接入你常用的任何 AI 编程与智能助手！

### 方式 A：Google Antigravity / Claude Desktop
1. 将本项目目录复制到你的 skills 目录：
   - Windows: `C:\Users\<你的用户名>\.gemini\config\skills\大学通用实验报告skill\`
2. 在对话框中直接对 AI 说：
   > “帮我写一份《操作系统》实验二 进程调度与互斥 的实验报告”
3. AI 将主动向你确认个人学籍信息，并严格按照 6 页黄金排版输出高质量报告！

### 方式 B：Cursor / Windsurf
将 `SKILL.md` 的内容添加到你项目的 `.cursorrules` 或全局 Rules 中，随时让 AI 依据本规则编译规范报告。

---

## 📑 版面结构规范 (标准 6 页布局)

| Sheet (物理纸张) | 栏位 / 页码 | 模块名称 | 内容规范 |
| :--- | :--- | :--- | :--- |
| **Sheet 1 (正面)** | **Page 1 (左栏)** | **表头与实验目的** | • 校名大标题 + 学院/课程/日期标头<br>• 8列标准信息表 + 所用仪器材料表 + 5点核心目的 |
| | **Page 2 (右栏)** | **实验原理** | • 系统体系结构与 PDU 交互机理<br>• 逐层封装分用机制与算法核心原理剖析 |
| **Sheet 2 (反面)** | **Page 3 (左栏)** | **实验过程 Part 1** | • 任务一：拓扑环境搭建与参数选型<br>• 居中实测高清大图 1（4.0~4.2 英寸）<br>• 任务二：核心仿真与排错分析 + 实测大图 2 |
| | **Page 4 (右栏)** | **实验过程 Part 2** | • 任务三：核心实测解剖与抓包分析<br>• 实测大图 3 与大图 4<br>• 协议/参数对比标准三线表 |
| **Sheet 3 (附录)** | **Page 5 (左栏)** | **附原始实验记录** | • 【原始记录一】节点参数/配置规划标准表<br>• 【原始记录二】核心代码/CLI 配置命令语法块（Consolas 灰底蓝条）<br>• 【原始记录三】控制台实测大图 5、6 |
| | **Page 6 (右栏)** | **思考题解答与总结** | • 【课后思考题全套深度题解】（标准 4 道题目，多角度综合技术论证）<br>• 【实验总结与反思】（理论与工程实践闭环） |

---

## 🛠️ 高保真终端截图渲染器 (`render_terminal.py`)

无需再忍受截图中乱码发虚的文字！使用内置脚本直接生成 100% 锐利的控制台图：

```bash
# 生成 Cisco Packet Tracer 控制台界面
python scripts/render_terminal.py --type cisco --title "PC0 - Command Prompt" --commands "ipconfig,ping 192.168.1.1" --output term.png

# 生成 Windows CMD 命令行界面
python scripts/render_terminal.py --type cmd --title "Windows 命令提示符" --commands "dir,netstat -an" --output cmd.png

# 生成 Linux Bash 终端界面
python scripts/render_terminal.py --type linux --title "ubuntu@suse: ~" --commands "ps -ef,gcc -o lab lab.c" --output linux.png
```

---

## 🤝 全国高校模板共建计划

无论你来自 **四川轻化工大学（SUSE）**，还是清华、北大、电子科技大学、华中科技大学、大连理工大学……  
如果你有本校的官方实验报告封面或特殊排版要求：

1. **Fork 本仓库**；
2. 在 `templates/` 下新建你学校命名的配置（如 `example_uestc_lab.json`）；
3. 提交 Pull Request！

让我们一起把中国大学生的实验报告排版工具做到极致！💪

---

## 📜 开源协议

本项目采用 [MIT 许可证](LICENSE)。你可以自由使用、修改和分发，但请保留原作者版权声明。

如果这个项目帮到了你或你的室友，请随手点一个 **⭐ Star** 支持一下！
