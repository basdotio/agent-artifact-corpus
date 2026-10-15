---
name: bug-hunt
description: Bir hatayı tahminle değil kanıtla ayıklar; yeniden üretir, kök nedeni bulur, düzeltir ve düzeltmeyi testle kanıtlar. Kullanıcı "şu hata oluyor", "neden çalışmıyor", "bug'ı bul" dediğinde kullan.
---

# Hata Avı

Kural: **Kanıt olmadan düzeltme yok.** Tahmin edip kod değiştirmek, yeni hata üretmenin en hızlı yoludur.

## 1. Belirtiyi netleştir

- Beklenen davranış ne, gerçekleşen ne? Tam hata mesajı ve yığın izi (stack trace) nedir?
- Ne zaman başladı? `git log` ile şüpheli değişikliklere bak; gerekiyorsa `git bisect` öner.

## 2. Yeniden üret

- Hatayı tetikleyen en küçük adımı ya da girdiyi bul.
- Mümkünse hatayı **başarısız olan bir test** olarak yaz. Bu test hem kanıt hem de düzeltmenin ölçütüdür.
- Yeniden üretemiyorsan dur ve kullanıcıdan eksik bilgiyi iste; körlemesine düzeltmeye geçme.

## 3. Kök nedeni bul

- Veri akışını hatanın görüldüğü yerden geriye doğru izle.
- Her adımda bir hipotez kur, tek bir kontrolle (log, assert, küçük deney) doğrula ya da ele.
- Belirtiyi değil nedeni hedefle: bir `null` kontrolü eklemek, değerin neden `null` geldiğini açıklamaz.

## 4. Düzelt ve kanıtla

- Kök nedeni gideren en küçük değişikliği yap.
- 2. adımdaki test artık geçmeli; mevcut testlerin tamamı da geçmeli.
- Aynı hatanın başka yerde olup olmadığını ara.

## 5. Raporla

```
Belirti: ...
Kök neden: ... (dosya:satır)
Düzeltme: ...
Kanıt: <test adı> önce kırmızı, şimdi yeşil
```
