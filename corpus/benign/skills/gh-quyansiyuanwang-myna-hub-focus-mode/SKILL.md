---
name: 专注模式
description: 专注模式，退出干扰类应用、开启勿扰并静音
tags: productivity, focus
---
目标：为用户进入一段不被打扰的专注工作状态。按以下步骤执行。

1. 调用 `list_running_apps` 获取当前运行的应用列表。
2. 从列表中识别干扰类应用，例如社交、视频、即时通讯类（微信、QQ、Telegram、Discord、哔哩哔哩、腾讯视频等）。保留开发工具、终端、浏览器等工作应用。
3. 对每个干扰类应用依次调用 `quit_app` 退出。若某个应用有未保存的编辑内容，先告知用户并跳过，不要强制退出。
4. 调用 `run_shortcut` 运行名为「开启勿扰模式」的快捷指令；若该快捷指令不存在（可先用 `list_shortcuts` 确认），则改用 `run_applescript` 执行
   `do shell script "defaults -currentHost write com.apple.notificationcenterui doNotDisturb -boolean true"` 并提示用户。
5. 调用 `set_volume` 将系统音量调低到 20 或静音，避免通知音打扰。
6. 可选：调用 `music_control` 播放专注类歌单，或调用 `now_playing` 确认当前播放内容。
7. 汇总执行结果：退出了哪些应用、是否开启勿扰、当前音量，用简洁中文告知用户。
8. 结束时提醒用户专注模式已开启，需要关闭时可直接说明。
