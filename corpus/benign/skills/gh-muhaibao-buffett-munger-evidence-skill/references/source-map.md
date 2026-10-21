# 巴菲特与芒格资料来源地图

核验日期：2026-10-07 起，各轮另注日期。下面列维护者核验过的来源入口和各轮新增来源。**入口存在不代表全文已入库**；你自己的库以本地 `stats`、文档元数据及合并报告为准，参考覆盖快照见 [coverage.md](coverage.md)。网页可读、浏览器可读与程序可下载是不同状态。

采集缺口与合并报告 `source_gaps` 一起检查。Colossus 原 HTML 仅主持人导言，全文未取得。历史年报与拆出的信共享原件，引用时按 `parent_document_id` 和原页去重。

## 第三轮新增来源（2026-10-07）

- CNBC三个旧缺口：2016-02-29和2012-10-24取自[RBCPA档案](https://www.rbcpa.com/warren-e-buffett/)中的CNBC全文PDF镜像；2013-05-06取自[CNBC原PDF](https://fm.cnbc.com/applications/cnbc.com/resources/editorialfiles/2013/05/08/2013-05-06%20Warren%20Buffett%20Squawk%20Box%20Transcript_0.pdf)。PDF文件页码可核查，发布者粗稿未逐句核原声。
- [2026-03-31 CNBC原发布者稿](https://pressroom.versantmedia.com/cnbc/press-releases/cnbc-exclusive-transcript-berkshire-hathaway-chairman-warren-buffett-speaks)已入库，标unofficial/rough。另补2008–2014若干目录外CNBC文字，本轮CNBC合计15份；目录外节目不冒充固定31项的缺口关闭。
- [哥伦比亚《The Superinvestors of Graham-and-Doddsville》](https://business.columbia.edu/insights/chazen-global-insights/superinvestors-graham-and-doddsville)原发布页正文已取得并索引；原PDF镜像辅助核验。表格与文中第三方引文单独保留，不归为巴菲特口述。
- 2026-10-09 第四轮：同一 Worldly 档案中 10 份此前未入库的芒格文字（评论文章、1989 退会信、1984 书面陈述、2019 WSJ 访谈）已入库，系列名 `munger-writings-worldly`。档案中 1995 年《人类误判心理学》PDF 仍按上轮判断不入库（后期扩写版本）。
- [Worldly档案](https://worldlypartners.com/charlie-munger-archive/)的2007 USC、2017 Michigan Ross、2020 Caltech、2022 Singleton四份第三方转录已入库，均secondary/rough。Singleton缺逐段人名而保持未归属；Michigan只核定年份。不能以档案网页标题代替正文核验。
- 档案标成1995心理学的PDF经原页核验是后期扩写版，未重复入库；标作Redlands2020的链接实际指向Caltech。保留排除记录和日期差异。2010-01-20采访已有原CNBC版，不重复导入镜像。

## 第五轮新增来源（2026-10-09 至 10-10）

- **CNBC 巴菲特档案页的转录核查方法**：页面内嵌 JSON 的 `chapters[].transcript` 数组有内容才算有发布者文字。2024 年会 56 个章节都有转录；2025 年会章节为空，2026 年会没有章节；待补的 13 项 CNBC 访谈和芒格 2023 原始访谈的章节转录也都为空。内置浏览器访问该站返回 Access Denied，用普通请求读取。
- [cnbc.com 原发布的访谈全文](https://www.cnbc.com/2017/05/09/full-transcript-billionaire-investor-warren-buffett-speaks-with-cnbc-percent-u2019s-becky-quick-on-percent-u201csquawk-box-percent-u201d.html)：2008-05-05、2012-05-07、2015-03-25、2017-05-08、2018-08-30、2019-05-03 为全文，2026-07-15 为摘录。CNBC 自称 unofficial transcript，标 `primary / rough`。2012-11-28 的 cnbc.com 页面已无正文，改用转载。
- [rbcpa.com 巴菲特资料页](https://www.rbcpa.com/warren-e-buffett/)：转载的 2008–2012 年访谈、报刊文章、1991 圣母大学和 1998 佛罗里达大学讲座稿、1975 养老金备忘录扫描件、FCIC 访谈整理稿、学生问答笔记。全部按转载镜像处理；与库内已有同日 CNBC 原发布稿重复的三份未入库。
- [Finanzapedia 年会全文](https://finanzapedia.com/en/warren-buffett/annual-meetings/2025-berkshire-hathaway-annual-meeting)：2025、2026 年会第三方全文，`secondary / rough`。页面把全文重复了一遍，只取第一份；2026 稿按发言人重排。其他可比对版本：steadycompounding.com、good-investing.net（2026 只到约 2:02:20）、gscm.co。
- [Fortune 官网的 2003 贸易逆差文章](https://fortune.com/article/warren-buffett-foreign-trade/)、[捐赠誓言网站的巴菲特誓言信](https://givingpledge.org/pledge/warren-buffett/)：发布者自己的页面。
- 不可用：nytimes.com 拒绝自动访问，内置浏览器也按安全策略禁止，因此没有合法转载的 NYT 文章仍列为缺口；Scribd 扫描件来源与版权不明，不采用。

## 用户自行导入的译本

- 中文版《穷查理宝典》《滚雪球》《芒格之道》等受版权保护的书**不随本技能分发**。持有合法副本的用户可以自行解包、按章节切分后导入，元数据设 `source_type: translation`（默认不参与检索），本人话语的章节可在归属表中以 `translation-of-own-words` 归属，并用 `translation_of` 指向库内英文原文。

## 第六轮新增来源（2026-10-11）

- [GitHub zhengxixuan/CharlieMungerTalk](https://github.com/zhengxixuan/CharlieMungerTalk)：无许可证声明的公开仓库。只导入 2010 哈佛西湖演讲稿（Santangel's Review 转录）和 2011 Motley Fool 年会笔记；其余与库内材料重复，或是同一份中信译文，未导入。

## 优先收集的一手来源

| 优先级 | 来源与核验范围 | 证据性质和使用限制 |
|---|---|---|
| P0 | [伯克希尔：巴菲特股东信目录](https://www.berkshirehathaway.com/letters/letters.html)，页面列出 1977–2024 年逐年链接 | 本人署名原文。目录另外介绍收录 1965–2024 年信件的付费书，不等于网站已免费提供 1965–1976 年全文。信件年度通常是所述财政年度，须另存签署日期。 |
| P0 | [年度及中期报告](https://www.berkshirehathaway.com/reports.html)，已入库年报 1995–2025、季报 1996 Q1–2026 Q2；[2024 年报原 PDF](https://www.berkshirehathaway.com/2024ar/2024ar.pdf) 共 150 个 PDF 页面 | 公司一手财务披露。按官方表格行列识别年度和季度；股东信、管理层讨论、财表、审计意见分别标注作者或责任主体。财表数字不是巴菲特或芒格个人观点；PDF 页码与印刷页码须分开保存。 |
| P0 | [伯克希尔发布的 Wesco 芒格信件目录](https://www.berkshirehathaway.com/wesco/WescoHome.html)，当前页面列出 1997–2009 年 | 芒格本人署名书面材料；这是信件目录，不是西科年会讲话全集。缺少年份应列缺口，不得按规则猜 URL 后声称已收录。 |
| P0 | [巴菲特和芒格五十周年特别信](https://www.berkshirehathaway.com/SpecialLetters/WEBCTMLtr.html) | 两位分别署名，两篇分别入库，不能混作同一作者。 |
| P1 | [CNBC 年会档案](https://buffett.cnbc.com/annual-meetings/)与[档案说明](https://buffett.cnbc.com/warren-buffett-archive/) | 已保存并索引 1994–2024 年 62 场的发布者文字稿；2025–2026 年 4 场当前普通 HTML 无可提取正文，原因可能是只有播放器或版式变化，不能断言原视频不存在。章节为编者标题；无视频时间码。2024 年起不得默认芒格参加，合成声音也不能当作本人发言。 |
| P1 | [CNBC 2023 年会上午场](https://buffett.cnbc.com/video/2023/05/08/morning-session---2023-meeting.html)，可见时长 02:44:49、章节和发言者标注 | 浏览器已核验有正文。事件日期为 [2023-05-06](https://buffett.cnbc.com/2023-berkshire-hathaway-annual-meeting/)，网页发布为 2023-05-08。除两位之外还有 Greg Abel、Ajit Jain、Becky Quick 与提问者。章节 10 涉及 AI；章节 24 涉及苹果和分散投资。不能把问题中的判断当作受访者答案。 |
| P1 | [CNBC 完整采访目录](https://buffett.cnbc.com/cnbc-interviews/) | 采访者原发布渠道的一手音视频。并非每个视频页都显示文字稿；逐页确认。部分 web 读取返回 403，而正常浏览器可读，不能把错误页入库。 |
| P1 | CNBC 巴菲特 [2019-02-25](https://www.cnbc.com/2019/02/25/full-transcript-billionaire-investor-warren-buffett-speaks-with-cnbcs-becky-quick-on-squawk-box-today.html)、[2020-02-24](https://www.cnbc.com/2020/02/24/full-transcript-billionaire-investor-warren-buffett-speaks-with-cnbcs-becky-quick-on-squawk-box-today.html)、[2023-04-12](https://www.cnbc.com/2023/04/12/full-transcript-berkshire-hathaway-chairman-ceo-warren-buffett-speaks-with-cnbcs-becky-quick-on-squawk-box-today-.html)长访谈 | 三篇正文已入库。发布者明确标为 unofficial transcript，故为 `primary / rough`；提问者与巴菲特分开，源稿存在疑似发言标签错误的段落保持未核定。 |
| P1 | [芒格最后一次 CNBC 采访文字稿](https://www.cnbc.com/2023/11/30/full-transcript-from-cnbcs-charlie-munger-a-life-of-wit-and-wisdom-.html)与[扩展版视频](https://buffett.cnbc.com/video/2023/12/05/charlie-mungers-final-cnbc-interview.html) | 两页均经浏览器核验。录制日期 2023-11-14；文字稿对应 2023-11-30 播出的特别节目；扩展视频显示 01:44:37。**文字稿与扩展视频不是已核对的一一对应版本**，不能直接移植时间码。分段区分 Munger 与 Quick。 |
| P1 | [CNBC 原频道：2023 Daily Journal 股东大会](https://www.youtube.com/watch?v=9VVPO3KWj3A) | 已核验发布者为 CNBC Television，发布日期 2023-02-15。这是原始录制来源；字幕如来自 YouTube 自动生成，须另标 ASR，不能称人工校对官方逐字稿。其他年份逐场核验来源与完整性。 |
| P1 | [Stripe Press 免费交互版《穷查理宝典》](https://www.stripe.press/poor-charlies-almanack)、其实际链接的 [Berkshire Mode 全文页](https://www.stripe.press/poor-charlies-almanack/book)及[PCA 原出版方入口](https://www.poorcharliesalmanack.com/) | 已从全文页提取十一篇主体及后续材料，保存原始 HTML 和章节链接。本人文字标一手编辑本，编辑材料单独标二手；具体篇目的删节与改写不能忽略。 |
| P1 | [Acquired 对芒格的原始采访](https://www.acquired.fm/episodes/charlie-munger)，发布日期 2023-10-30 | 原发布者全文文字稿已入库，`primary / official`；具体录制日期未核定，不能以发布日期替代。主持人开场、赞助和结束语归主持人，不归芒格；没有经验证的视频时间码。 |
| P2 | [Worldly Partners 芒格档案](https://worldlypartners.com/charlie-munger-archive/)保存的 Daily Journal 2013–2023 年会文字版本 | 十一份均为 `secondary / rough`；2013开头截断、2015为报道集。2018 稿有删节说明；2021 原 PDF 后半重复前半，保留原件但只索引一次；2022 稿说明问题可能概括。发言人标签属于转录者判断，不能当成已验证原声。 |
| P2 | [Ivey 托管的 Buffett Partnership Letters 汇编](https://www.ivey.uwo.ca/media/2975913/buffett-partnership-letters.pdf) | 已按信件边界和原 PDF 页段拆为 29 条记录。属于本人信件的转录／重排副本，`primary / rough`，不是签名影印件；年份标题和转录错误原样保存，精确引文需继续查原件。 |
| P2 | [USC 主办方关于 2007 毕业演讲的报道](https://gould.usc.edu/news/300-graduate-from-usc-law/) | 主办方对事件日期与部分原话的直接报道，**不是完整演讲逐字稿**。核验日期为 2007-05-13。完整版须追溯主办方录音或授权出版文本。 |
| P2 | [SEC 伯克希尔档案入口](https://www.sec.gov/edgar/browse/?CIK=1067983&owner=exclude) | 用于核对原申报、修订、报告期和申报日期。CIK 1067983 经 [SEC 公司记录](https://www.edgarcompany.sec.gov/servlet/CompanyDBSearch?cik=0001067983&main_back=2&page=detailed)核验。动态页面空壳出现 “No Filings” 不代表公司没有申报。 |

新增历史源：[The Oracle’s Classroom 年报档案](https://theoraclesclassroom.com/archives/)的1965–1994共30个实际PDF链接已保存，来源是原公司报告的第三方镜像。原件未改，逐页OCR为rough；1974旋转、1975乱序重复、1981第3页漏识需要专门处理，OCR 不在本技能脚本内。Worldly的1983–1996西科信和1977–1982 Blue Chip联署信也已入库，不能误归公司或唯一作者。

## 初始库中的原文定位样本

1. [巴菲特 1996 股东信 HTML](https://www.berkshirehathaway.com/letters/1996.html)：页面正文可抽取，适合验证书面原文检索和能力圈问题。
2. [芒格 2014 五十周年特别信 PDF](https://www.berkshirehathaway.com/SpecialLetters/CTM%20past%20present%20future%202014.pdf)：5 个 PDF 页面，伯克希尔发布的芒格本人论述。
3. [芒格 Wesco 2009 股东信 PDF](https://www.berkshirehathaway.com/wesco/cm2009.pdf)：7 个 PDF 页面，涉及具体业务、浮存金与内在价值；不能将全文每个财务事实泛化为投资格言。

上表 **CNBC 2023-11-30 芒格专访文字稿**也已入库。它是电视特别节目的文字版本，不能据此声称已取得之后发布的扩展视频逐字稿。

## 演讲和版本归属陷阱

- [Talk One](https://www.stripe.press/poor-charlies-almanack/talk-one)是 **1986-06-13 洛杉矶 Harvard School 毕业演讲**，该校后来成为 Harvard-Westlake；不是哈佛大学。该出版页对场合有明确说明。
- [Talk Two](https://www.stripe.press/poor-charlies-almanack/talk-two)包含 1994 年演讲、后来修订的补记与问答。不能把所有段落统一标为 1994 年现场讲话。
- [Talk Three](https://www.stripe.press/poor-charlies-almanack/talk-three)是 1996 年演讲的编辑删节本，原页明确说明缩减重复内容并插入概括；这些概括未归为芒格发言。
- [Talk Four](https://www.stripe.press/poor-charlies-almanack/talk-four)包含芒格对早期演讲表达失败的后记，适合辨认观点的修订；页内编辑说明不能都归给芒格。
- [Talk Eight](https://www.stripe.press/poor-charlies-almanack/talk-eight)写于 **2000 年夏天**，是明确标注的虚构寓言；标题中的 2003 年不能当作事件或写作日期，Quant Tech 不能当作真实历史公司。
- [Talk Eleven](https://www.stripe.press/poor-charlies-almanack/talk-eleven)是芒格 **2005 年**重写的合成作品，材料来自 1992、1994、1995 年三次演讲，出版方明确说这个完整版本从未讲过。后附 Revisited 又提到“2000 年”，这处版本不一致保留说明，不擅自修正。
- 十份 Revisited 和 Talk Two 独立问答均单独建档。只有明确的修订日期才赋值，未注明日期的材料保持未知，不能继承前面原演讲的日期。
- 单篇 Stripe 页面普通下载可能只有动态壳；本次正文来自公开链接的 `/book`。采集器需要实际发现的 `chapter-links.json`，不能把空页面或猜测的章节 URL 当作全文。
- [2025 年度股东信](https://www.berkshirehathaway.com/letters/2025ltr.pdf)落款 **Gregory E. Abel，2026-02-28**。官方域名、路径 `letters/`、文中频繁提及 Warren，都不足以把作者认定为巴菲特。
- 巴菲特的材料不限年度股东信：[2025-11-10 官方新闻稿及个人信](https://www.berkshirehathaway.com/news/nov1025.pdf)是不同文类。公司新闻说明与嵌入的本人信应分别划分。

## 西科讲话与传记：保留价值，准确降级

西科会议现场笔记可以弥补原始录像缺口，但不是“芒格官方逐字稿”。[Whitney Tilson 的 2005 西科会议笔记](https://www.rbcpa.com/wp-content/uploads/2017/01/Tilson_Whitney_Wesco_Meeting_Notes_2005.pdf)明确说明并非逐字稿、现场禁止录音，内容由快速打字与记忆整理，且按主题重排。入库须标 `source_type=meeting_notes`、`primary_status=secondary`、`transcript_quality=rough`，补充说明其为现场记录者的同期笔记、并非逐字稿。引述时写“据 Tilson 的现场笔记”，不能去掉中间人。[Tilson 原站 2006 笔记](https://tilsonfunds.com/wscmtg06notes.pdf)同样包含编辑补充和对遗漏词句的猜测。

传记是用户需要的重要背景来源，但**传记整体不是两位本人的一手材料**：

- [Alice Schroeder《The Snowball》出版方记录](https://www.penguinrandomhouse.com/books/162310/the-snowball-by-alice-schroeder/)确认作者、版本及与巴菲特合作采访背景。作者叙述标二手；书中可追溯本人采访的段落标“经传记转述的一手引语”，保留书名、版次、页码，不能反推为独立原始录音。
- Janet Lowe《Damn Right!》可由 [Wiley 提供的章节样张](https://catalogimages.wiley.com/images/db/pdf/0471244732.pdf)和[版权/书名页](https://catalogimages.wiley.com/images/db/pdf/R0471244732.fm.pdf)核验。公开样张不等于整本已收集。不同版本页码不同。
- 仅从出版社元数据可以核实书目，不能回答书中未读取章节的细节。受版权保护的整本资料通过用户已有授权文件或合法阅读权限接入；本资料包不附盗版书。

## 采集与回答所需的最小来源链

为每件文献分别记录：原作者/发言人、发表机构、原始 URL、实际获取 URL、事件日期、发布/签署日期、报告年度、版本、语言、来源类型、转录方式、抓取方式、原文件校验值、页码/章节/可验证时间码，以及引用权限。正文保持原文，翻译与总结另存。

证据强度并不等于同一个句子被转载的次数。多站转载同一次发言只算一个源事件；AI 编写的“巴菲特金句”、其他人格 skill 的总结、第三方视频剪辑标题不进入原话证据层。问答先查原始陈述，再比较年代、问题语境和反例；推测必须另标“基于证据的模拟”，明确哪些前提来自原文、哪些连接由模型提出。对于本人没有谈过的新问题，引用相似原则只能说明推断路径，不能保证真实本人一定同意。
