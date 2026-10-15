---
name: "animated_short_film"
description: "Skill dựng phim hoạt hình ngắn từ đầu đến cuối trên Muse AI: thu thập yêu cầu (thời lượng, ngôn ngữ, tỷ lệ khung hình), vẽ character sheets, chốt kịch bản story bible, keyframes, mega prompt từng cảnh, generate video, làm VO, dựng phim bằng ffmpeg. Tác giả: Đặng Hữu Sơn. Dùng khi user muốn làm phim hoạt hình ngắn từ con số 0 trên Muse AI."
---

# Animated Short Film Pipeline (Muse AI)

**Tác giả:** Đặng Hữu Sơn
**Mô tả:** Skill dựng phim hoạt hình ngắn từ đầu đến cuối trên Muse AI — từ một ý tưởng thô thành file MP4 hoàn chỉnh: nhân vật, kịch bản, hình ảnh, video, thuyết minh và dựng phim.

## Purpose
Dẫn dắt toàn bộ quy trình sản xuất một phim ngắn hoạt hình 2D trên Muse AI — từ ý tưởng đến file MP4 hoàn chỉnh — theo pipeline đã kiểm chứng trong dự án "The Last Lantern" (8 cảnh, nhân vật on-model, match-cut liền mạch).

## Giai đoạn 0 — Thu thập đầu vào (BẮT BUỘC, hỏi trước mọi thứ)
Hỏi user 3 câu dưới đây trước khi làm bất cứ việc gì. Chưa có đáp án thì chưa sang giai đoạn 1.

### 1. Thời lượng phim mong muốn là bao lâu?
- Mỗi clip video generate ra dài khoảng **10 giây** (chuẩn của media-generation).
- **Số cảnh = làm tròn lên (thời lượng mong muốn ÷ 10).**
- Ví dụ:
  - Muốn phim ~60 giây → 60 ÷ 10 = **6 cảnh**
  - Muốn phim ~80 giây → 80 ÷ 10 = **8 cảnh**
  - Muốn phim ~45 giây → 4,5 → **5 cảnh** (tổng 50 giây, cắt gọn ở khâu dựng) hoặc giảm còn 4 cảnh
- Chốt con số cảnh với user ngay tại bước này — mọi giai đoạn sau đều dựa vào con số này.

### 2. Ngôn ngữ chính là gì?
- **Tiếng Việt / Tiếng Anh / ngôn ngữ khác** (theo yêu cầu của user).
- Ngôn ngữ đã chọn quyết định: ngôn ngữ VO, ngôn ngữ của VO_SCRIPT.md, và ngôn ngữ dùng khi thảo luận kịch bản với user.

### 3. Tỷ lệ khung hình: 16:9 (ngang) hay 9:16 (dọc)?
- Đây không chỉ là lựa chọn output — nó **ràng buộc toàn bộ ref đầu vào**.
- ⚠️ RÀNG BUỘC MẠNH — dán nguyên văn (tiếng Anh) vào mọi prompt generate ảnh/video của dự án:
  > **STRICT ASPECT RATIO LOCK:** The final output video MUST be **[16:9 landscape | 9:16 vertical — chọn 1]**. All reference images — character sheets, context sheets, keyframes, first-frame and last-frame images — MUST share this exact aspect ratio. Reference images are not only style and character guides; they directly condition the output framing and composition. Any reference image with a mismatched aspect ratio MUST be regenerated or cropped to the locked ratio before use. NEVER mix aspect ratios within a single project.
- CLI `media-generation`: 16:9 → `--orientation landscape`; 9:16 → `--orientation vertical`.
- Verify bằng ffprobe ở mọi giai đoạn: sai tỷ lệ = làm lại ngay, không để lọt xuống giai đoạn sau.

## Workflow
Làm theo đúng thứ tự 7 giai đoạn. Mỗi giai đoạn có prompt mẫu và checklist trong `references/`. Không bỏ qua giai đoạn nào.

1. **Character sheets** → `references/01-character-sheets.md`
   Vẽ character reference sheet cho từng nhân vật theo đúng tỷ lệ đã khóa ở Giai đoạn 0 (nhiều góc + biểu cảm). Đây là "khóa nhân vật" — mọi asset sau này đều phải nạp sheet này.
2. **Thảo luận & chốt kịch bản** → `references/02-story-and-script.md`
   Hỏi user để chốt logline, nhân vật, thế giới, rồi viết **Story Bible** (`STORY.md`): character lock chép nguyên văn, style lock, luật continuity, từng cảnh (beat, first/last frame, VO, nhạc). Số cảnh = con số đã chốt ở Giai đoạn 0.
