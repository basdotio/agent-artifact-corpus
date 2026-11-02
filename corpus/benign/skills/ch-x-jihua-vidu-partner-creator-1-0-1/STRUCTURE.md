# partner-creator 文件夹结构说明

## 📁 目录结构

```
partner-creator/
├── SKILL.md                    # 主文档 - Skill 使用指南
├── QUICKSTART.md               # 快速开始指南
├── STRUCTURE.md                # 本文件 - 文件夹结构说明
│
├── assets/                     # 资源文件夹
│   ├── character-sheet.png     # 角色设计图（单张）
│   ├── character-sheet-1.png   # 角色设计图（多张版本）
│   ├── character-sheet-2.png
│   ├── character-three-view-1.png  # 三视图（正面/侧面/背面）
│   ├── character-three-view-2.png
│   ├── greeting.png            # 打招呼图片
│   └── photos/                 # 角色参考照片文件夹
│       ├── photo_1.jpg
│       ├── photo_2.jpg
│       └── photo_3.jpg
│
├── config/                     # 配置文件夹
│   └── push-config.json        # 定时推送配置
│
├── references/                 # 参考文档文件夹
│   ├── current-character.md    # 当前角色设定文档
│   └── daily-scenes.md         # 日常场景库
│
├── scripts/                    # 脚本文件夹
│   ├── search-images-tavily.mjs    # 🔍 搜索角色照片（Tavily API）
│   ├── setup-character.sh          # 角色初始化脚本
│   ├── generate-character-sheet.sh # 生成角色设计图
│   ├── generate-reference.sh       # 生成参考图
│   ├── generate-image.sh           # 生成图片
│   ├── generate-video.sh           # 生成视频
│   ├── choose-media-type.sh        # 选择媒体类型（图片/视频）
│   ├── send-message.sh             # 发送消息
│   ├── send-feishu-video.sh        # 发送视频到飞书
│   ├── proactive-message.sh        # 🤖 主动发消息
│   ├── hourly-push.sh              # 定时推送（单次）
│   └── push-daemon.sh              # 守护进程（定时推送管理）
│
└── templates/                  # 模板文件夹
    └── character-template.md   # 角色设定模板
```

---

## 📂 文件夹功能详解

### 1. `/assets` - 资源文件夹

**功能：** 存放所有生成的图片和参考照片

#### 子文件夹 `/assets/photos`
- **功能：** 存放角色参考照片
- **用途：** 从网上搜索下载或用户提供的角色照片，用于生成三视图和后续图片
- **格式：** jpg, png, webp 等图片格式

#### 主要文件：
- `character-sheet.png` - 角色设计图（单张版本）
- `character-three-view-*.png` - 三视图（正面/侧面/背面在同一张图）
- `greeting.png` - 用户确认满意后生成的打招呼图片

---

### 2. `/config` - 配置文件夹

**功能：** 存放配置文件

#### 文件说明：
- `push-config.json` - 定时推送配置
  - 包含平台信息（feishu/telegram/discord 等）
  - 目标聊天 ID
  - 推送时间设置
  - 启用/禁用状态

---

### 3. `/references` - 参考文档文件夹

**功能：** 存放角色设定和场景库

#### 文件说明：
- `current-character.md` - 当前角色的完整设定文档
  - 基础身份（名字、年龄、职业）
  - 外形设定（发型、眼睛、身材）
  - 性格设定（核心性格、情绪表达）
  - 关系设定（与用户的关系）
  - 日常生活（兴趣爱好、习惯）
  - 互动风格（说话语气、是否幽默）
  - 角色剧情（背景故事、人生目标）

- `daily-scenes.md` - 日常场景库
  - 工作场景（办公室、写代码、开会）
  - 休闲场景（看书、听音乐、打游戏）
  - 运动场景（健身、跑步、打球）
  - 美食场景（吃饭、喝咖啡）
  - 社交场景（聚会、逛街、看电影）
  - 居家场景（睡觉、做饭、看电视）

---

### 4. `/scripts` - 脚本文件夹

**功能：** 存放所有自动化脚本

#### 🔍 搜索和下载类：

##### `search-images-tavily.mjs` 
- **功能：** 使用 Tavily API 搜索角色照片
- **用法：**
  ```bash
  node scripts/search-images-tavily.mjs "角色名" -n 10        # 搜索图片URL
  node scripts/search-images-tavily.mjs "角色名" --download   # 直接下载
  ```
- **特点：**
  - 支持中国可访问的图片源（微博、百度、知乎等）
  - 自动过滤被墙网站（Instagram、Twitter 等）
  - 可选择下载或只返回 URL

---

#### 🎨 角色创建类：

##### `setup-character.sh`
- **功能：** 初始化新角色
- **用法：** `./scripts/setup-character.sh "角色名"`
- **执行内容：**
  - 创建角色设定文档
  - 搜索角色照片
  - 下载照片到 assets/photos/
  - 生成三视图

##### `generate-character-sheet.sh`
- **功能：** 生成角色设计图（单张）
- **用法：** `./scripts/generate-character-sheet.sh "角色名"`
- **输出：** assets/character-sheet.png

##### `generate-reference.sh`
- **功能：** 生成角色参考图（用于后续生成的依据）
- **用法：** `./scripts/generate-reference.sh "描述"`

---

#### 🖼️ 图片视频生成类：

##### `generate-image.sh`
- **功能：** 生成角色图片
- **用法：** `./scripts/generate-image.sh "场景描述" [输出路径] [比例]`
- **示例：**
  ```bash
  ./scripts/generate-image.sh "在咖啡店喝咖啡，微笑着看向镜头"
  ```
- **输出：** 默认保存到 assets/ 目录

