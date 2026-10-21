---
name: "xiezhen-shoot-planner"
description: "Codex / Claude 的真实景点+真实日期人像外拍规划：出片点与 SNS 机位调研、照着小红书/Instagram/抖音出片帖设计同款机位与姿势、穿搭方案、太阳/地形/天气光线、园区底图、一日行程与园内路线、≥9 张分镜（含连拍/短片/实况，编号按路线，每页带站位坐标与谷歌地图步行导航）与拍摄脚本，再用系列词链写 prompt、codex-imagegen 出示意图。触发：外拍规划、拍摄脚本、拍摄小抄、出片点、光线角度、分镜、穿搭、路线、行程、站位导航、写真出图。"
---

# 外拍规划与写真出图接力（Codex / Claude）

代码仓库：GitHub `utopiabelmont/xiezhen-shoot-pipeline`，安装见仓库 `INSTALL.md`。本 skill 可由 Codex 独立执行全部阶段，也可保留 Claude + Codex 出图的接力方式；不依赖 Claude、Claude in Chrome 或另一位代理。

下文用 `<root>` 指仓库根目录，按这个顺序确定：① 用户本次对话指定的路径；② 当前工作区里含 `pipeline.py` 与 `docs/WORKFLOW.md` 的目录；③ 环境变量 `XIEZHEN_CONFIG` 指向的文件，否则 `~/.xiezhen-pipeline/config.json`（Windows 为 `%USERPROFILE%\.xiezhen-pipeline\config.json`）里的 `root`。同文件的 `python` 是候选解释器，使用前验证路径仍存在且属于当前选定仓库；优先使用当前仓库 `.venv`，再用可用的 Python 3.10+。仅安装 SKILL.md 不等于装好运行时；三处都没有时按 `INSTALL.md` 下载完整仓库并安装依赖，路径无法确定再问用户。云端会话须在云端另装运行时，本机登记与登录不会自动同步。统一入口 `<python> <root>/pipeline.py <阶段> <plan>`，工作目录设为 `<root>`；每个阶段的输入、输出、验收标准在 `<root>/docs/WORKFLOW.md`。

## 环境能力与可选依赖

- Codex 桌面版 / CLI：直接用终端与文件工具执行脚本、读写 JSON 和 Markdown。Windows 路径含空格时用 `& '<python绝对路径>' '<root>/pipeline.py' ...`，设置 `PYTHONUTF8=1` 与 `PYTHONIOENCODING=utf-8`。不要要求用户点击 `run_job.cmd`，除非当前确实没有终端能力。
- 调研：使用当前会话已有的网页搜索或浏览器工具；能访问用户已登录浏览器时做 SNS 人工级浏览。Codex CLI 不保证带有登录浏览器。无法访问时，记录平台、查询日期、原因与未验证项，采用可读的公开网页或用户给出的文字资料；不把搜索摘要当成已看过的原帖。未实际观察到的构图、姿势、点赞数、设备、EXIF 不编造；没有可靠 SNS 素材的分镜用 `src.kind="无 SNS 素材"`，`meta.sns` 写明调研缺口，继续完成其余阶段。
- prompt：已安装 `nuyoah-xiezhen-prompt` 时读取并应用；未安装时直接用本仓库 `templates/prompt_chains.md` 的系列母版与变体规则，并按阶段 9 的检查项验收，不要求先安装 Claude skill。
- 出图：`stylize` / `shots` 使用本环境安装的 `codex-imagegen-cli` 与 ChatGPT 登录。缺少它时保留 OSM 底图，交付分镜、prompt、无示意图的 PDF 与核对表，说明尚未生成图片。不要假定任意 Codex 环境均有生图接口或凭据，也不要递归启动另一个 Codex 来执行规划。

## 输入

用户给出：景点名（一个或一天里的多个，或坐标）、日期（可多日）、到场时段、器材（机身、镜头焦段范围、有无闪光/反光板）、人物数与服装方向。缺日期时先问一次；器材没说就用默认这一套：Sony α7 V + FE 24-105mm F4 + HVL-F60RM2（主力：静态、连拍、短片），iPhone 14 Pro（实况、手机随拍），DJI Osmo Pocket 3（20mm 等效，三轴云台，适合手持跟拍与环绕短片），Ricoh GR IV（28mm 等效定焦，适合随手抓拍与细节）；用户有几台设备就把几台都写进 `--gear`（写进 `meta.gear`），SNS 调研和分镜都按这份设备清单来；其余按默认继续（一位成年女性，服装由阶段 2b 提议）。多个景点时每个景点各建一个 plan，主 plan 里写 `trip.json` 排一天的顺序。

