# Giai đoạn 4 — Mega Prompt từng cảnh

## Mục đích
Viết 1 prompt "copy-paste là chạy" cho mỗi cảnh, gom đủ: style lock, character lock, camera, hành động, âm thanh, nhạc, VO, first/last frame. Viết kỹ ở đây thì video generate ra ít phải sửa.

## Cấu trúc mega prompt (tiếng Anh)
```
<Style lock>, 16:9.
FIRST FRAME: <mô tả frame đầu = keyframe đầu>
MOTION: <diễn biến hành động trong cảnh — viết từng bước theo trình tự thời gian>
CAMERA: <chuyển động camera: push-in, orbit, aerial follow...>
LAST FRAME: match <keyframe cuối>
SOUND: <tiếng động chi tiết: gió, bước chân, lửa crackle...>
MUSIC: <diễn biến nhạc trong cảnh>
VO (warm narrator): "<câu VO từ STORY.md>"
```

## Global locks (dán đầu mọi prompt)
```
Soft 2D Disney/Pixar animation, clean rounded shapes, warm cinematic lighting,
painterly rich backgrounds, [16:9 landscape 1280x720 | 9:16 vertical 720x1280],
no text, no watermark.
STRICT ASPECT RATIO LOCK: the output MUST be exactly [16:9 | 9:16] — the same
ratio locked in project intake. All attached references already share this
ratio; never introduce a mismatched one.
<Character lock chép nguyên văn từ STORY.md cho nhân vật xuất hiện trong cảnh>
Keep every character exactly on-model with the attached sheets in all frames.
```

## Thứ tự nạp ref (bắt buộc)
1. Character sheet của nhân vật trong cảnh (MILO_SHEET, LYRA_SHEET...)
2. Keyframe first frame
3. Keyframe last frame
→ Rồi mới đến prompt text.

## ⚠️ Luật realism (đọc kỹ trước khi viết MOTION)
Mọi hành động vật lý nhỏ phải đúng cơ chế thực tế. Ví dụ đã gặp trong dự án thật:
- Thắp đèn có khung kính: **mở cửa/panel kính → đưa bấc vào chạm tim đèn → đóng cửa lại**. Không viết "châm lửa xuyên qua kính".
- Bão dập lửa: gió **xé rách đèn giấy**, lửa **chập chờn trong housing kính rung lắc rồi tắt**.
- Đèn lớn châm lửa: qua **miệng mở phía dưới** và **khay lửa sắt** — nhân vật bay/chui qua miệng đèn vào khay trước khi đèn bùng cháy.
Kiểm tra từng động từ trong MOTION: "nó có thể xảy ra như vậy ngoài đời không?" Nếu không → viết lại.

## Checklist
- [ ] Mỗi cảnh 1 mega prompt đầy đủ 7 mục (FIRST FRAME → VO)
- [ ] Character lock + style lock có mặt trong mọi prompt
- [ ] Thứ tự ref đúng: sheet → first frame → last frame
- [ ] MOTION đã rà soát realism, không có hành động phi logic
