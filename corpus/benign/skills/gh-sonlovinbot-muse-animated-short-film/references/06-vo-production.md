# Giai đoạn 6 — Làm VO (thuyết minh)

## Triết lý
VO là **người kể chuyện**, không phải máy đọc. Mỗi cảnh chỉ 1–2 câu đặt ở **đầu cảnh**, rồi để khoảng lặng cho hình ảnh, tiếng động và nhạc. Tổng VO chỉ nên phủ ~50–60% thời lượng phim. Cảnh cảm xúc cao trào có thể **không cần VO** — để nhân vật/moment tự thở (VD: nhân vật cất tiếng hát sau 10 năm im lặng thì VO chỉ nói 1 câu mở rồi im hoàn toàn).

## Bước 1 — Viết VO_SCRIPT.md
Cho mỗi cảnh:
- **Timecode:** cảnh N bắt đầu ở giây (N-1)×độ-dài-cảnh. VO vào sau ~1 giây đầu cảnh, dứt trước khi hết cảnh ~2 giây.
- **2 phiên bản:** tiếng Anh + tiếng Việt (hoặc ngôn ngữ user chọn).
- **Direction:** ghi chú tone/giọng cho người thu (VD: "trầm xuống ở cuối câu", "bật cười nhẹ trong giọng").
- Dấu `...` trong script = nghỉ một nhịp (~0,5 giây).

Template 1 cảnh:
```markdown
## CẢNH N — "<Tên>" (start–end)
*VO vào lúc X, dứt trước Y.*
**EN:** <câu tiếng Anh>
**VI:** <câu tiếng Việt>
*Direction: <chỉ dẫn giọng>*
```

## Bước 2 — Thu VO
**Option A: TTS (nhanh, làm mẫu)**
```bash
/opt/hatch/bin/tts speak --voice <voice-id> --language <en|vi> \
  --output <project>/audio/vo_canhN.mp3 --text-stdin <<< "<câu VO>"
```
- Chọn voice: xem catalog `/opt/hatch/skills/voice-selector/voice_source.json` (giọng narrator ấm, kể chuyện). Voice tiếng Anh đọc tiếng Việt thường không chuẩn bằng voice bản xứ — nghe thử trước.
- Truyền text qua `--text-stdin`, không paste vào argument.
- Kiểm tra thời lượng: `ffprobe -show_entries format=duration` — câu VO phải ngắn hơn thời lượng cảnh.

**Option B: User thu ngoài (chất lượng cao)**
- Đưa user VO_SCRIPT.md + spec: WAV 48kHz, thu không nhạc nền, đọc 2–3 take mỗi câu.
- Có thể đưa file TTS mẫu để user tham khảo nhịp đọc.

## Checklist
- [ ] VO_SCRIPT.md đủ 2 ngôn ngữ + timecode + direction
- [ ] Mỗi file VO ngắn hơn cảnh chứa nó
- [ ] Đã nghe thử toàn bộ, không có câu nào bị ngắt cụt
