# Bài học xương máu (từ dự án "The Last Lantern")

Đọc trước khi bắt đầu pipeline mới. Mỗi bài học dưới đây đều đã "trả giá" bằng giờ generate lại.

## 1. Chốt kịch bản trước, vẽ sau
Đổi 1 chi tiết kịch bản sau khi đã generate = làm lại keyframes + video của mọi cảnh liên quan. STORY.md phải được user duyệt cứng (giai đoạn 2) rồi mới vẽ. Không có "sửa nhỏ thôi".

## 2. Mô tả nhân vật càng chi tiết, càng ít lệch
"Chàng trai mặc áo xanh" sẽ cho ra 8 phiên bản áo xanh khác nhau. "Blue double-breasted keeper's jacket with gold buttons and gold trim, brown trousers, brown boots" mới khóa được. Màu sắc + từng món đồ phải có tên gọi cụ thể trong character lock.

## 3. Character sheet luôn đứng đầu danh sách ref
Thứ tự nạp ref ảnh hưởng trực tiếp đến độ on-model. Sheet nhân vật trước, keyframe sau. Đảo thứ tự là nhân vật bắt đầu "trôi".

## 4. Realism: kiểm tra từng động từ trong MOTION
Bài học lớn nhất dự án: user phát hiện prompt viết "thắp đèn" trong khi đèn còn khung kính đóng kín — phi thực tế. Từ đó mọi prompt đều phải trả lời: "ngoài đời nó diễn ra đúng như vậy không?" Mở cửa kính → châm bấc → đóng cửa. Gió dập lửa → xé đèn giấy / lửa chập chờn trong housing rung. Viết prompt như một đạo diễn hiểu vật lý, không phải nhà thơ.

## 5. Match-cut miễn phí nhưng phải thiết kế từ đầu
Last frame N = first frame N+1 nghe đơn giản, nhưng chỉ hoạt động khi keyframes được vẽ đúng luật từ giai đoạn 3. Không thể "fix ở khâu dựng" — dựng chỉ nối, không tạo được continuity.

## 6. Đừng generate lại 1 clip quá 3 lần
Nếu clip vẫn lệch sau 2–3 lần thử, vấn đề nằm ở mega prompt (MOTION mơ hồ, thiếu character lock, hoặc yêu cầu phi thực tế), không phải ở may rủi. Quay lại sửa prompt.

## 7. Kiểm tra audio gốc trước khi mix
Đừng giả định clip generate ra là im lặng. Có clip mang sẵn tiếng gió/nhạc nền — xóa đi thì phí, giữ lại thì phải duck dưới VO. Quyết định này cần dữ kiện từ ffprobe, không phải từ suy đoán.

## 8. Normalize trước khi nối, không bao giờ nối trước normalize
Trộn clip 1248×704 với 1280×720 trong 1 lệnh concat = lỗi hoặc méo hình. Chuẩn hóa tất cả về cùng độ phân giải/fps/codec trước.

## 9. VO là gia vị, không phải món chính
Phim 80 giây chỉ cần ~45 giây VO. Khoảng lặng cho hình ảnh và nhạc thở mới là thứ khiến VO đắt giá. Cảnh đỉnh cảm xúc: cho moment tự lên tiếng, VO rút lui.

## 10. Đặt tên file có ý nghĩa từ ngày đầu
`scene1-fading-light.mp4` chứ không phải `media-generation-...-uuid.mp4`. Đến lúc có 30+ file trong folder, bạn sẽ cảm ơn chính mình.

## 11. Khóa tỷ lệ khung hình từ câu hỏi đầu tiên
16:9 hay 9:16 không phải chuyện "để sau tính" — nó quyết định toàn bộ ref đầu vào. Một character sheet vẽ 16:9 đem đi generate video 9:16 sẽ cho ra bố cục vỡ. Hỏi và khóa ngay ở Giai đoạn 0, dán STRICT ASPECT RATIO LOCK vào mọi prompt.
