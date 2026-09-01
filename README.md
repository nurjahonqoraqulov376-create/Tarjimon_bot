# 🌐 Tarjimon Bot — uz / ru / en / ar / fr / de

Telegram bot: **qaysi tilda yozsangiz ham**, javobda **oltala tildagi** tarjima
chiqadi. Ovozli xabar yuborsangiz — avval matnga o'giradi, keyin tarjima qiladi.

```
Siz:  Salom, qalaysan?

Bot:  🇺🇿 O'zbekcha · asl matn
      Salom, qalaysan?

      🇷🇺 Русский
      Привет, как дела?

      🇬🇧 English
      Hello, how are you?

      🇸🇦 العربية
      مرحبا، كيف حالك؟

      🇫🇷 Français
      Bonjour comment allez-vous ?

      🇩🇪 Deutsch
      Hallo, wie geht es dir?
```

## Imkoniyatlar

- 🔄 **Avtomatik til aniqlash** — manba tilni ko'rsatish shart emas
- 🌍 **Oltala tilda javob** — uz, ru, en, ar, fr, de bir xabarda
- 🎤 **Ovozli xabar** — faster-whisper orqali matnga o'girib tarjima qiladi
- 🇺🇿🇷🇺🇬🇧🇸🇦🇫🇷🇩🇪 **Interfeys tili** — menyu va xabarlar siz tanlagan tilda
- 💾 **SQLite** — sozlamalar bot qayta ishga tushsa ham saqlanadi
- 💰 **Bepul tarjima** — API kaliti va to'lov kerak emas (deep-translator)

## Buyruqlar

| Buyruq | Vazifasi |
|---|---|
| `/start` | Botni ishga tushirish va til tanlash |
| `/til` | Interfeys tilini o'zgartirish (`/lang` ham ishlaydi) |
| `/help` | Yordam |
| `/stats` | Statistika va xotira sarfi (faqat admin uchun) |

---

## Lokalda ishga tushirish

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

copy .env.example .env          # Linux/Mac: cp .env.example .env
# .env faylini ochib BOT_TOKEN ni qo'ying

