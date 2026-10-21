# Changelog

## 1.1.0 - 2026-10-18

### 调整

- 技能重命名为 `zhong-portfolio-archetypes`，纳入 zhong- 系列
- 目录扁平化：`SKILL.md` 移到仓库根目录，站点数据移到 `assets/sites.json`
- 新增 `agents/openai.yaml`，支持 Codex 自动发现
- README 增加 Codex 与 Claude Code 两种安装方式

## 1.0.0 - 2026-10-18

### 新功能

- 首次开源发布：设计师 / 创意开发者个人网站风格原型库
- 从 RicoUI 清单的 180 个站点中实测抓取，174 个有效，人工归类为 11 种原型
- 每种原型给出版式骨架、字体、配色、动效、技术栈、反模式与代表站
- 选型决策表（含“安静但想被记住”等条件冲突处理）、案例详情页与 NDA 作品指南
- 参考站检索脚本 `find_refs.py`；数据抓取与构建工具 `tools/`；产品设计师求职示例