## 网络与执行位置

- 脚本要联网（Nominatim、Overpass、Open-Meteo、Commons）。先在当前执行环境直接运行；不能访问接口时说明缺口。`--fixture` 仅用于安装自测，仓库样本不是本次出行的实况数据。获取到真实天气 JSON 时可用 `sun --weather-json`；不要把真实响应覆盖进仓库的离线样本。
- 出图必须在装了 codex-imagegen 且已 ChatGPT 登录的环境上跑。Overpass 504 可以稍后重跑；生图失败按阶段 8 只记录、不自动重试。重跑底图时 geometry / meta / styled 三个文件必须来自同一次 basemap，否则叠加会错位。
- Claude 等确实没有终端能力的会话才使用本机桥接：把命令写进 `<root>\job.ps1`（UTF-8 with BOM，模板 `scripts/job.example.ps1`），双击 `run_job.cmd`，读 `job_done.txt` 与 `job_log.txt`；具体见 `docs/WINDOWS_SETUP.md`。不假定会话能控制本机。
- 批量出图默认按当前 plan 执行 `shots`。需要并行时可拆 jsonl 用 `run_shots.py --jobs`，每条只提交一次；Windows 的后台 `Start-Process` 使用 `-WindowStyle Hidden`。输出按编号合并到 `out/<plan>/`。

## 流程（阶段号与 WORKFLOW.md 一致）

0. **立项**　`pipeline.py init <plan> --place ... --date ... --arrive ... --hours ... [--lat --lon] [--elev-m] [--gear] [--body] [--flash] [--outfit]`。`<plan>` 用「地点缩写-月日」。
1. **出片点**　`pipeline.py spots <plan>`，读 `spots.md`，按末尾关键词做网页调研（官方见どころ页、日文/中文攻略、拍摄规则、票价、开放时间、人流时段）。
2. **SNS 调研**　用户已在 Chrome 登录小红书 / Instagram / 抖音 / TikTok 时，人工级浏览并填 `spots_social.md`（模板 `templates/sns_research.md`）；不批量抓取、不保存图片。各平台路径（2026-09-27 实测）：小红书直接开 `search_result?keyword=` 常空白，要在 `/explore` 首页搜索框里输入关键词回车，先读结果页右侧「点点」AI 对 30 篇笔记的机位汇总，再点 1–3 篇高赞帖（用 JS 跳 `/explore/<id>` 会触发 300031 风控，拦一次就停）；抖音 `douyin.com/search/<词>` 可用，等 10 秒以上再读；TikTok `tiktok.com/search?q=` 首次常报「不明なエラー」，点「もう一度お試しください」即出；Instagram `explore/search/keyword/?q=%23<标签>` 读图片 alt。顺带看近期活动（祭典、灯笼祭、投影、临时封闭）。检索词除了「<地点> 拍照 / 机位 / 出片」，再按设备清单里的每台设备各搜一轮（例「<地点> GR4」「<地点> pocket3」「<地点> 索尼A7M5」「<地点> iPhone 人像」）；帖子里写明或能从画面与 EXIF 说明判断的拍摄设备记进 `sns_refs.json` 的 `device`，用户手上有同款设备的机位帖优先复刻（焦段、画幅、成像观感对得上），设备不同时在 `reproducible.why` 写清换算（例「原帖 GR 28mm，用 24-105 的 28mm 端」）。末尾必须写「对分镜的影响」：与主流机位重合的、本组差异化机位、新增备选、需现场核实的。
   出过片的帖子逐条记进 `plans/<plan>/sns_refs.json`（规则见 `docs/SNS_NOTES.md`）：机位帖 S01…（机位方位与距离、机高、焦段估计、景别、`frame` 人物中心横向位置与头顶/脚的纵向比例、前景背景从近到远、姿势、穿搭、天气光线、可复现度与理由、对应停留点），姿势帖 X1… 拆成姿势 P01…（名称、一句话要领、景别方向焦段、适合的场景），平台汇总 Q1…（检索词、汇总篇数、要点）。**只看图写字**：不下载、不截图原帖图片，也不用 Codex、系统截图等任何方式保存；原帖图片不交给生图模型做参考或 edit 输入。用户想在私用版 PDF 里看原图时，让用户自己用手机保存后放进 `sns_inbox/`，跑 `pipeline.py sns-import <plan>` 归到 `sns_private/`（不入库，公开版不放）。
