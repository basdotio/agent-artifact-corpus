# 从飞书日历拿简历附件（2026-09-15 实测）

面试日程由 HR（章丹烨）约，标题格式：`算法实习（<姓名>）——线上面试`，简历 PDF 挂在日程附件里。

## 为什么走浏览器 UI 而不是接口

- 飞书网页日历的数据走 `internal-api-lark-api.feishu.cn/im/gateway/`，是 protobuf 私有网关，没法直接调。
- 开放平台 API（calendar/v4 + drive 下载）要建企业自建应用、管理员审批，用户没有现成凭证。
- 附件预览页是**整页图片渲染**（没有 textLayer，没有 canvas 文字），读不到文字 → 只能点下载。

所以流程 = 用户已登录的 Chrome（claude-in-chrome）打开日历 → 找日程 → 开附件预览 → **征得用户同意后**点下载。

## 步骤

1. `navigate` → `https://www.feishu.cn/calendar/week`（会跳到企业域 `befriends.feishu.cn`），等 4 秒加载。
2. 列出本周面试日程（周视图 DOM 里有标题和时间）：
   ```js
   [...new Set([...document.querySelectorAll('div,span')].filter(e=>e.children.length<3)
     .map(e=>(e.innerText||'').trim().replace(/\s+/g,' '))
     .filter(t=>/面试/.test(t)&&t.length<60))]
   ```
   下周的点左上角 `>` 翻页再跑一次。和 `kb.py pending` / 已处理列表对一下，只处理还没有学习包的人；桌面已有同名简历 PDF 就直接用本地的，不用再下。
3. 截图定位日程块并点击 → 右侧弹出详情卡，「N 个附件 (xxx KB)」下面是 PDF 文件名。
4. 点文件名 → 打开全屏预览页，顶部是完整文件名，右上角两个图标：☁️ 存到云空间、⬇️ 下载。
5. **下载前在对话里问用户**（文件名 + 大小 + 来源：飞书日历某日程），得到明确同意再点 ⬇️。同一次请求里要下多份时，可以一次列清单一起问。
6. 文件落在 `~/Downloads/`，用 `ls -t ~/Downloads/*.pdf | head` 找到后 `mv` 到 `~/Desktop/`（和已有简历放一起）。
7. 点左上「退出」关预览，用完 `tabs_close_mcp` 关标签页。

## 坑

- 详情卡关掉后别在日历空白处乱点：点空白格子会弹「新建日程」框。误弹了就点框右上 × 关掉，**不要点保存**。
- 网络请求监听要在点击前先调用一次 `read_network_requests`，否则抓不到（不过这里用不上接口，一般不需要）。
- 附件文件名很长会被截断，以预览页顶部的完整名为准。
