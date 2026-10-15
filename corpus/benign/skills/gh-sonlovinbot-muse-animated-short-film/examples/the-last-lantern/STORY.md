# STORY BIBLE — "The Last Lantern" · Ngọn Đèn Cuối Cùng

> Ví dụ cấu trúc `STORY.md` (Giai đoạn 2 trong `SKILL.md`). Nội dung dựng lại từ [`MEGA_PROMPTS.md`](MEGA_PROMPTS.md) của dự án thật — dùng làm khuôn khi chốt kịch bản với người xem.

## Thông số đã chốt ở Giai đoạn 0

| Mục | Giá trị |
|---|---|
| Thời lượng | ≈ 85–90 giây → **8 cảnh** (~10–12 giây/cảnh) |
| Ngôn ngữ thuyết minh | Tiếng Anh (bản phát hành có thuyết minh Việt – Anh, xem [`VO_SCRIPT.md`](VO_SCRIPT.md)) |
| Tỷ lệ khung hình | **16:9**, 1280×720 — mọi character sheet và keyframe đều 16:9 |

## Logline

Ở vương quốc Solmar — thành phố của những chiếc đèn lồng — ngọn đèn lớn nhất đã tắt suốt mười năm. Cậu bé thắp đèn Milo tìm thấy Ember, đốm lửa cuối cùng hoá thành chú cáo nhỏ, và cùng công chúa Lyra (người đã không cười suốt mười năm) vượt cơn bão để thắp lại Đèn Hoàng Gia.

## Thế giới

- **Solmar:** thành phố trên vách đá, hàng trăm đèn lồng giấy ấm áp, bầu trời tím – cam lúc chạng vạng.
- **Sky Spire:** ngọn tháp cao, tối, chưa thắp — nơi treo Đèn Hoàng Gia (Royal Lantern).
- **Ngọn hải đăng cũ:** xưởng bỏ hoang, nơi đốm lửa chui vào chiếc mặt dây chuyền đồng.
- **Đồi đài thiên văn:** nơi ba nhân vật hứa với nhau.

## Character lock (chép nguyên văn vào mọi prompt)

| Nhân vật | Khoá ngoại hình | Tính cách |
|---|---|---|
| **Milo** | boy 10, messy brown hair, warm brown eyes, blue double-breasted keeper's jacket with gold buttons/trim, brown trousers, brown boots | tự tin, thân thiện, dũng cảm che chở bạn |
| **Lyra** | girl 9, silver-blonde side braid, golden star hairpin, silver tiara, moon-white dress, pale-blue starry cape | ngọt ngào, nhút nhát, can đảm; hát ru của mẹ |
| **Ember** | tiny baby fox of living golden ember-light, flame tail, big amber eyes | tinh nghịch, hay hắt xì ra tia lửa |

Model sheet: [Milo](../../docs/assets/characters/milo-sheet.jpg) · [Lyra](../../docs/assets/characters/lyra-sheet.jpg) · [Ember](../../docs/assets/characters/ember-sheet.jpg)

## Style lock

Soft 2D Disney/Pixar animation, clean rounded shapes, warm cinematic lighting, painterly rich backgrounds, 16:9, 1280×720, no text, no watermark.

## Luật continuity

- Khung cuối cảnh N = khung đầu cảnh N+1 → 9 keyframe K1…K9 cho 8 cảnh; K2…K8 dùng chung ở chỗ nối nên cắt cảnh không lộ.
- Mọi prompt có nhân vật nạp character sheet **trước**, rồi mới đến keyframe đầu/cuối.

## Luật realism đã áp dụng

- Cảnh 5: bão **xé rách đèn giấy**, lửa **chập chờn trong vỏ kính rung lắc** rồi mới tắt — không tắt "bằng phép".
- Cảnh 7: Đèn Hoàng Gia châm qua **miệng mở phía dưới và khay lửa bằng sắt**; người thắp đèn **mở cửa kính nhỏ, chạm que mồi vào bấc rồi đóng lại** — không đốt xuyên qua kính.

## Mô-típ âm nhạc

Một giai điệu hộp nhạc ru ngủ (bài hát của mẹ Lyra): mờ nhạt ở cảnh 1 → sáng dần → vỡ vụn trong bão (cảnh 5) → hiện trọn khi Lyra hát (cảnh 6) → dàn nhạc chiến thắng (cảnh 7) → piano dịu lại (cảnh 8).

## Từng cảnh

| # | Tên cảnh | Thời lượng | Khung đầu → cuối | Nhịp chính |
|---|---|---|---|---|
| 1 | The City of Fading Light | ~10 s | K1 → K2 | Toàn cảnh Solmar, Milo thắp đèn, đốm lửa vàng rơi xuống |
| 2 | The Last Ember | ~10 s | K2 → K3 | Đốm lửa vào hải đăng, chui vào mặt dây chuyền, hoá thành Ember |
| 3 | The Silent Princess | ~10 s | K3 → K4 | Lyra theo ánh sáng, Ember hắt xì tia lửa, Lyra bật cười sau 10 năm |
| 4 | Promise Under the Stars | ~10 s | K4 → K5 | Ngoéo tay "We will light the sky again", gió nổi lên |
| 5 | The Storm | ~12 s | K5 → K6 | Bão tắt mọi ngọn đèn; Milo ôm Ember trong áo khoác |
| 6 | The Climb | ~12 s | K6 → K7 | Leo cầu thang xoắn, Lyra cất tiếng hát, lửa Ember sáng lại |
| 7 | The Royal Lantern Rises | ~12 s | K7 → K8 | Ember trao ngọn lửa tim, Đèn Hoàng Gia bay lên, cả thành phố sáng lại |
| 8 | Dawn | ~10 s | K8 → K9 | Lễ hội ánh sáng, Ember thành chòm sao hình cáo, tựa phim |

Prompt chi tiết từng cảnh: [`MEGA_PROMPTS.md`](MEGA_PROMPTS.md).