2b. **穿搭**　`pipeline.py palette <plan>`（从 Commons 场地照抽 6 个主色；也可 `--images` 用现场照），再按 `docs/OUTFIT_GUIDE.md` 与 `templates/outfit_template.md` 写 `plans/<plan>/outfit.json` 与 `outfit.md`：先按场地前三主色选路线（同系色融 / 邻近色稳 / 补色点缀跳），全身 ≤ 3 色加一处点缀，服装色与场地主色 ΔE ≥ 12（有意融入标 `blend_ok`），红叶季亮一档、阴天脸旁放亮色、强色背景避纯白纯黑、避细条纹与反光面料、裙长配动作、一套主装 + 一件可换层次 + 道具；写替换方案（雨/晴/冷/园外备选）、道具妆发、逐张提醒、SNS 穿搭观察（`spots_social.md` 穿搭栏）。`meta.outfit`、prompt 的 OUTFIT 词链、`model_sheet.md` 都从它来；`cards` 阶段把它渲染成 PDF 第一页。
3. **光线**　`pipeline.py sun <plan>`，读 `sun.md`：逐半小时方位/高度/影长、地形遮挡后的实际直射截止、天气光质（直射比≥0.5 且云量<60% 晴天硬光；≥0.5 高云透光；0.2–0.5 薄云；<0.2 阴天）、人物朝向与光型表。日期超出 16 天只用天文数据，临近再跑；出发前一天必跑一次：`pipeline.py sun <plan> --weather-only` 只刷新预报（逐时天气、降水量、气温体感、风），本机与云端都拉不到 Open-Meteo 时，用当前可用的网页工具打开接口 URL 读出 JSON 存到文件，加 `--weather-json <文件>`；然后更新 `meta.forecast` 与 `trip.json` 的 `weather`，重跑 `cards`。
4. **底图**　`pipeline.py basemap <plan> --meters <园区最长边×1.2> [--center lat,lon]`；密集城区或长条形场地拆成两张（`--name north/south`，各 260–300 m）；园外备选点另做 `--name <x> --center ...`；OSM 缺失的步道用 `--extra`（`templates/geometry_extra_example.json`），`approx: true` 的线在小抄上注明「概略」。分镜的 `subject_latlon` 要落在所选底图范围内，边缘留 60 m。
5. **风格化**　`pipeline.py stylize <plan> [--name] [--prompt-extra "..."]`（codex-imagegen edit，指令 `templates/basemap_style_prompt.txt`）。与 `_osm.png` 并排核对几何未漂移；城区宽马路被画成运河时加 `--prompt-extra "图中没有任何河流、运河或水面，所有灰色道路都画成浅灰米色的路面"` 重跑。
6. **分镜**　从 SNS 素材出发：每条可复现的机位帖设计一张同款（机位、焦段、构图、姿势照原帖），姿势帖里的每个姿势按场景分到停留点各设计一张，平台汇总的姿势补在对应地点；每张写 `src`（`ref`、`kind`、`platform`、`title`、`url`、`posted`、机位帖的 `level` / `why`、姿势帖的 `likes` / `pose_id` / `pose_name` / `pose_how`、`what` 照搬了什么、`also` 同时参考的素材）。与原帖不同的地方（天气、背影开场、加一个动作）写进 `what` 或 `why`。素材覆盖不到的开场过渡、细节、连拍、短片、实况再补，`src` 写 `{"ref": "", "kind": "无 SNS 素材", "what": "补充分镜：…"}`。季节不符复现不了的帖子只作穿搭参考。`meta.sns` 一句话记录素材使用情况。然后读 `docs/SHOT_DESIGN.md`（分镜基本法，见下节摘要），按 `templates/shotlist_template.md` 与 `templates/shotlist_schema.json` 写 `plans/<plan>/shotlist.json`，导出 `shotlist.md`；每条写 `role`、`pose`、`gaze`，主图 `hero: true`，备选 `optional: true`。动态素材按 `docs/VIDEO_NOTES.md` 加在静态分镜之后（标 `supplement: true`）：`medium: burst` 连拍 ≥ 2 张（30 张/秒、预拍 0.5 s、1/500 以上，动作有起止，连拍只选 1 张，出的是照片、计入组图）；`medium: video` 短片 ≥ 5 条、六个角色各一（S-Gamut3/S-Log3、ISO 800、斑马 52% 看脸 95% 看高光、180° 快门配 ND、竖幅；`clip.mode` 24p 实时 ≤ 5 s 或 sq60 / sq120 升格实录 2–3 s；`clip.move` 从运镜库选一种：opening 下摇揭示或遮挡揭示、context 侧跟/后跟/前跟、interaction 固定微推或 1/4 环绕、portrait 固定转身回眸、detail 固定升格、closing 后拉上摇；写 `start` / `end` / `nd` / `exposure`，起止各留 1 秒静止；运镜页的轨迹按 `clip.move_type` 画，文字判断不准时写明 `move_type`，距离、机高、环绕方向可用 `cam_dist_start` / `cam_dist_end` / `cam_h` / `orbit_side` 覆盖）；`medium: live` iPhone 实况 ≥ 6 条放在过渡、候场、室内与主要机位。短片与实况不计入 9 张与景别配比。写完跑 `pipeline.py lint <plan>`：硬性项不过就改分镜（`jobs` 阶段会拒绝生成任务），提示项能改则改。硬性要求：≥ 9 条；景别覆盖特写、近景、半身、全身、环境远景中至少 4 种；焦段只从器材里选（每条可写 `device`，不写视为主机身：主图与连拍用主机身，需要稳定器的跟拍或环绕短片可交给 Pocket 3，随手抓拍与细节可交给 GR，实况用 iPhone；`lens` 写该设备的等效焦段，照同款设备原帖设计的分镜用同一台）；每条写太阳方位、光型、人物朝向、机位距离、晴天/阴天/雨天备选；同组内动作、视线、机位不重复；每条有 `subject_latlon`、`cam_bearing`、`cam_dist`、`face_bearing`、`bg_bearing`、`bg_label`、`size`、`look`、`flash`；室内 `indoor: true`；多底图时每条写 `basemap`；`alt_time` 指晴天版时刻；**站位要精确到能走过去**：`subject_latlon` 写 5 位小数（约 1 m），落在能站人的人行道、露台或沙滩上，不落在车道、楼内或水面，用 OSM 节点与路网（Overpass 查 `tourism=viewpoint`、`artwork`、桥梁、`highway=footway` 与 `level`）或 Google 地图核对，标志物站位写进 `scene_bible.md`；导航目标默认是人物站位，长焦远机位写 `walk_to: {"to": "camera"}`（由 `cam_bearing` + `cam_dist` 推算机位），室内写 `walk_to: {"place_id": "<Google 地点 ID>", "label": "<店名> <楼层>"}`，车站、巴士站、店门等写 `walk_to: {"latlon": [..], "label": ".."}`；写完跑 `python tools/nav.py --plan plans/<plan>` 列出每条的导航目标逐条核对；`meta.sun` 从 `sun.json` 的 rows 取整点与半点；`meta.date` 与 `meta.place` 必填（PDF 命名用）。
6b. **路线**　在 `meta.route_stops` 写园内停留点顺序（每站的分镜 id 与备注）、`meta.route_source`（官网設施顺序 / 順路、小红书或官方博客攻略、当天预报）、`meta.route_speed_mps`（雨天 0.85）；一天多景点另写 `plans/<主plan>/trip.json`（模板 `templates/trip_template.md`：起点、各景点、点间交通的线路 / 发到时刻 / 分钟 / 来源，备选景点 `optional`；`weather.summary` 一句话写当天天气对行程的影响、`weather.notes` 写雨具衣物路面等提醒，逐时天气由脚本从 `sun.json` 截取）。`pipeline.py route <plan>` 与 `pipeline.py trip <plan>`（`cards` 阶段会自动跑）沿底图步道算最短路、估停留与时刻，出 `route.md` / `trip.md` 与两张页面。分镜时段已按光线与活动时刻排好时写 `meta.route_timing: "shots"`（每站停留按分镜时间窗）与 `meta.route_start`（出站后第一站的到达时刻），停留点可写 `dwell_min`；分镜分在几张底图上时另做一张覆盖全程的总览底图（`basemap <plan> --name route --meters <全程最长边×1.2>`），写进 `meta.route_basemap`。路线页终点时刻要早于离开的班次。路线定下后跑 `pipeline.py renumber <plan>`：编号改成游览顺序（01 是路线上第一张，备选排最后），每张时段按停留点到达—离开时刻均分，同步 `outfit.json` per_shot、`sns_refs.json`、`prompts.md` 标题，写 `id_map.json`；脚本列出正文里的旧编号引用（「改 16 室内」「同 09」），手改。已出图的用 `--rename-images`，最好先编号再出图。规则见 `docs/ROUTE_NOTES.md`：顺序按 营业时间与最后入场 → 光线时段 → 交通班次 → 官网順路 / 攻略 → 天气 → 地理最短路；官方地图只读顺序不放进小抄；路线不穿建筑与水面，终点靠出口，总时长不超过营业时间。
7. **prompt**　先写 `plans/<plan>/scene_bible.md`：场地真实样子（建筑材质颜色、桥与栏杆形制、标志物的高度形状与位置、当季植被）与容易被画错的东西，场景词链与负面词从它来。有 `src` 的分镜，取景段直接用 `sns_refs.json` 对原帖构图的文字（人物位置比例、前景背景从近到远），姿势段用 `src.pose_how`；只用文字，不加参考图。用已安装的 `nuyoah-xiezhen-prompt`，未安装则用 `templates/prompt_chains.md` 的「系列母版 + 同系列变体」：全组固定风格词链、成像词链、人物与服装（`templates/prompt_chains.md`），每张只改取景与机位、动作与视线、环境与光线；光线引用 `sun.md`，按「来源—落点—结果」写；服装与道具分开写；无参考图时写「本张重新生成一位「…」类型的成年原创女性」。输出 `plans/<plan>/prompts.md`：每张 `## <id>-<标题>` 后接一个 ```text 代码块（`jobs` 阶段靠此解析；标题会成为文件名，不带 `/`）。每条短片另在 `move_prompts.md` 写 `## <id>a-起幅` / `## <id>b-中间` / `## <id>c-落幅` 三节：人物、服装、场景、光线沿用该短片的词链，只换每帧的取景与动作，写清三帧之间人物大小、俯仰、朝向怎么变，并写「主体放在画面中间约七成宽度内」（运镜页裁成 9:16）；没有人物的帧写「画面里没有人物」。短片与实况写「关键帧」：成像词链换成对应介质的观感（S-Log3 还原后的柔和影调 / iPhone 实况观感），运动部位写轻微动态模糊，风格、人物、服装词链不变。
8. **出图**　`pipeline.py jobs <plan>` → `inbox/<plan>.jsonl`（追加分镜后用 `--missing` 只排还没出图的）；短片三帧 `pipeline.py jobs <plan> --moves` → `shots --moves` → `out/<plan>-moves/`，挑好的放进 `plans/<plan>/move_frames/`；`pipeline.py shots <plan>`（只跑本企划的 jsonl，不用 `run_shots.cmd` 以免重跑 inbox 里的旧批次）。每条只提交一次，失败只记录，不改词不重试。尺寸 3:4 → 1152x1536，4:5 → 1216x1520，横幅 1536x1152；后端改成 1086x1448 属正常；单张 30–120 秒。
9. **检查**　逐张检查人物完整性、服装与道具分离、光线来源与落点、景别焦段、手指肢体、文字水印、黑边暗角；已安装 nuyoah-xiezhen-prompt 时另按其第六步检查。再核对光向与 `sun.md`、背景方位与底图一致、构图与 `sns_refs.json` 对原帖的描述一致（人物位置、朝向、前景背景）；短片三帧看起中止之间的变化是否符合运镜。构图不对就改写取景段重出，有黑边暗角加负面词重出（检查后改词重出是新的一轮，和阶段 8 的「不自动重试」不冲突）。状态只写 test / failed，用户确认后才 final；重做回到原始分镜重新编译，不用上一轮生成图做输入。把 `out/<plan>/log.jsonl` 复制为 `plans/<plan>/generation_log.jsonl`。
10. **拍摄脚本与核对表**　`pipeline.py cards <plan> [--images out/<plan>]`（图片按文件名前两位匹配分镜 id），逐页检查：文字溢出、标签重叠、太阳箭头方向、页脚「AI 拍摄示意，非现场实拍」、右下「时段 · 地点 · 步行导航」的坐标与二维码。每张分镜卡右下写站位坐标、谷歌地图步行导航链接（`https://www.google.com/maps/dir/?api=1&destination=<lat>,<lon>&travelmode=walking`，有 place_id 时加 `destination_place_id`）与二维码，PDF 里二维码和导航行可直接点按（`cards/links.json` + pypdf，没装 pypdf 时只能扫码）；核对表里每条分镜有「谷歌地图步行导航」，每个停留点有「导航到本站」。产物 `cards/card_<id>.png`、`cards/outfit_0*.png` 与 PDF；PDF 顺序固定为 行程页 → 穿搭页 → 路线页 → 分镜按路线顺序（无路线时静态在前、动态在后），短片一览只进核对表。有 `src` 的分镜卡：左侧一张示意图，中间来源栏（素材类型与可复现度、平台日期、原帖标题、二维码、照搬了什么、同款姿势、现场差异、链接），补充分镜写「无 SNS 素材」；分镜都带 `src` 时不再出 SNS 汇总页与姿势参考页。连拍与短片的「相机设置」块会自动换成连拍或 S-Log3 短片的内容，分镜写了 `device` 时第一行显示「设备焦段」；每条短片卡后面自动插一页运镜示意（俯视轨迹、侧视俯仰、操作要点、起中止三帧、时间条），`move_frames/` 里有三帧时用 Codex 画面并放大，否则用线稿；检查轨迹方向、距离与三帧是否符合分镜意图。**PDF 文件名固定为 `<出行日期>_<地点>_拍摄脚本.pdf`**（例 `2026-09-28_浅草寺_拍摄脚本.pdf`，改版加 `_v2`），由 `pipeline.py` 按 `shotlist.json` 的 `meta.date` 与 `meta.place`（括号前的部分）自动命名；同一步还生成 `<出行日期>_<地点>_拍摄核对表.html`（现场勾选用：器材（按设备列出用在哪几张）、服装、行程、到场核对、按路线分组的分镜与每条的原帖链接、短片运镜一览、收尾；也可 `pipeline.py checklist <plan>` 单独做；发布或放进 examples 用 `--public`），和 PDF 一起交付；交付给用户、同步到本机、放进 examples 的文件都用这个名字，不用「拍摄脚本.pdf」这类无日期无地点的名字。
11. **当天资料**　`timeline.md`（交通班次注明来源与查询日期、每张时段、分岔点、最后入场、回程后续 3 班）、`model_sheet.md`（服装/道具/妆发/每张一句话，标出照哪条帖子的同款）、`arrival_checklist.md`（到场 10 分钟核对项）、有短片时 `clips.md`（剪辑顺序与转场遮挡物，模板 `templates/clips_template.md`；时间线每条 video 加 1.5 分钟）。

