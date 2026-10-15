# Giai đoạn 7 — Dựng phim bằng ffmpeg

## Mục đích
Nối các clip thành 1 phim hoàn chỉnh, mix VO đúng timecode, xuất file cuối đạt chuẩn.

## Bước 1 — Kiểm tra audio gốc của clip
```bash
ffprobe -v error -show_entries stream=index,codec_type -of csv <clip.mp4>
```
- Clip có audio nền (tiếng gió, nhạc...) → **giữ lại**, duck nhỏ dưới VO.
- Clip im lặng → mix VO trực tiếp.

## Bước 2 — Normalize tất cả clip về cùng chuẩn
Độ phân giải theo tỷ lệ đã khóa ở Giai đoạn 0: 16:9 → 1280×720; 9:16 → 720×1280.
```bash
# 16:9:
ffmpeg -i <clip>.mp4 -vf "scale=1280:720,fps=24" \
  -c:v libx264 -pix_fmt yuv420p -c:a aac -ar 48000 <clip>_norm.mp4
# 9:16:
ffmpeg -i <clip>.mp4 -vf "scale=720:1280,fps=24" \
  -c:v libx264 -pix_fmt yuv420p -c:a aac -ar 48000 <clip>_norm.mp4
```
Tất cả clip phải cùng 1280×720, 24fps, audio AAC 48kHz trước khi nối.

## Bước 3 — Nối các cảnh
```bash
# list.txt: mỗi dòng: file '<clip>_norm.mp4' theo thứ tự cảnh 1→N
ffmpeg -f concat -safe 0 -i list.txt -c copy joined.mp4
```
Nhờ luật match-cut (frame cuối N = frame đầu N+1) nên các mối nối gần như vô hình. Nếu thấy frame trùng lặp quá lâu ở mối nối, trim bớt bằng `-ss`/`-t` trước khi nối.

## Bước 4 — Mix VO vào đúng timecode
Cảnh N (mỗi cảnh D giây) → VO đặt ở offset = (N-1)×D + 1 giây:
```bash
ffmpeg -i joined.mp4 -i vo_canh1.mp3 -i vo_canh2.mp3 \
 -filter_complex "[1:a]adelay=1000|1000[a1];[2:a]adelay=11000|11000[a2]; \
 [0:a][a1][a2]amix=inputs=3:duration=first:normalize=0[a]" \
 -map 0:v -map "[a]" -c:v copy -c:a aac final.mp4
```
(`adelay` tính bằng mili-giây: cảnh 2 bắt đầu giây 11 → delay 11000.)

## Bước 5 — Verify file cuối
```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate -of default=noprint_wrappers=1 final.mp4
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 final.mp4
```
Checklist: 1280×720 ✓, 24fps ✓, có cả video + audio stream ✓, tổng thời lượng = N×D ✓. Xem lại 1 lượt từ đầu đến cuối trước khi giao.
