> [English](licensing.md) · 中文

# 许可

两个问题，把它们混为一谈是常见的错误：

1. **我们可以重新分发它吗？** —— 管的是第 1 层（`corpus/`），那一层是 vendored（随仓库分发）的。
2. **我们可以拿它来测量并发布聚合数字吗？** —— 管的是第 2 层（`manifest/`），那一层不是。

**第二个问题对这里的一切东西答案都是「可以」。** 在你合法获得的材料上本地跑一个工具，并发布计数和比率，既不是分发，也不构成演绎作品。这就是第 2 层存在的原因，也是它只放 URL 和哈希的原因。

| 类别 | 语料库 | vendor 进第 1 层 | 第 2 层 |
|---|---|---|---|
| **无许可证** | trailofbits、snyk-labs、MalSkillBench、MCPTox、zast-ai | ❌ **零授权** | ✅ |
| **NC / SA** | SkillTrustBench（CC-BY-NC-SA）、obaydata（NC）、awesome-claude-code（NC-ND） | ❌ ShareAlike 传染，NonCommercial 门槛 | ✅ |
| **Copyleft** | OWASP Benchmark（GPL）、TruffleHog（AGPL）、thedotmack（AGPL） | ❌ copyleft 条款会波及语料仓库本身 | ✅ |
| **专有** | `anthropics/skills` —— 每个 skill 的 LICENSE.txt 写着 All rights reserved，禁止 Reproduce 和 Distribute | ❌ **硬红线** | ✅ |
| **宽松** | DataDog、SkillMD-138K、clawhub-security-signals、skillsgoat、skillcraft-audit、guarddog、package-analysis、NVIDIA、cisco、automatelab、各厂商仓库 | ✅ | ✅ |

**在重新分发这件事上，无许可证比 NC/SA 更严格** —— 零授权对比有条件的授权 —— **但在测量这件事上两者完全相同。** 两者都待在第 2 层。

## 为什么这份语料是独立的仓库

第 1 层把我们自己写的 MIT 材料和宽松许可的第三方样本混在一起，因此它背负着 Apache-2.0 和 CC-BY-4.0 的义务。一个扫描器如果把这份语料 vendor 进自己的树，就得让整个仓库继承这些义务 —— 而为了被 benchmark 一下就付这个代价，任何扫描器都不该被要求。

把语料保持独立，意味着扫描器依赖它的方式和依赖任何测试 fixture 一样：按引用、钉在某个 commit 上、各自的许可证原封不动。等到有好几个扫描器在这里被测量时，这一点会更要紧，因为它们的许可证不会一致。

同样的推理也是为什么任何 AGPL 或 NonCommercial 的语料，不论体量多小，都不许进入第 1 层。Copyleft 会波及到 vendor 它的那个仓库，而这个仓库的存在意义就是能被任何人 vendor。

## 署名

每一个 vendored 的样本都在它的标签里记录 `origin.license` 和 `origin.source`，并出现在 `NOTICE` 中。署名是 Apache-2.0 和 CC-BY-4.0 的一项条件，所以这是许可证义务，不是记账。

**标签与 `NOTICE` 的交叉校验尚未实现。** `make validate` 检查的是 `origin.license` 是否属于第 1 层允许的许可之一；它不读 `NOTICE`。在那项检查落地之前，让两者保持同步是人工的，这一点写在这里和 `NOTICE` 里，而不是被说成自动的。

## 这里没有覆盖的一件事

恶意样本是真实的攻击载荷。在上述许可证下重新分发是合法的，但它终究是放在公开仓库里的恶意代码。

第 1 层用三种方式缓解：能用重建就用最小化的重建而不是原始载荷；我们自己写的样本里没有任何活的网络目标（只用 RFC-2606 保留名称，而在把这一点当作标签依据之前，请先读 `design.zh-CN.md` 里的捷径特征陷阱）；每一个可执行形态的样本都带有标记它的标签。

我们**不**提供 DataDog 所做的那种无害化处理 —— 他们的样本用密码 `infected` 做了 zip 加密，这正是它们留在第 2 层、而不是被解包进第 1 层的原因。