改版：复制为 `<plan>-v2`，只重做变动的分镜，复用图片记 `img_from`，新增分镜单独出图，最后统一重跑 `cards`，`generation_log.jsonl` 合并两轮。编号或分镜大改时（例如改成 SNS 驱动）整轮重做：新 plan 里重写 `shotlist.json` 与 `prompts.md`，`id_map.json` 记新旧对应，时间线、模特页、剪辑单、到场清单按新编号重写。

## 分镜基本法（docs/SHOT_DESIGN.md 摘要，lint 按此检查）

- 叙事：一组 9–13 张是一段有开头、高潮、结尾的故事。角色 `role`：`opening` 开场（交代环境，排第一）、`context` 环境（人与场地，走动穿行）、`interaction` 互动（人在做什么，≥ 2）、`portrait` 肖像（情绪与身份）、`detail` 细节（手、道具、局部，≥ 1，给节奏换气）、`closing` 收尾（背影、远眺、俯瞰，排最后）；主图 `hero: true` ≥ 1。每张只讲一件事，两张讲同一件事就删一张。
- 景别配比：远景定氛围 ≥ 1、全身定状态 ≥ 2、七分/中景讲日常 ≥ 1、半身 ≥ 2、近景抓情绪 ≥ 1、特写提质感 ≥ 1；单一景别 ≤ 40%，至少覆盖 4 类。
- 节奏：寄り/引き 交替，相邻两张景别不同，相邻两张焦段档或机位方向不同；焦段覆盖 广(≤35)/标(50)/中长(70–105) 三档；至少一张俯或仰。拍摄顺序按动线，成片顺序按叙事。
- 姿态 `pose` 至少三种（stand/walk/sit/lean/back/crouch）；视线 `gaze` 看镜头（camera）不超过 60%，其余 away/down/closed/back；正面看镜头、侧面看远处、背影靠手部小动作；动作只做一半。
- 裁切不在颈、肘、腕、膝、踝；人朝向景物，人景比例 2:3 或 5:5；至少两张有前景层次，至少一张用框（门洞、拱廊、柱子）。
- 光：阴天靠来源方向造差异（檐下背光、拱廊开口侧光、窗光、店灯）；晴天版至少一张逆光/侧逆光；正午硬光优先门楼、回廊、树荫。
- 一致性：一人一套服装（道具可换）、一种创意外观与白平衡、一个色彩主题；主图是竖幅、构图完整、脸清楚、背景最有辨识度的一张。

