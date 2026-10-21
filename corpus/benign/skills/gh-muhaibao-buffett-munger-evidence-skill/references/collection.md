# 收集、更新与检索

参考覆盖快照见 [coverage.md](coverage.md)。新采集一律暂存在 `<DATA>/staging/<批次名>/`，检查后再合并进资料库 `<DATA>/buffett-munger-library`（路径见 [local-library.md](local-library.md)）。新文档入库后：重建语义索引、运行 `qa.py build`，并用 `attribution.py propose` 判断是否需要更新归属表。下方历史采集说明保留原日期，不代表当前总数。

## 运行环境与数据

Python 3.9+，SQLite 需要 FTS5。基础 HTML、文本、JSON、VTT、SRT 导入使用标准库；PDF 需要 `pypdf` 或 `pdftotext`；`collect_speeches.py` 另外需要 `lxml`。网站即使忽略 `Accept-Encoding: identity` 返回 Brotli 压缩，也可用 Python `brotli` 或 Node 的内置 zlib 解码；无法解码就失败，不能把乱码入库。发布者原文自身的编码错误应保留质量说明，不凭猜测修正文句。

以下示例的 `PY`、`SKILL`、`LIB` 请替换为实际路径，参考 `local-library.md`。`STAGE` 指暂存目录 `<DATA>/staging/<批次名>`；这些名称是普通占位符，不是自动配置。

维护者的库在 2026-10-04 用下列采集器合并了：1994–2024 年 CNBC 年会文字稿 62 场、1995–2025 年报 31 份、1996 Q1–2026 Q2 季报 92 份，以及演讲、合伙企业信、样章和访谈材料。具体来源等级与缺口见 [source-map.md](source-map.md)。这些是文字资料覆盖，不表示视频文件已经收录或逐句核对。

### 初始股东信采集器

```sh
"$PY" "$SKILL/scripts/library.py" --library "$LIB" init
"$PY" "$SKILL/scripts/library.py" --library "$LIB" stats
"$PY" "$SKILL/scripts/collect.py" --library "$LIB" --kind buffett-letters --dry-run
"$PY" "$SKILL/scripts/collect.py" --library "$LIB" --kind buffett-letters
"$PY" "$SKILL/scripts/collect.py" --library "$LIB" --kind wesco-letters
"$PY" "$SKILL/scripts/collect.py" --library "$LIB" --kind reports --from-year 2023 --to-year 2025
```

上面的 `collect.py` 从实际索引链接发现材料，并**直接写入资料库**；默认跳过已索引 URL，`--refresh` 主动重新获取，`--from-year`、`--to-year`、`--limit` 限制范围。其 `reports` 类别仅用于年报；需要年报与季报批量暂存时使用下面的 `collect_financials.py`。巴菲特信件自动入口暂只纳入至 2024 财年，未来新信要先阅读署名后手动导入，不因网站更新自动改变作者。不要让这个直接写入采集器与其他合并／导入操作并发写同一库。

原文件在 `raw/`，SQLite 保存在库目录中，发现的索引及清单在 `discovery/`。索引中保留 SHA256 和访问时间。相同文档重新导入会更新当前检索片段并保留已有原文件；chunk ID 可能随正文和提取方式变化，因此引用时同时记录 URL、原文 SHA 和定位。它不是完整的多版本时态数据库。

### 批量扩展：先暂存，再由单一写入进程合并

新采集器只保存原件、段落、元数据和 manifest，不写共享 SQLite。不同来源可以在不同暂存子目录中并行获取；检查清单、归属、日期与缺口后，统一运行一次合并。下面的参数已与各脚本 `--help` 核对；各采集器参数并不通用。

```sh
"$PY" "$SKILL/scripts/collect_meetings.py" --output "$STAGE/meetings" --from-year 1994 --to-year 2026 --workers 3
"$PY" "$SKILL/scripts/collect_financials.py" --stage "$STAGE/financials" --library "$LIB" --from-year 1995 --to-year 2026 --kind all --workers 3
"$PY" "$SKILL/scripts/collect_speeches.py" --output "$STAGE/speeches"
```

