# Giai đoạn 2 — Thảo luận & Chốt kịch bản (Story Bible)

## Mục đích
Biến ý tưởng mơ hồ của user thành một **Story Bible** duy nhất, chốt cứng mọi thứ trước khi vẽ một nét nào. Đây là "hiến pháp" của phim — mọi prompt sau này đều trích từ đây.

## Lưu ý từ Giai đoạn 0
- Số cảnh đã chốt từ công thức thời lượng (thời lượng ÷ 10, làm tròn lên). Không hỏi lại "mấy cảnh" — chỉ xác nhận.
- Ngôn ngữ thảo luận và VO = ngôn ngữ đã chọn ở Giai đoạn 0.

## Prompt thảo luận (hỏi user, từng câu một, ngắn gọn)
1. Phim về ai? (nhân vật chính, tuổi, tính cách, ngoại hình)
2. Câu chuyện một câu là gì? (logline: ai + muốn gì + vật cản + cái giá)
3. Thế giới diễn ra ở đâu? Phong cách hình ảnh? (VD: 2D Disney/Pixar, anime, 3D...)
4. Mấy cảnh? Mỗi cảnh bao lâu? (gợi ý: 8 cảnh × 10 giây = phim ~80 giây)
5. VO ngôn ngữ gì? Giọng kể chuyện hay nhân vật tự thoại?
6. Nhạc: có motif chủ đạo không? (VD: bài hát ru → full orchestra ở cao trào)
7. Cảm xúc từng cảnh đi lên hay xuống? Đâu là đỉnh cảm xúc?

## Template STORY.md (viết xong đưa user duyệt)
```markdown
# <TÊN PHIM> — Story Bible
*Dòng mô tả: phong cách, số cảnh, ngôn ngữ VO*

## Logline
<1 câu>

## Characters (CANONICAL LOCK — chép nguyên văn vào mọi prompt)
- **<TÊN> (tuổi, vai):** <mô tả ngoại hình chi tiết + tính cách + arc>

## World & Style Lock
<Thế giới, phong cách hình ảnh, 16:9 1280x720, âm thanh, nhạc, VO>

## Continuity Rule
**Last frame of Scene N = first frame of Scene N+1 (match cut).**

### Scene N — "<Tên cảnh>"
- Beat: <cảm xúc chủ đạo>
- First frame: <mô tả>
- Last frame: <mô tả> (= first frame cảnh N+1)
- VO: "<câu thoại>"
- Music: <diễn biến nhạc>
```

## Quy tắc chốt
- Phần **Characters (CANONICAL LOCK)** phải viết đủ chi tiết để paste nguyên văn vào prompt mà không cần sửa.
- Mỗi cảnh bắt buộc có first frame + last frame mô tả rõ — đây là nguyên liệu cho keyframes ở giai đoạn 3.
- VO mỗi cảnh chỉ 1–2 câu, đơn giản, quốc tế (dễ dịch).
- User duyệt STORY.md xong mới sang giai đoạn 3. Đổi kịch bản sau khi đã vẽ = làm lại từ đầu.