## 相机与闪光灯的默认策略（Sony α7 V + HVL-F60RM2）

短片：動画位 4K 24p S-Log3，S&Q 位 60→24 与 120→24 两个预设，斑马 52%/95%，伽马显示辅助开，WB 固定 5600K，三分线网格与 90% 安全框，Dynamic Active，晴天 ND64–256 / 薄云 ND16–32 / 阴天 ND4–8；曝光补偿与测光按每条 `clip.exposure`（逆光以脸为准让背景过曝，白墙水面 +0.3～0.7，深色背景 −0.3）。连拍 H+ 电子 30 张/秒预拍 0.5 s，横向走动果冻明显换机械 10 张/秒。

全组固定一种创意外观（阴雨低饱和用 IN；要保留朱红、靶蓝这类对比色用 FL），WB 固定阴天预设或 5600K，RAW+JPEG；记忆位 M1 散射 / M2 逆光 / M3 黄昏闪光。闪光灯阴天默认关，只在黄昏收尾（后帘同步，TTL −1 EV，1/60）或晴天后侧光补脸（TTL −1.3 EV，HSS）时用；展厅、寺社内堂一律关。细节见 `docs/CAMERA_NOTES.md`。

只用手机拍（`--body` 写 iPhone 等）时：`lens` 写镜头档位（0.5× / 1× 24·28·35mm / 2× / 人像模式 / 5×），`clip.mode` 的 24p / sq60 / sq120 对应录像 4K 24 fps、录像 4K 60 fps（回家放 24p）、慢动作 4K 120 fps，`clip.nd` 写「—」，连拍写 `burst.fps: 10`、`precap_s: 0`（快门键向左滑住），`look` 写摄影风格与格式，`flash` 写关；`cards` 与 `checklist` 自动换成手机的写法，详见 `docs/VIDEO_NOTES.md` 第 8 节。

## 交付

对话中给：调研摘要（spot 列表与来源链接、SNS 结论与 `sns_refs.json` 的素材清单、每张分镜对应哪条素材）、光线摘要（关键时刻与实际直射截止）、分镜表与 lint 结果、每张完整 prompt、图片路径、质量状态与 `generation_log.jsonl`、穿搭方案（`outfit.md`）、拍摄脚本 PDF（`<日期>_<地点>_拍摄脚本.pdf`，行程、穿搭、路线页在前，分镜按路线顺序编号，每页附 SNS 来源与二维码、站位坐标与谷歌地图步行导航，短片卡后接运镜页）与核对表 HTML（`<日期>_<地点>_拍摄核对表.html`）、时间线/模特页/到场清单/剪辑单/行程与路线页，以及需要现场核实的事项。写作不用设问式标题、「不是A，是B」式对举与破折号金句。