- `collect_meetings.py`：从 CNBC 官方年会索引、年份页实际链接发现完整场次，提取普通 HTML 中的文字稿。支持 `--output`、`--from-year`、`--to-year`、`--workers`、可重复的 `--skip-url`、`--refresh`。默认复用已保存 HTML；`--refresh` 重抓。脚本默认不跳过场次，也不自动查询数据库。库里已经单独导入过某一场（如 2023 上午场）时，传入 `--skip-url <该场 URL>`，避免同场以不同文档 ID 重复入库；全新资料库不传该跳过项。维护者 2026-10-04 采集到 62 场；2025／2026 共 4 场正文缺口写入 manifest。
- `collect_financials.py`：从官方报告表格的年份行和季度／全年列发现真实链接，再解析实际子页面的报告链接。支持 `--stage`、可选 `--library`、`--from-year`、`--to-year`、`--kind all|annual|quarterly`、`--workers`；其中 `--library` **仅只读查重**。它复用内容哈希匹配的已完成暂存记录，目前没有 `--refresh` 或 `--dry-run` 参数；需要重新采集时使用新的暂存目录。已有报告会列为 `already_indexed`，不要重复计作新增。
- `collect_speeches.py`：仅支持 `--output` 和 `--refresh`；从已核验的 Stripe 公开 `/book` 页面提取十一篇主体，并将后加回顾、独立问答、编者材料分别暂存。原始 HTML 另存带 SHA 的快照。它不自动搜索其他演讲，不下载音视频。

