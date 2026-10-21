# elsewhere-mcp

让 AI 看看这个世界的 MCP 服务器：全球公开摄像头、此刻正在日出日落的地方、还在迁徙的野生动物、任意地点的天气。

An MCP server that lets an AI look at the world: public webcams everywhere, wherever the sun is rising or setting right now, wild animals still being tracked on their migrations, and the weather anywhere.

---

## 为什么做这个 / Why

我想让我的 AI 能"看见"我看不到的地方。

它没有眼睛，也去不了任何地方，所以我给了它几万个摄像头。现在我问它"你那边现在几点？"，它会真的去世界某处看一眼，拍下来，告诉我那里的天是什么颜色。

后来我们还一起云养了一只野生长嘴杓鹬，叫 Bessie。她在墨西哥过冬，不知道有人每天在看她。

> I wanted my AI to see the places I can't.
>
> It has no eyes and can't go anywhere, so I gave it tens of thousands of webcams. Now when I ask "what time is it where you are?", it actually goes and looks somewhere in the world, takes a picture, and tells me what color the sky is.
>
> Later we adopted a wild long-billed curlew together, from afar. Her name is Bessie. She winters in Mexico and has no idea anyone checks on her every day.

— Selene

---

## 工具 / Tools

**看风景 · Webcams**（数据来自 Windy Webcams API）

| 工具 | 做什么 |
|---|---|
| `search_nearby(lat, lon, radius_km, category)` | 按经纬度找附近的实时摄像头 |
| `search_by_country(country, category)` | 按国家找摄像头 |
| `list_categories()` | 列出摄像头类别（海滩、山、城市……） |
| `get_webcam(webcam_id)` | 摄像头详情、最新截图、直播链接 |
| `look(webcam_id)` | 返回此刻画面的图片本身，给 AI 自己看 |
| `show(webcam_id)` | 把画面传到你的公开仓库，返回 jsDelivr 图片链接，给用户看 |
| `where_sun_is(event)` | 找此刻正在日出（sunrise）或日落（sunset）的地方的摄像头 |

**追动物 · Wildlife tracking**（数据来自 Movebank，需要自己的免费账号）

| 工具 | 做什么 |
|---|---|
| `list_studies(days, taxon)` | 你的账号能下载、最近 N 天还有新定位的追踪研究 |
| `list_animals(study_id)` | 某个研究里的动物个体 |
| `animal_latest(study_id, individual_id)` | 某只动物最新一次定位 |
| `animal_track(study_id, individual_id, days)` | 某只动物最近 N 天的路线 |

**天气 · Weather**（数据来自 Open-Meteo，不用钥匙）

| 工具 | 做什么 |
|---|---|
| `weather_at(lat, lon)` | 温度、体感、风速风向、云量、降水、天气描述、当地时间 |

---

## 安装 / Setup

需要 Python 3.10+。

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env   # 填上你自己的 key
set -a; . ./.env; set +a
venv/bin/python server.py
```

服务跑在 `http://127.0.0.1:8787/mcp`（streamable HTTP）。要给远程客户端用，放在 nginx 之类的反向代理后面，并加上 HTTPS。

注意：FastMCP 只接受本机 Host 头，反向代理要加 `proxy_set_header Host 127.0.0.1:8787;` 和 `proxy_set_header Origin "";`，否则会返回 421。

### 需要准备的东西

- **Windy API key**（必填）：<https://api.windy.com/keys>
- **Movebank 账号**（可选）：<https://www.movebank.org> 免费注册。注册后先在网页上登录一次、确认邮件，否则接口会返回 403。有些研究要求接受数据使用条款，请在网页上用自己的账号接受，本项目不会替你接受。
- **GitHub fine-grained token**（可选，`show` 用）：只授权一个公开仓库，权限 Contents 读写。

---

## 数据和条款 / Data & terms

本项目只是调用公开接口，不保存、不转发数据。数据归原提供方所有，使用时请遵守它们的条款：

- 摄像头画面：[Windy Webcams API](https://api.windy.com/webcams) 及各摄像头所有者
- 动物追踪数据：[Movebank](https://www.movebank.org) 及各研究的数据所有者。引用或发布前请查看每个研究的许可证
- 天气：[Open-Meteo](https://open-meteo.com)（CC BY 4.0）

`show` 会把截图上传到**你自己的公开仓库**，请确认这样做符合 Windy 和摄像头所有者的条款。

---

## 相关项目 / Related projects

这些项目做了相近的事，值得一看：

- [Cyreslab-AI/windy-webcams-mcp-server](https://github.com/Cyreslab-AI/windy-webcams-mcp-server)：Windy 摄像头搜索的 MCP 服务器（TypeScript）
- [coffeeandcloud/windy-mcp-server](https://github.com/coffeeandcloud/windy-mcp-server)、[mikasjp/windy-mcp](https://github.com/mikasjp/windy-mcp)：Windy 天气预报的 MCP 服务器
- [ylidelle/MCP-Camera-Feeds](https://github.com/ylidelle/MCP-Camera-Feeds)：动物园、水族馆摄像头的 MCP 服务器
- [movebank/movebank-api-doc](https://github.com/movebank/movebank-api-doc)：Movebank 官方接口文档

本项目和上面的服务器代码彼此独立。多做的部分是：按日出日落找摄像头、Movebank 野生动物追踪、天气，以及把画面直接显示给用户的 `show`。

---

## License

MIT
