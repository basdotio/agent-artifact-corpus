# 踩坑记录（editor_sdk 通道 + 脚注处理）

全部在一次完整的投稿排版任务中实测踩过并解决。build_paper.py / postprocess.py 的代码已内置对应修复，此处记录原因，便于排查与迁移到其他工具链时避坑。

## editor_sdk（edsdk.py）的五个坑

1. **脚注编号格式工具不暴露**：①编号 + 每页重排只能保存后改 XML——sectPr 里写 `<w:footnotePr><w:numFmt w:val="decimalEnclosedCircle"/><w:numRestart w:val="eachPage"/></w:footnotePr>`（postprocess 第 3 步）。
2. **`doc_insert_footnote` 的 idx 是"插到该字符之前"**，且占位符会被脚注结构切成两段导致 `doc_find` 后续匹配不到（find 不跨结构边界）。解法：先 `doc_find_and_set(delete)` 删占位符，再在 token 原 begin 处插脚注。
3. **`doc_set_document_style` 的对齐映射有 bug**：jc 传 both/justify 都写成 `w:val="end"`（右对齐）。必须 XML 后处理改回 both（postprocess 第 1 步）。
4. **插入的正文 run 被显式写入 `rFonts ascii/hAnsi=SimSun`**，覆盖 docDefaults 的 Times New Roman，西文会变宋体。后处理把这两个槽换成 Times New Roman，eastAsia 保持宋体（postprocess 第 2 步）。标题/楷体的 run 自带全槽字体，不受影响。
5. **`doc_set_page_number` 必须传 `section_index`**，不传直接报错。

## 脚注 XML 的两个坑

6. **脚注 id 要从 2 开始**：Word 惯例 id=-1/0 留给 separator/continuationSeparator，必须补这两个条目，真实脚注 id 顺延 +2（document.xml 的引用和 footnotes.xml 的条目要同步改）。
7. **重建 footnotes.xml 必须整体生成**，不能逐条 regex 替换——id 顺延后新旧 id 碰撞，会互相覆盖（实测覆盖错过多条内容，逐条抽验"编号-内容"对应才发现）。

## 其他实测经验

8. `create_doc` / `save_file` 返回纯文本不是 JSON，解析要兼容（`file_id=` 正则 / "saved to"）。
9. `--json` 传含反斜杠的 Windows 路径会被 bash 吞转义，一律用 `--json-file` + 正斜杠路径。
10. 脚注文本 run SDK 默认给 Arial + sz18，字号恰好是小五但字体要换；`doc_insert_footnote` 的 content 只收纯文本，斜体只能后处理按登记的子串切 run。
11. 交付后用户可能在编辑器里改文档（删重复脚注、改页码、改措辞）——每轮问答前先重扒 docx 核对当前状态，别拿交付时的快照答话。
12. `doc_get_outline` 对不用 Heading 样式的文档返回空——本流程的标题是 Normal 段+显式字体，大纲为空是预期，验证用 XML 解包。
13. **后处理必须幂等**：脚注 id 顺延与 footnotes.xml 重建只能按"首次运行"做一次；postprocess.py 已加 separator 检测跳过重复重建。任何绕过脚本的手动 XML 编辑后再跑后处理，先确认文档状态。
14. **spec 不允许孤儿脚注**：build 只插入被引用的占位符，postprocess 按 spec 全量重建；两者基数必须一致，否则编号-内容整体错位。build 与 postprocess 均有断言拦截，看到断言消息先修 spec，不要手工改文档绕过。

## 验证

`scripts/verify_docx.py <docx> --spec <spec.json>` 固化了全部可机械判定项（zip、脚注标记与条目一一对应、id 从 2 开始、separator/①编号/每页重排、docDefaults 两端对齐+firstLineChars=200+TNR/宋体、无 SimSun 西文、脚注小五无 Arial、标题黑体居中无缩进、页脚 PAGE、无残留占位符、脚注数量/编号-内容/斜体数与 spec 一致）。退出码非 0 逐项修完再交付；之后再用 editor_sdk 全新 `open_file` 确认 XML 可解析。