##### `generate-video.sh`
- **功能：** 生成角色视频（4秒）
- **用法：** `./scripts/generate-video.sh "场景描述" [输出路径] [比例]`
- **输出：** MP4 格式视频

##### `choose-media-type.sh`
- **功能：** 自动选择生成图片还是视频
- **用法：** 由其他脚本调用
- **规则：** 4次图片 : 1次视频

---

#### 📤 发送消息类：

##### `send-message.sh`
- **功能：** 发送消息到各平台（飞书、Telegram 等）
- **用法：** `./scripts/send-message.sh "消息内容" [目标用户ID]`
- **支持平台：** 飞书、Telegram、Discord、WhatsApp 等

##### `send-feishu-video.sh`
- **功能：** 发送视频到飞书
- **用法：** `./scripts/send-feishu-video.sh <视频路径> <消息> [目标用户ID]`

##### `proactive-message.sh`
- **功能：** 🤖 主动发送消息（用于定时推送）
- **用法：** `./scripts/proactive-message.sh <话题类型>`
- **话题类型：**
  - `morning` - 早安问候
  - `evening` - 晚间问候
  - `miss` - 表达想念
  - `invite` - 约会邀请
  - `random` - 随机话题

---

#### ⏰ 定时推送类：

##### `hourly-push.sh`
- **功能：** 单次定时推送（生成并发送视频+消息）
- **用法：** `./scripts/hourly-push.sh`
- **流程：**
  1. 从场景库随机选择场景
  2. 使用 Vidu q2 生成场景图片
  3. 使用 Vidu q3 将图片转为4秒视频
  4. 发送视频 + 消息

##### `push-daemon.sh`
- **功能：** 守护进程，管理定时推送
- **用法：**
  ```bash
  ./scripts/push-daemon.sh start   # 启动守护进程
  ./scripts/push-daemon.sh stop    # 停止守护进程
  ./scripts/push-daemon.sh status  # 查看状态
  ./scripts/push-daemon.sh log     # 查看日志
  ./scripts/push-daemon.sh test    # 测试推送
  ```
- **特点：**
  - 每小时整点自动推送
  - 自动重启（如果崩溃）
  - 日志记录
  - 防止重复推送

---

### 5. `/templates` - 模板文件夹

**功能：** 存放模板文件

#### 文件说明：
- `character-template.md` - 角色设定模板
  - 包含角色设定的所有维度
  - 用于快速创建新角色

---

## 🔄 工作流程

### 创建新角色流程：

```
1. 用户请求创建角色
   ↓
2. setup-character.sh
   - 创建角色设定文档（references/current-character.md）
   - 搜索角色照片（scripts/search-images-tavily.mjs）
   - 下载照片到 assets/photos/
   ↓
3. generate-character-sheet.sh
   - 生成三视图（assets/character-three-view-*.png）
   ↓
4. 用户确认满意
   ↓
5. 生成打招呼图片（assets/greeting.png）
   ↓
6. 配置定时推送（config/push-config.json）
   - 启动守护进程（scripts/push-daemon.sh）
```

### 日常使用流程：

```
用户请求 → 生成图片/视频 → 发送给用户
           ↓
    generate-image.sh / generate-video.sh
           ↓
    send-message.sh / send-feishu-video.sh
```

### 定时推送流程：

```
守护进程（push-daemon.sh）
   ↓
每小时整点 → hourly-push.sh
   ↓
选择场景（references/daily-scenes.md）
   ↓
生成图片/视频
   ↓
发送消息（proactive-message.sh + send-feishu-video.sh）
```

---

## ⚠️ 重要说明

### 已删除的重复文件：

1. **备份文件：**
   - `*.bak`, `*.bak2`, `*.final` - 都是开发过程中的备份文件
   - 已删除，保留最新版本

2. **重复的旧脚本：**
   - `search-images.sh` - 旧版本，已被 `search-images-tavily.mjs` 替代
   - `search-photos.sh` - 功能重复
   - `download-photos.sh` - 已集成到 `search-images-tavily.mjs`
   - `auto-fetch-photos.sh` - 旧版本

3. **无用文件：**
   - `cron-push.sh` - 已被 `push-daemon.sh` 替代（守护进程更可靠）
   - `assets/*.txt` - 临时文件，无用

---

## 📊 文件统计

### 清理前：
- 总文件数：约 35 个
- 包含备份文件：7 个
- 包含重复脚本：4 个

### 清理后：
- 总文件数：24 个
- 无备份文件
- 无重复脚本
- 结构清晰，功能明确

---

## 🎯 核心文件清单

**必须保留的核心文件：**

1. **文档类：**
   - SKILL.md - 主文档
   - QUICKSTART.md - 快速开始

2. **脚本类：**
   - search-images-tavily.mjs - 搜索照片
   - setup-character.sh - 初始化角色
   - generate-image.sh - 生成图片
   - generate-video.sh - 生成视频
   - push-daemon.sh - 守护进程

3. **模板类：**
   - character-template.md - 角色模板

4. **配置类：**
   - push-config.json - 推送配置

**可选文件：**
- assets/ 目录下的图片（可以删除后重新生成）
- references/current-character.md（创建新角色时会被覆盖）

---

## 📝 维护建议

1. **定期清理 assets/ 目录：**
   - 删除不需要的旧图片
   - 保留最新的三视图和打招呼图片

2. **备份重要文件：**
   - references/current-character.md - 角色设定
   - config/push-config.json - 推送配置

3. **更新场景库：**
   - 定期更新 references/daily-scenes.md
   - 添加新的场景和话题

4. **监控守护进程：**
   - 使用 `push-daemon.sh status` 检查状态
   - 使用 `push-daemon.sh log` 查看日志

---

生成时间：2026-03-18
版本：v1.0-clean