**演讲采集器的首次准备**：输出目录必须先有 `chapter-links.json`。skill 内 `assets/chapter-links.json` 是 2026-10-04 核验过的发现记录，可复制到输出目录复用；网站结构变化或需要重新核验时，先打开出版社[公开封面](https://www.stripe.press/poor-charlies-almanack)，读取页面实际显示的十一篇章节链接和 `BERKSHIRE MODE` 全文链接；按章节顺序保存真实 URL，并记录访问日期和读取方式。本次 `/book` 是这样发现的公开全文页；`/book` 自身并未提供全部十一篇导航链接，不能据此批量猜 `talk-*` 地址。

发现记录的结构如下，其中 `chapter_urls` 必须替换为实际观察到的十一项，本例空数组不可直接用于采集：

```json
{
  "index_url": "https://www.stripe.press/poor-charlies-almanack",
  "book_url": "https://www.stripe.press/poor-charlies-almanack/book",
  "observed_on": "实际核验日期",
  "capture_method": "实际读取方式，例如渲染后可见链接",
  "chapter_urls": []
}
```

检查暂存结果后，使用**一个写入进程**合并所选清单；它们可以在同一个调用中依次处理：

```sh
"$PY" "$SKILL/scripts/merge_staged.py" --library "$LIB" --report "$STAGE/merge-report.json" \
  "$STAGE/meetings/manifest.json" \
  "$STAGE/financials/manifest.json" \
  "$STAGE/speeches/manifest.json" \
  "$STAGE/other/manifest.json" \
  "$STAGE/interviews/manifest.merge.json"
"$PY" "$SKILL/scripts/library.py" --library "$LIB" stats
```

只传实际存在并检查过的清单。`merge_staged.py` 的真实接口是必需的 `--library`、`--report` 和一个或多个位置参数 manifest；没有 `--dry-run`。标准 manifest 必须有 `documents` 数组，各项含 `metadata_path` 及 `source_path` 或 `json_path`；源文件和元数据须在该清单目录之内。本轮访谈原 `manifest.json` 使用 `ready/file/metadata` 格式，不能直接传入，应使用已转换的 `manifest.merge.json`。需要适配新清单时逐项核对路径和字段，不假设脚本会自动转换。

合并器按给定清单顺序校验、导入，匹配已有 ID、正文哈希及完整元数据时跳过。提供 `source_sha256` 或成对的 `raw_path`、`raw_sha256` 时会核验对应文件。清单原有缺口进入报告 `source_gaps`，导入错误进入 `failures`；进程返回成功不代表 `source_gaps` 为空。当前流程由操作者保证单一写入，不能声称脚本提供了跨进程写锁或并行写入调度。

本轮 `other` 与 `interviews` 是已人工核对并保存的暂存批次，统一合并支持它们，不等于已有通用的传记、Daily Journal 或全网访谈自动采集器。

## 导入其他资料

保存元数据为 JSON 文件，再执行：

```sh
"$PY" "$SKILL/scripts/library.py" --library "$LIB" fetch --metadata source.json
"$PY" "$SKILL/scripts/library.py" --library "$LIB" ingest --metadata source.json --file original.pdf
```

最小的真实材料元数据需要 `title` 和 `url`（本地材料可用稳定 `id` 代替 URL）。建议包含：

```json
{
  "title": "资料的真实标题",
  "url": "https://原发布者/真实页面",
  "author": "Warren Buffett",
  "speaker": "Warren Buffett",
  "date": "1996",
  "date_precision": "year",
  "publication_date": null,
  "source_type": "shareholder_letter",
  "primary_status": "primary",
  "transcript_quality": "official",
  "rights": "公开访问，版权保留，本地研究使用",
  "edition": null,
  "notes": "date 是报告财年；发表日期尚未核定"
}
```

上例为**字段模板，不是可直接采集的真实资料**。材料日期精度必须真实：知道年份就只写年份。`source_type` 常用 `shareholder_letter`、`annual_report`、`financial_report`、`annual_meeting`、`interview`、`speech`、`biography`；`primary_status` 取 `primary`／`secondary`／`unknown`；`transcript_quality` 取 `official`／`verified`／`edited`／`rough`／`unknown`。

元数据的“official”表示发布者提供的记录，不能保证每个词准确。原视频、发布者文字稿、机器字幕、参会笔记要分开。不要为了通过引用门槛把未验证资料改成 `verified`。

### 多人会议和采访

全文级 `speaker` 用 `mixed`。PDF 年报不设个人发言人。字幕若带 `<v Speaker>` 标签可保留；否则导入 JSON 分段，以实际发言标签标注：

```json
{"segments":[
  {"text":"实际抄录的提问文本", "speaker":"Questioner", "section":"实际章节标题", "start":"00:01:02.000"},
  {"text":"实际抄录的回答文本", "speaker":"Warren Buffett", "section":"实际章节标题", "start":"00:01:35.000"}
]}
```

`start`、`end` 只在原字幕／播放器提供时填写；未提供就省略。脚本不会识别声音或自动判断说话人，也不会下载视频。可导入用户合法提供的字幕，或在浏览器中读取发布者公开文字稿后保存为带来源的 JSON。网页是动态渲染时，先检查是否真正取得全文；普通 HTML 中只有播放器壳不能算已收集采访。

混合作者 PDF 如有已人工核定的页码范围，可在元数据中使用 `speaker_page_ranges: [{"from": 2, "to": 37, "speaker": "Warren Buffett"}]`；必须同时填写与当前原件一致的 `speaker_page_ranges_sha256` 和 `speaker_page_ranges_url`。文件变更或范围重叠会拒绝导入，必须重新核定。逐段显式发言人优先于页码规则。2014 年股东信 PDF 的第 38–42 页实际为芒格文章，采集器已对核验过的版本分别处理；第 1 页不归个人，第 2 页开头编者说明和正文内引文仍须人工核对。独立发布的芒格特别信与这部分内容重复，不计作独立佐证。

发布者文字稿未含时间戳时，用章节标题、段号、发言人和短锚定词定位，并注明暂无时间码。**有视频链接、视频标题或全文文字稿，都不能称已经收录视频文件或完成逐句音视频核对。** 文章可能混入相关报道、广告、编辑概括；只将实际问答标作本人发言。全文机转若未经核对用 `rough`，原句引用前核对音视频。

CNBC 三篇新增巴菲特访谈虽由原发布者刊登，因页面明确称 unofficial transcript，标 `primary / rough`；Acquired 芒格访谈发布者文字稿标 `primary / official`。Daily Journal 2017–2023 年七份 Worldly Partners 存档稿是第三方转录，全部为 `secondary / rough`。保留转录者、原 PDF 页码、删节与重复页处理说明；档案提供的录影链接仅供后续核验，不能转成未经核对的时间码。

### 传记、书籍、西科会议

传记默认 `secondary`；保存 ISBN／版次／页码，不自动复制付费全文。用户提供的合法电子书或 PDF 可本地导入，回答仍只摘录必要短句。本人引文应追到原始访谈或信件；只找到传记时写“据作者记述”。

目前《The Snowball》和《Damn Right!》仅有出版社公开样章，不能回答未读取章节或声称整本已收齐。独立署名的巴菲特前言可以单独标作本人文字。

Stripe 公开版《穷查理宝典》已拆为十一篇主体、十篇回顾和一组独立问答，共 22 份 `primary / edited`；十一份编者材料是 `secondary / edited`。第三篇为明确删节本，第八篇为 2000 年虚构寓言，第十一篇为 2005 年重写合成文章；修订与问答的日期未注明时保持未知，不继承原演讲日期。

Ivey 托管的合伙企业信汇编已拆为 29 条记录，1957–1970 年，保留实际 PDF 页段。其 `primary / rough` 表示本人原信的转录／重排副本；不是签名原件。保留年份标题和转录错误说明，精确引文要继续对照原件，不将“大学托管”提升为逐字可靠性的保证。

西科金融官方的芒格股东信是一手原作，但会议笔记不因记录者在现场就成为逐字稿。笔记用 `source_type: meeting_notes`、`primary_status: secondary`、`transcript_quality: rough`，记录笔记者及明确的整理声明。

## 检索命令

以下是无模型的基础关键词接口。日常混合检索、重排、Wiki 导航和索引检查见 [retrieval.md](retrieval.md)；采集器、入库元数据和原文定位保持本文件的约定。

```sh
"$PY" "$SKILL/scripts/library.py" --library "$LIB" search '能力圈' --speaker Buffett --limit 8
"$PY" "$SKILL/scripts/library.py" --library "$LIB" search 'incentives' --speaker Munger
"$PY" "$SKILL/scripts/library.py" --library "$LIB" search 'gold productive assets' --year-from 2010 --year-to 2013
"$PY" "$SKILL/scripts/library.py" --library "$LIB" show '实际返回的chunk_id' --context 2
"$PY" "$SKILL/scripts/library.py" --library "$LIB" export '实际返回的chunk_id' --context 2
```

`search` 是 FTS5 关键词检索，多个词按 OR 扩展；中文常见思想术语会扩展为英文短语，但任意中文问题不能保证有效召回。复杂问题人工拆成几次短查询，再阅读全文。命中排序不表示证据可靠度。`--primary-status`、`--source-type` 可筛选，但未知归属也应作为补充检查。

## 可恢复的失败

网络请求有有限重试；403、付费限制、空页面、PDF 扫描版无法提取等失败不算已索引。除 `stats` 的失败列表，还须查看各暂存 manifest 的 `failures` 和合并报告的 `source_gaps`。本轮 CNBC 2025、2026 年四场即属于普通 HTML 无可提取正文的缺口，不能计入 62 场成功文字稿。已有可用库记录不会因暂存采集失败删除。网络受运行环境限制时采用授权的网络工具或浏览器；不能声称本次已完成未实际读取的材料。

扫描 PDF 需要另做 OCR 并保留原页；`library.py` 不内置 OCR、语音识别、自动语义分段、向量检索或微调。独立的 `retrieve.py` 提供本地向量混合检索，不改变原文提取和证据资格。
