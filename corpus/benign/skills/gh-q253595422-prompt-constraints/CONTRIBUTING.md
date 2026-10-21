# 贡献指南（Contributing）

感谢你愿意改进 Prompt Constraints。这是一个**纯 Markdown 的 Agent Skill**——没有构建、
没有依赖、没有测试框架，所有价值都在文字里。因此贡献门槛低，但**写作标准高**。

---

## 一、核心心态

这个项目的立身之本是「约束的清晰度」。

> 加一句模糊的形容词，不如改对一条约束。

任何让文档变更长、但没有变更准确的改动，都会被拒。**宁缺毋滥**是本项目的默认审稿标准。

---

## 二、可以贡献什么

| 类型 | 说明 | 改哪个文件 |
|---|---|---|
| 🐛 事实纠错 | 模型能力、参数上限、官方 schema 写错了 | `references/models.md` 对应行 |
| ✨ 新增模型 | 补充一个生图/视频模型的适配规则 | `references/models.md`（必要时新建独立文件） |
| 📚 词条扩充 | 补充精准的中英对照视觉词汇 | `references/vocab.md` |
| 🚫 排除项补充 | 补充某类任务的真实失败模式 | `references/negative.md` |
| 🧩 模板改进 | 修正模板的不可用之处 | `references/templates.md` |
| 📐 方法论修正 | 六层约束模型有逻辑漏洞 | `references/constraints-core.md` |
| 📝 示例补充 | 提供经过实测的高质量示例 | `examples/` |
| 🌐 翻译 | 英文版文档 | 见第六节 |

---

## 三、写作约束（**必须遵守**）

这些不是风格偏好，是这个 skill 赖以生效的规则。**违反的 PR 不会被合并。**

1. **不许写抽象形容词。** 「高级感 / 电影感 / 氛围感」出现时必须配具体视觉元素解释。
2. **不许写「no X」式否定。** 排除项一律写成包含排除结果的场景描述。
3. **不许把参数写进提示词正文。** 模型名、版本、时长、比例、分辨率一律外置。
4. **术语保留英文原名。** FPV、one-shot、prompt、Seedance、Nano Banana 等不翻译。
5. **中文优先，结构清晰。** 表格用于对照，代码块用于可直接复制的内容。
6. **不要发明 API / 字段 / 参数。** 拿不准的写「以官方文档为准」，不要编。
7. **不引用受版权保护的书籍原文。** 转述，并注明思路来源。

---

## 四、改动流程

```bash
# 1. Fork 并克隆
git clone https://github.com/<your-name>/prompt-constraints.git
cd prompt-constraints

# 2. 建分支（分支名用 type/简短描述）
git checkout -b feat/add-kling-reference

# 3. 改完自检（见下节）

# 4. 提交
git commit -m "feat(models): 补充可灵 Kling 的首尾帧约束"

# 5. 推送并发起 PR
git push origin feat/add-kling-reference
```

### 提交信息规范

采用 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <描述>

type:  feat | fix | docs | refactor | chore
scope: models | vocab | negative | templates | core | image | video | consistency
```

示例：
- `feat(models): 补充 LTX-2.5 的 screenplay 格式约束`
- `fix(vocab): 修正「体量感」的英文对照`
- `docs(examples): 新增竖版海报示例`

---

## 五、提交前自检清单

- [ ] 改了 `references/` 下的文件名或路径 → **同步更新 `SKILL.md` 的加载表与路由表**
- [ ] 新增了引用 → 确认目标文件真实存在，无断链
- [ ] 新增了词条/模型 → 是否有官方依据？无依据的已标注「经验性归纳」
- [ ] 内容是否符合第三节的 7 条写作约束
- [ ] 改动是否让文档变长了但没变准？如果是，考虑删掉
- [ ] 是否包含个人信息（真实姓名、邮箱、本机路径、令牌）→ 有则移除

---

## 六、新增一个模型的完整步骤

以新增「某视频模型 XYZ」为例：

1. 在 `references/models.md` 的**视频模型表**加一行：提示词形态 / 偏好 / 避坑。
2. 若该模型的提示词结构复杂（有官方 schema、特殊字段、多模式），在
   `references/video.md` 补一节，或在 `references/models.md` 内单独展开。
3. 若它会带来新的**通用**失败模式 → 补进 `references/negative.md` 的视频专属池。
4. 若它有独特的运镜/术语 → 补进 `references/vocab.md` 的视频动词表。
5. 更新 `SKILL.md` 路由表的模型关键词。
6. 在 `CHANGELOG.md` 的 `[Unreleased]` 段加一行。

**注意**：能力边界（时长上限、参考资产数量、分辨率）必须注明来源或明确标注为经验性归纳。
写错参数比不写更糟。

---

## 七、翻译

欢迎英文版。约定：

- 英文版放 `README.en.md`，`references/` 暂不强制翻译。
- 翻译是**重写**不是直译：英文提示词的惯用表达与中文不同。
- 术语表（`references/vocab.md`）本身就是中英对照，可直接复用。

---

## 八、行为准则

参与本项目即表示同意遵守 [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/)。

简单来说：**对事不对人。** 技术分歧用证据讨论，不要人身攻击、不要贬低他人审美或水平。

---

## 九、License

本项目采用 [MIT License](LICENSE)。
**提交 PR 即表示你同意以 MIT 协议授权你的贡献。**
