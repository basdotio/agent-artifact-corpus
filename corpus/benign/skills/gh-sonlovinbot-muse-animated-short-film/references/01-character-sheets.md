# Giai đoạn 1 — Character Sheets (Khóa nhân vật)

## Mục đích
Tạo "chứng minh thư" hình ảnh cho từng nhân vật. Từ đây về sau, mọi ảnh/video đều phải nạp sheet này để nhân vật không bị lệch (on-model).

## ⚠️ Tỷ lệ khung hình (từ Giai đoạn 0)
Character sheet PHẢI vẽ đúng tỷ lệ đã khóa — 16:9 hay 9:16. Sheet không chỉ là tham chiếu style/nhân vật, nó còn định hình trực tiếp output video. Dán STRICT ASPECT RATIO LOCK vào prompt. CLI: 16:9 → `--orientation landscape`; 9:16 → `--orientation vertical`.

## Prompt mẫu (dùng cho từng nhân vật, prompt tiếng Anh)
```
Character reference sheet, [16:9 landscape | 9:16 vertical] orientation, soft 2D Disney/Pixar
animation style, clean rounded shapes, warm cinematic lighting.
STRICT ASPECT RATIO LOCK: the sheet MUST be exactly [16:9 | 9:16]. This sheet
will directly condition video output framing — no other ratio is acceptable.
Character: [MÔ TẢ CHI TIẾT: tuổi, giới tính, tóc, mắt, trang phục từng món,
màu sắc chính xác, phụ kiện, đặc điểm nhận dạng]
Show: front view, side view, back view, 3/4 view, plus 3 expression close-ups
(happy, sad, determined). Same outfit and colors in every view, consistent
proportions. Plain soft neutral background, no text, no watermark.
```

## Quy trình
1. Viết mô tả nhân vật thật cụ thể (màu áo, kiểu tóc, phụ kiện) — càng chi tiết càng khó lệch về sau. Hỏi user chốt mô tả trước khi vẽ.
2. Generate bằng CLI:
   ```
   /opt/hatch/bin/media-generation --media-subagent-output-type image \
     --orientation landscape --output-dir <project>/character_sheets \
     "<prompt trên>"
   ```
3. Kiểm tra: đúng 16:9 (dùng `ffprobe` hoặc xem ảnh), các góc có đồng nhất trang phục/màu sắc không. Chưa đạt → sửa prompt, vẽ lại.
4. Lưu sheet với tên rõ ràng: `milo-sheet-16x9.webp`, `lyra-sheet-16x9.webp`...

## Checklist trước khi sang giai đoạn 2
- [ ] Mỗi nhân vật chính đều có sheet 16:9 riêng
- [ ] Mô tả nhân vật đã được user chốt (không đổi giữa chừng)
- [ ] Sheet đủ các góc nhìn + biểu cảm, nền trơn, không chữ
