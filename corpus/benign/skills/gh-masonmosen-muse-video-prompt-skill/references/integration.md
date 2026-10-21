# CueShot 链路集成

本 skill 与 Mason 自研的两个 CueShot skill 组成完整链路：

```
cinematic-shot-design（生成前）
  场景/情绪 → 导演风格匹配 → 镜头决策 → 可执行 prompt
  （单镜头默认；2-3 镜仅用于 reveal-reaction-action 链、 confrontation、
   有意义的环境揭示、地点/时间变化）
        │
        ▼
muse-video-prompt-skill（生成中）← 本 skill
  六段式模板归位 → media.generate_video → 多段 snapshot 接续 → ffmpeg 拼接
        │
        ▼
ai-director-video-review（生成后）
  single / variants / sequence 三模式
  → 技术完整性 + 连续性 + 生成痕迹检查
  → 发布结论（ready / post_fix / regenerate_segment / reject）
  → 最小返修方案（定位到具体时间段，如"以 00:03.2 为参考重生成 00:04.2–00:05.8"）
```

## 衔接规则
- cinematic-shot-design 的输出 prompt 按本 skill 六段式模板字段归位后，再交用户定稿。
- 审片时把提示词、分镜、参考图和创作意图一起给 ai-director-video-review，避免把有意的叙事变化误判为连续性错误。
- 返修结论若要求"局部重生成"，回到本 skill 第 3 步，只重跑该段（snapshot 接续该段的前一段）。
- 观察与推断分离：审片报告里无法确认的不写成事实，标待确认。