python bot.py
```

Token [@BotFather](https://t.me/BotFather) dan olinadi (`/newbot`).
Admin ID ni [@userinfobot](https://t.me/userinfobot) aytadi.

Birinchi ovozli xabarda Whisper modeli internetdan yuklab olinadi (~150 MB) —
faqat bir marta.

### Botsiz tekshirish

```bash
python translator.py     # tarjima va til aniqlashni sinaydi
```

---

## Railway'ga joylash

### 1. Loyihani yuklash

```bash
git init
git add .
git commit -m "Tarjimon bot"
git remote add origin <sizning-repo-url>
git push -u origin main
```

Railway'da: **New Project → Deploy from GitHub repo** → shu repo'ni tanlang.
`railway.json` va `Dockerfile` avtomatik topiladi.

### 2. Volume ulash (⚠️ majburiy)

Railway'ning fayl tizimi har bir deploy'da tozalanadi. Volume'siz
foydalanuvchilar tanlagan til va statistika **har safar yo'qoladi**.

Service → **Settings → Volumes → New Volume** → Mount path: `/data`

### 3. Variables

| Nomi | Qiymati | Izoh |
|---|---|---|
| `BOT_TOKEN` | `123456:ABC-...` | BotFather'dan |
| `DB_PATH` | `/data/bot.db` | volume ichida bo'lishi shart |
| `ADMIN_ID` | `123456789` | `/stats` uchun |
| `WHISPER_MODEL` | `small` | `tiny` / `base` / `small` |
| `WHISPER_BEAM` | `5` | beam qidiruv kengligi (1 = tez, aniqligi past) |
| `WHISPER_IDLE_UNLOAD_SEC` | `300` | bo'sh turgan modelni bo'shatish |
| `MAX_VOICE_SEC` | `120` | maksimal ovoz uzunligi |
| `THROTTLE_SEC` | `1.5` | flood himoyasi |

### 4. Muhim sozlamalar

- **Replicas = 1.** Ikkita nusxa bir vaqtda `getUpdates` chaqirsa, Telegram
  `409 Conflict` qaytaradi. Bot bundan o'zi tiklanadi (~11 soniyada qayta
  ulanadi), lekin ikkita nusxa doim urishib turadi — shuning uchun 1 ta
  bo'lishi shart.
- **Sleep o'chirilgan bo'lsin.** Xizmat uxlasa polling to'xtaydi.
- **Healthcheck yoqilmasin.** Bu worker, HTTP porti yo'q.

> ⚠️ **`railway.json` eskirmoqda.** Railway Config-as-Code'ni
> **2026-12-01** da o'chiradi. Shuning uchun muhim sozlamalar Railway'ning
> **service sozlamalarida** ham o'rnatilgan (`numReplicas = 1`,
> `dockerfilePath = Dockerfile`, `sleepApplication = false`). Shu sababli
> `railway.json` yo'qolsa ham build to'g'ri ketadi — busiz Railway RAILPACK'ka
> tushib qolardi va Dockerfile'dagi ffmpeg hamda whisper modeli yo'qolardi.
>
> Railway'da Dockerfile `builder` enum qiymati emas (u faqat HEROKU / NIXPACKS
> / PAKETO / RAILPACK), Dockerfile'ni **`dockerfilePath`** belgilaydi.

---

## 💰 $5 byudjet haqida

Railway resurs bo'yicha hisoblaydi: **RAM $10/GB/oy**, **vCPU $20/vCPU/oy**.
Hobby obunasi ichida $5 lik usage bor, ya'ni RAM'ni doim band qilib turish
qimmatga tushadi.

Shuning uchun bot maxsus qilib shunday yozilgan:

- Whisper modeli **darhol yuklanmaydi** — faqat birinchi ovozli xabar kelganda
- `WHISPER_IDLE_UNLOAD_SEC` (default 5 daqiqa) davomida ishlatilmasa —
  **xotiradan bo'shatiladi** va xotira operatsion tizimga qaytariladi
- Model Docker image ichida tayyor turadi, shuning uchun qayta yuklash
  ~1.5 soniya oladi

**Railway'da `base` model bilan o'lchangan natijalar** (bo'sh turgan bot):

| Resurs | O'lchov | Oylik |
|---|---|---|
| RAM | o'rtacha **65 MB**, eng yuqori 173 MB | ~$0.64 |
| CPU | o'rtacha **0.003 vCPU** | ~$0.06 |
| **Jami** | | **~$0.70/oy** |

> ⚠️ **Default model `small` ga o'zgartirildi**, chunki `base` o'zbek nutqini
> yetarlicha aniq eshitmasdi. Bo'sh turgan botning RAM sarfi o'zgarmaydi —
> model xotirada faqat ovoz kelganda turadi va `WHISPER_IDLE_UNLOAD_SEC`
> dan keyin bo'shatiladi. Ovoz qayta ishlanayotganda RAM ~400 MB o'rniga
> ~950 MB gacha ko'tariladi, ya'ni **hisob ovozli xabarlar soniga bog'liq**.
> Ovoz juda ko'p ishlatilsa va $5 kredit yetmasa, Railway'da
> `WHISPER_MODEL=base` qo'ying yoki `WHISPER_IDLE_UNLOAD_SEC` ni kamaytiring
> (masalan `120`). `WHISPER_BEAM=1` ham CPU sarfini tushiradi, lekin
> aniqlikni pasaytiradi.

---

## Qanday ishlaydi

| Fayl | Vazifasi |
|---|---|
| [bot.py](bot.py) | Ishga tushirish, middleware'lar, polling |
| [translator.py](translator.py) | Tarjima, til aniqlash, bo'laklarga bo'lish, kesh |
| [stt.py](stt.py) | Ovoz → matn, modelni lazy-load qilish va bo'shatish |
| [db.py](db.py) | SQLite: foydalanuvchilar va statistika |
| [i18n.py](i18n.py) | Interfeys matnlari (uz/ru/en/ar/fr/de) |
| [handlers/](handlers/) | `/start`, matn, ovoz va boshqa xabarlar |

### Tarjima ishonchliligi

Ikkita mustaqil provayder ketma-ket sinaladi (har biri 3 martadan, kechikish
oshib boradi):

1. **gtx JSON endpoint** — `translate.googleapis.com/translate_a/single`.
   JSON qaytaradi va **aniqlangan manba tilni ham** beradi.
2. **deep-translator** — birinchisi ishlamasa.

> ⚠️ **Nega bu shunday qilingan.** `deep-translator` Google sahifasini
> "scrape" qiladi. Google 500 xatosi qaytarganda u **xato sahifasining
> matnini muvaffaqiyatli tarjima sifatida** qaytaradi:
> `"Error 500 (Server Error)!!1500.That's an error..."` — va hech qanday
> exception ko'tarmaydi, ya'ni qayta urinish ham ishlamaydi.
> Bu haqiqiy foydalanuvchida ro'y bergan.
>
> Shuning uchun **har bir natija `_looks_like_error_page()` bilan
> tekshiriladi**. Tekshiruv `lru_cache` ning ichida turadi — aks holda axlat
> javob keshga tushib, barcha keyingi urinishlar ham o'shani qaytaraverardi.
>
> Ikkala provayder ham yiqilsa, foydalanuvchi **tushunarli xato xabari**
> oladi — hech qachon axlat matn emas.

### Til qanday aniqlanadi

Bu botning eng nozik joyi. **`sl=auto` ataylab ishlatilmaydi.**

Google avtomatik aniqlashda ~130 til ichidan tanlaydi va qisqa matnda
muntazam ravishda biz qo'llamaydigan tilni tanlaydi. O'lchangan haqiqiy
javoblar:

| Matn | Google aytdi | `sl=auto` bilan tarjima |
|---|---|---|
| `Qalaysan` | `so` (somali) | ❌ "Dry" / "Сухой" |
| `Rahmat` | `id` (indonez) | ❌ "Grace" / "Милость" |
| `Danke schoen` | `nl` (golland) | ❌ "Thank you shoe" |

Bitta xato **ikki** joyni buzadi: tarjima noto'g'ri chiqadi va xabardagi
"asl matn" yorlig'i noto'g'ri tilga yopishtiriladi — o'zbekcha matn
"🇬🇧 English · asl matn" bo'lib ko'rinadi.

Shuning uchun manba til avval aniqlanadi, keyin **barcha** tarjimalar aniq
`sl=<manba>` bilan so'raladi. Aniqlash tartibi:

1. **Yozuv** — arab yozuvi faqat `ar`, kirill faqat `ru`/`uz`, lotin esa
   `uz`/`en`/`fr`/`de` bo'lishi mumkin. Bu eng ishonchli dalil va arab
   matni uchun umuman so'rov yubormaydi.
2. **Google** — javobi shu chegara ichiga keltiriladi. Qo'llanmaydigan til
   aytsa, eng yaqin tilimizga o'tkaziladi (`so`/`id`/`tr` → `uz`,
   `nl`/`af` → `de`, `ca`/`it` → `fr`).
3. **Lug'at dalili** — qisqa (≤2 so'z) matnda Google bitta so'zga qarab
   hukm chiqaradi va adashadi (`Bonjour` → `en`). Lug'atimizda haqiqiy
   dalil bo'lsa — lug'atdagi so'z, `o'`/`g'` tutuq belgisi, `é è ç` yoki
   `ä ö ü ß` diakritikasi — o'shanga ishonamiz.
4. **Interfeys tili zondi** — dalilsiz qisqa matn hali ham ikki ma'noli:
   `Suv` ni Google `en` (SUV) deydi. Matnni foydalanuvchining interfeys
   tilidan tarjima qilib ko'ramiz; natija haqiqatan o'zgarsa (`Suv` →
   "Water"), demak matn o'sha tilda. Inglizcha `Hello` ni o'zbekchadan
   tarjima qilsak o'zgarmaydi va biz Google javobida qolamiz.
5. **Oflayn heuristika** — Google umuman javob bermasa ishlaydi:
   alifbo, o'zbekcha qo'shimchalar (`-lar`, `-ning`, `-yapman`),
   stopword'lar va diakritikalar.

Shu sababli `Non` so'zi o'zbek foydalanuvchi uchun "bread", fransuz
foydalanuvchi uchun "no" deb o'qiladi — teng dalilda interfeys tili hal
qiladi.

Ovoz uchun Whisper tilni faqat **qo'llab-quvvatlanadigan 6 til orasidan**
tanlaydi — aks holda u 99 ta tildan noto'g'risini tanlab, ma'nosiz matn
qaytarishi mumkin. Oltalasining ham ehtimoli past bo'lsa (shovqin, musiqa,
boshqa til), bot "tushunmadim" deb javob beradi.

### Ovoz sifati

Ovozli xabar aniqligi uchun:

- `WHISPER_MODEL=small` — `base` o'zbekchani ancha yomon eshitadi
- `WHISPER_BEAM=5` — greedy (`1`) qidiruv tez, lekin so'zlarni chalkashtiradi
- harorat zaxirasi (`0.0 → 1.0`) — natija ishonchsiz chiqsa qayta uriladi
- VAD `min_silence_duration_ms=700` — gap o'rtasidagi tabiiy pauza kesilmaydi

Model faqat ovoz kelganda yuklanadi va `WHISPER_IDLE_UNLOAD_SEC` dan keyin
xotiradan bo'shatiladi, shuning uchun `small` doimiy RAM sarfini oshirmaydi.

### Uzun matn qanday yuboriladi

Telegram bitta xabarni 4096 belgi bilan cheklaydi, shuning uchun uzun matn
yuborilganda **mijozning o'zi** uni bir necha xabarga bo'lib, ketma-ket
jo'natadi. Bu ikki joyni buzgan edi:

1. **Flood himoyasi bo'laklarni yeb qo'yardi.** `ThrottleMiddleware` interval
   ichida kelgan xabarni jimgina tashlab yuborardi (`return None`), ya'ni
   uzun matnning faqat birinchi bo'lagi tarjima qilinardi. Endi xabarlar
   navbatda kutadi; faqat navbat `max_queue` dan oshsa ogohlantiriladi.
2. **Javobni bo'lish.** `split_for_telegram` uzunlikni `len()` bilan
   o'lchardi, Telegram esa **UTF-16 kod birliklarida** sanaydi — 🇺🇿 kabi
   bayroq emoji Python uchun 2, Telegram uchun 4. Emojili matnda bo'lak
   chegaradan oshib ketardi. Bundan tashqari funksiya ba'zan **bo'sh bo'lak**
   qaytarardi (Telegram bo'sh xabarni rad etadi va butun yuborish to'xtardi)
   va til sarlavhasini o'z matnidan ajratib yuborardi.

Endi bo'lish `tg_len()` (UTF-16) bilan hisoblanadi, faqat so'z chegarasida
kesadi — shu sababli `&amp;` kabi HTML entity hech qachon ikkiga
bo'linmaydi — va sarlavha doim o'z matni bilan bitta xabarda qoladi.

Yuborishning o'zi ham himoyalangan: `429` (flood) kelsa kutib qayta uriladi,
HTML tahlil qilinmasa xabar oddiy matn sifatida yuboriladi, bitta bo'lak
yiqilsa qolganlari baribir yetkaziladi. `deliver` endi handler'ning
`try/except` bloki ichida — ilgari u tashqarida turgani uchun yuborishdagi
xato foydalanuvchiga bildirilmay, javob jimgina yo'qolardi.

### Nega bir vaqtda 3 ta so'rov

Bitta xabar 6 tilga tarjima qilinadi. Oltala so'rovni birdan yuborsak
Google'ning bepul endpoint'i "unusual traffic" deb bloklaydi — ishlab chiqish
paytida haqiqatan ro'y berdi: `302 Found` → `google.com/sorry/index`.
Shuning uchun:

- `translator._MAX_PARALLEL` bir vaqtda 3 tadan ko'p so'rovga yo'l qo'ymaydi
- kesh (`_CACHE_SIZE`) takroriy iboralarni umuman so'ramaydi
- `302`/`429` ko'ringanda gtx **120 soniyaga chetlab o'tiladi** — aks holda
  qolgan 5 til uchun ham 3 martadan urinib, blokni uzaytirar edik
- qayta urinish kechikishiga jitter qo'shilgan
