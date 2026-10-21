# 分段生成 → 拼接 → 验证工作流

## 拆段
- 按节拍拆，每段 ≤10 秒，每段 2-3 个镜头。
- 每段提示词段首声明接续关系（见 prompt-template.md 多段模板）。

## 生成
- 第 1 段正常生成，记下返回的 `snapshot_id`。
- 第 N+1 段传入 `resume_from_snapshot_id = 第 N 段的 snapshot_id`，不重传参考图。
- 确认每段尺寸一致（ffprobe 查 width/height），不一致不拼。

## 拼接
```bash
cd <实验目录>
printf "file 'seg1.mp4'\nfile 'seg2.mp4'\nfile 'seg3.mp4'\n" > concat-list.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i concat-list.txt -c copy <成片名>-full.mp4
ffprobe -v error -show_entries stream=duration -of default=noprint_wrappers=1 <成片名>-full.mp4
```
- 同编码同尺寸时 `-c copy` 无损快拼；有一段尺寸不同则先统一转码再拼。

## 验证
- 每段 `bin/extract_frames.py <段文件> 3` 抽 3 帧看：人物/服装/场景是否吃进提示词。
- 全片在每个段交界 ±1 秒、每个关键节拍点抽帧：查换脸、服装跳变、场景断裂。
- 写结论：吃进项 / 偏差项 / 偏差原因推测；音频与动态细节列入"待用户终验"。

## 交付
- 分段文件保留（用户可能要单看某段），拼接成片为主交付。
- 统一放在 `workspace/prompt-experiments/<日期>/`，命名：`<主题>-segN.mp4` / `<主题>-full.mp4`。
