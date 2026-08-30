# 🌐 Tarjimon Bot — uz / ru / en

Telegram bot: **qaysi tilda yozsangiz ham**, javobda **uchala tildagi** tarjima
chiqadi. Ovozli xabar yuborsangiz — avval matnga o'giradi, keyin tarjima qiladi.

```
Siz:  Salom, qalaysan?

Bot:  🇺🇿 O'zbekcha · asl matn
      Salom, qalaysan?

      🇷🇺 Русский
      Привет, как дела?

      🇬🇧 English
      Hello, how are you?
```

## Imkoniyatlar

- 🔄 **Avtomatik til aniqlash** — manba tilni ko'rsatish shart emas
- 🌍 **Uchala tilda javob** — uz, ru, en bir xabarda
- 🎤 **Ovozli xabar** — faster-whisper orqali matnga o'girib tarjima qiladi
- 🇺🇿🇷🇺🇬🇧 **Interfeys tili** — menyu va xabarlar siz tanlagan tilda
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
| `WHISPER_MODEL` | `base` | `tiny` / `base` / `small` |
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

**Railway'da o'lchangan haqiqiy natijalar** (bo'sh turgan bot, production):

| Resurs | O'lchov | Oylik |
|---|---|---|
| RAM | o'rtacha **65 MB**, eng yuqori 173 MB | ~$0.64 |
| CPU | o'rtacha **0.003 vCPU** | ~$0.06 |
| **Jami** | | **~$0.70/oy** |

Ya'ni $5 kredit ichida ovoz tarjimasi uchun juda katta zaxira qoladi.
(Ovoz qayta ishlanayotganda RAM qisqa muddatga ~400 MB gacha ko'tariladi,
keyin `WHISPER_IDLE_UNLOAD_SEC` dan so'ng yana tushadi.)

**Sifatni oshirmoqchi bo'lsangiz:** `WHISPER_MODEL=small` qo'ying — o'zbek tilini
ancha yaxshi tushunadi, lekin RAM ~950 MB gacha ko'tariladi va faol botda oylik
$5 dan oshib ketishi mumkin. O'zgartirgandan keyin Railway loyihani qayta
build qiladi (model image ichiga yangidan yuklanadi).

---

## Qanday ishlaydi

| Fayl | Vazifasi |
|---|---|
| [bot.py](bot.py) | Ishga tushirish, middleware'lar, polling |
| [translator.py](translator.py) | Tarjima, til aniqlash, bo'laklarga bo'lish, kesh |
| [stt.py](stt.py) | Ovoz → matn, modelni lazy-load qilish va bo'shatish |
| [db.py](db.py) | SQLite: foydalanuvchilar va statistika |
| [i18n.py](i18n.py) | Interfeys matnlari (uz/ru/en) |
| [handlers/](handlers/) | `/start`, matn, ovoz va boshqa xabarlar |

### Til qanday aniqlanadi

deep-translator manba tilni qaytarmaydi, `langdetect` esa o'zbek tilini bilmaydi.
Shuning uchun ikki bosqich ishlatiladi:

1. **Heuristika** — alifbo (kirill/lotin), o'zbekcha tutuq belgilari (`o'`, `g'`),
   o'zbek kirilligiga xos harflar (`ў қ ғ ҳ`) va stopword'lar.
2. **Tasdiqlash** — matn baribir uchala tilga tarjima qilinadi; manba tilga
   tarjima natijasi asl matnga deyarli teng chiqadi. Qo'shimcha so'rov
   talab qilmaydi va heuristika xatosini tuzatadi.

Ovoz uchun Whisper tilni faqat **uz/ru/en orasidan** tanlaydi — aks holda u
99 ta tildan noto'g'risini tanlab, ma'nosiz matn qaytarishi mumkin. Uchala
tilning ehtimoli ham past bo'lsa (shovqin, musiqa, boshqa til), bot
"tushunmadim" deb javob beradi.
