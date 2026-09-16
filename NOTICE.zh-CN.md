> [English](NOTICE) · 中文

# NOTICE

本仓库 `corpus/` 下由 basdotio 编写的内容依 MIT 授权（见 `LICENSE`）。

`corpus/` 下**从第三方 vendored 进来的**样本各自保留原许可，逐项列在下面。每个这样的样本都在它的标签里记录 `origin.license` 和 `origin.source`（标签是 `corpus/<class>/<surface>/<id>.yaml`，放在样本树**旁边**，绝不放进树里），其许可必须与此表一致。

当前 vendored 的第三方内容：

  （暂无。第 1 层目前只有 basdotio 自己编写的样本。）

关于强制执行的说明：标签与 NOTICE 的一致性校验**尚未实现**。今天 `make validate` 只检查 `origin.license` 是否属于第 1 层允许的宽松许可之一，它不读这个文件。在那项检查落地之前，让此表与标签保持同步是一项人工义务。这一点写在这里而不是略去，因为署名是 Apache-2.0 和 CC-BY-4.0 的一项条件，因此是许可证义务，不是记账。

---

## 不在这里的东西

`manifest/corpora.yaml` 引用的语料库**没有** vendored —— 那一层只记录 `url + commit + sha256`，内容由 `make fetch` 拉到被 gitignore 的 `cache/`。

这个区分有法律意义：分发别人的作品受其分发条款约束，而**记录一个 URL 和一个哈希不是分发**。所以第 2 层可以引用无 license、CC-BY-NC-SA、AGPL 的语料，在本地测量并发布聚合数字，全部处在这些语料分发条款的管辖之外。这些材料一律不允许进入第 1 层。

详见 [docs/licensing.zh-CN.md](docs/licensing.zh-CN.md)。
