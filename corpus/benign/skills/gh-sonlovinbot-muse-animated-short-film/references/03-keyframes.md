# Giai đoạn 3 — Keyframes (Khung hình chốt)

## Mục đích
Vẽ trước các "cột mốc" hình ảnh của phim: K1..K(N+1) cho N cảnh. Keyframe = first frame và last frame của từng cảnh. Có keyframes rồi thì video chỉ việc "đi từ A đến B".

## Quy trình
1. Từ STORY.md, liệt kê K1..K(N+1): K1 = first frame cảnh 1, K2 = last frame cảnh 1 = first frame cảnh 2, ..., K(N+1) = last frame cảnh N.
2. Với mỗi keyframe, generate ảnh 16:9, **nạp character sheet của nhân vật xuất hiện trong frame làm ref trước**, rồi mới đến mô tả:
   ```
   /opt/hatch/bin/media-generation --media-subagent-output-type image \
     --orientation landscape \
     --image-file <path/character-sheet.webp> \
     --output-dir <project>/keyframes \
     "<mô tả keyframe, style lock + character lock chép từ STORY.md>"
   ```
3. Kiểm tra từng keyframe: 16:9, nhân vật on-model (so với sheet), ánh sáng/không khí đúng beat của cảnh.
4. Đặt tên file rõ ràng: `k1-city-dusk.webp`, `k2-spark-falls.webp`...

## Checklist
- [ ] Đủ K1..K(N+1), không thiếu mốc nào
- [ ] K_cuối_cảnh_N và K_đầu_cảnh_N+1 là CÙNG MỘT FILE (luật match-cut)
- [ ] Nhân vật trong keyframe khớp character sheet
- [ ] Tất cả 16:9
