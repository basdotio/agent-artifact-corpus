# Giai đoạn 5 — Generate video từng cảnh

## Mục đích
Biến mỗi mega prompt thành 1 video clip (first frame → last frame), rồi kiểm tra chất lượng trước khi dựng.

## Câu lệnh
```bash
/opt/hatch/bin/media-generation --media-subagent-output-type video \
  --orientation <landscape | vertical> \
  --image-file <character-sheet-1.webp> \
  --image-file <character-sheet-2.webp> \
  --image-file <K-first-frame.webp> \
  --last-frame-image <K-last-frame.webp> \
  --output-dir <project>/videos \
  --timeout-secs 600 \
  "<mega prompt của cảnh>"
```
- `--orientation`: **landscape** nếu dự án khóa 16:9, **vertical** nếu khóa 9:16. Không bao giờ để mặc định khi đã khóa tỷ lệ.
- `--image-file`: nạp được nhiều file — character sheet LUÔN đứng trước keyframe. Tất cả ref phải cùng tỷ lệ đã khóa (STRICT ASPECT RATIO LOCK).
- `--last-frame-image`: frame đích để video "đi tới".
- `--timeout-secs`: video generate lâu, đặt timeout lớn (VD: 600).

## Verify từng clip (bắt buộc, không bỏ qua)
1. **Kỹ thuật:** `ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,duration -of default=noprint_wrappers=1 <file>`
   → phải đúng tỷ lệ đã khóa (16:9 hoặc 9:16), đủ thời lượng mong muốn (~10s/clip).
2. **On-model:** xem frame đầu/giữa/cuối — nhân vật có khớp character sheet không? Lệch → generate lại (giữ nguyên prompt, hoặc siết character lock chặt hơn).
3. **Continuity:** frame cuối clip N đặt cạnh frame đầu clip N+1 — phải gần như trùng nhau (match-cut). Lệch nhiều → generate lại 1 trong 2 clip.
4. **Âm thanh gốc:** `ffprobe -show_streams` xem clip có audio stream không — ghi nhận để quyết định ở giai đoạn 7 (giữ + duck dưới VO, hay clip im lặng).

## Mẹo thực tế
- Generate các cảnh độc lập có thể chạy song song (mỗi cảnh 1 lệnh riêng).
- Đừng cố sửa 1 clip quá 2–3 lần — nếu vẫn lệch, quay lại sửa mega prompt (thường do MOTION mô tả mơ hồ hoặc thiếu character lock).