3. **Keyframes** → `references/03-keyframes.md`
   Vẽ K1..K(N+1) keyframe đúng tỷ lệ đã khóa, mỗi keyframe nạp character sheet làm ref. Keyframe cuối cảnh N = keyframe đầu cảnh N+1 (luật match-cut).
4. **Mega prompt từng cảnh** → `references/04-mega-prompts.md`
   Viết 1 mega prompt copy-paste cho mỗi cảnh: global locks (kèm STRICT ASPECT RATIO LOCK) + thứ tự nạp ref + FIRST FRAME / MOTION / CAMERA / LAST FRAME / SOUND / MUSIC / VO.
5. **Generate video** → `references/05-video-generation.md`
   Chạy `media-generation` cho từng cảnh (nạp sheet + first/last frame), verify on-model, continuity và tỷ lệ khung hình bằng ffprobe.
6. **Làm VO** → `references/06-vo-production.md`
   Viết kịch bản VO kiểu kể chuyện bằng ngôn ngữ đã chọn ở Giai đoạn 0 (không nói liên tục, ~60% thời lượng), thu bằng TTS hoặc để user thu ngoài.
7. **Dựng phim** → `references/07-assembly.md`
   Normalize về độ phân giải chuẩn của tỷ lệ đã khóa (16:9 → 1280×720; 9:16 → 720×1280), 24fps bằng ffmpeg, nối các cảnh, mix VO đúng timecode, verify file cuối.

> Trước khi bắt đầu dự án mới, đọc `references/08-lessons.md` — 10 bài học xương máu từ dự án "The Last Lantern".

## Output Contract
Kết thúc pipeline phải có:
- `STORY.md` — story bible đã chốt với user
- `character_sheets/` — sheet của mọi nhân vật, đúng tỷ lệ đã khóa
- `keyframes/` — K1..K(N+1), đúng tỷ lệ đã khóa
- `MEGA_PROMPTS.md` — mega prompt từng cảnh
- `videos/` — video từng cảnh, đã verify tỷ lệ + thời lượng
- `audio/` — VO từng cảnh (hoặc file user thu)
- `VO_SCRIPT.md` — kịch bản VO kèm timecode, đúng ngôn ngữ đã chọn
- File MP4 hoàn chỉnh: đúng tỷ lệ đã khóa, 24fps, có audio, đã verify bằng ffprobe, tổng thời lượng xấp xỉ thời lượng user yêu cầu ở Giai đoạn 0

## Operating Rules
1. **Giai đoạn 0 là bắt buộc:** không có thời lượng + ngôn ngữ + tỷ lệ khung hình thì không bắt đầu.
2. **STRICT ASPECT RATIO LOCK:** toàn bộ ref đầu vào (character sheets, context sheets, keyframes) phải cùng tỷ lệ với output. Ref sai tỷ lệ = vẽ lại, không dùng tạm.
3. **Khóa nhân vật:** mọi prompt generate ảnh/video đều phải nạp character sheet TRƯỚC TIÊN, rồi mới đến ref khác. Output lệch nhân vật = làm lại.
4. **Luật continuity:** frame cuối cảnh N = frame đầu cảnh N+1. Khi nối phim, các frame biên được share nên cut là vô hình.
5. **Luật realism (bắt buộc):** mọi hành động vật lý nhỏ trong prompt phải đúng cơ chế thực tế — mở cửa kính đèn trước khi đưa bấc vào châm lửa; bão xé rách đèn giấy / làm lửa chập chờn trong housing rung lắc; đèn lớn châm qua miệng mở phía dưới và khay lửa. Không bao giờ viết hành động phi logic (VD: đốt xuyên qua kính).
6. **Verify trước khi mix:** kiểm tra audio stream của clip gốc bằng ffprobe trước khi dựng — không giả định clip đang im lặng. Nếu có âm thanh nền thì giữ lại và duck dưới VO.
7. **Normalize trước khi nối:** mọi clip phải về cùng độ phân giải, fps trước khi concat.
8. **VO kể chuyện, không đọc liên tục:** mỗi cảnh 1–2 câu đặt đầu cảnh, chừa khoảng lặng cho hình ảnh/nhạc. Cảnh cảm xúc cao trào có thể để nhân vật "thở" thay vì VO.
9. Mọi con số user sẽ hành động theo (số cảnh, thời lượng, độ phân giải) phải lấy từ output tool thực tế hoặc từ tính toán ở Giai đoạn 0, không đoán.
