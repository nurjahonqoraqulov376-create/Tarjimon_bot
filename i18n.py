"""Bot interfeysi matnlari: o'zbek, rus, ingliz."""

from __future__ import annotations

from config import LANGS

TEXTS: dict[str, dict[str, str]] = {
    "uz": {
        "choose_lang": "Interfeys tilini tanlang:",
        "lang_saved": "✅ Til o'zbekchaga o'zgartirildi.",
        "start": (
            "👋 Salom, <b>{name}</b>!\n\n"
            "Men <b>3 tilli tarjimonman</b>. Menga <b>istalgan tilda</b> "
            "(o'zbek, rus yoki ingliz) matn yozing — men uni "
            "<b>uchala tilda</b> qaytaraman.\n\n"
            "🎤 Ovozli xabar ham yuborishingiz mumkin — avval matnga "
            "o'giraman, keyin tarjima qilaman.\n\n"
            "Boshlash uchun shunchaki biror narsa yozing 👇"
        ),
        "help": (
            "<b>Qanday ishlataman?</b>\n\n"
            "• Matn yozing — javobda 🇺🇿 🇷🇺 🇬🇧 uchala tarjima chiqadi\n"
            "• 🎤 Ovozli xabar yuboring (maksimal {max_sec} soniya)\n"
            "• Manba tilni ko'rsatish shart emas — o'zim aniqlayman\n\n"
            "<b>Buyruqlar</b>\n"
            "/start — botni qayta ishga tushirish\n"
            "/til — interfeys tilini o'zgartirish\n"
            "/help — shu yordam"
        ),
        "translating": "⏳ Tarjima qilinmoqda...",
        "listening": "🎧 Ovoz matnga o'girilmoqda...",
        "source_label": "asl matn",
        "too_long_voice": (
            "⚠️ Ovoz juda uzun ({sec} soniya). "
            "Maksimal uzunlik — {max_sec} soniya."
        ),
        "too_long_text": (
            "⚠️ Matn juda uzun. Maksimal {max_chars} belgi qabul qilaman."
        ),
        "empty_voice": "🤔 Ovozdan matn chiqmadi. Balandroq va aniqroq gapirib ko'ring.",
        "error": "❌ Xatolik yuz berdi. Birozdan keyin qayta urinib ko'ring.",
        "throttled": "⏱ Birozdan keyin urinib ko'ring.",
        "unsupported": (
            "🤔 Men faqat <b>matn</b> va <b>ovozli xabar</b>ni tarjima qila olaman."
        ),
        "not_admin": "Bu buyruq faqat admin uchun.",
        "stats": (
            "<b>📊 Statistika</b>\n\n"
            "👥 Foydalanuvchilar: <b>{users}</b>\n"
            "🔥 24 soatda faol: <b>{active_24h}</b>\n"
            "✍️ Matn tarjimalari: <b>{texts}</b>\n"
            "🎤 Ovoz tarjimalari: <b>{voices}</b>\n\n"
            "🧠 Xotira (RSS): <b>{rss_mb} MB</b>\n"
            "🗣 Whisper modeli: <b>{whisper}</b>"
        ),
        "whisper_loaded": "yuklangan ({model})",
        "whisper_unloaded": "yuklanmagan",
    },
    "ru": {
        "choose_lang": "Выберите язык интерфейса:",
        "lang_saved": "✅ Язык изменён на русский.",
        "start": (
            "👋 Привет, <b>{name}</b>!\n\n"
            "Я <b>переводчик на 3 языка</b>. Напишите мне текст на "
            "<b>любом языке</b> (узбекский, русский или английский) — "
            "я верну перевод <b>на всех трёх</b>.\n\n"
            "🎤 Можно отправить и голосовое сообщение — сначала распознаю "
            "речь, потом переведу.\n\n"
            "Просто напишите что-нибудь 👇"
        ),
        "help": (
            "<b>Как пользоваться?</b>\n\n"
            "• Отправьте текст — в ответ придут переводы 🇺🇿 🇷🇺 🇬🇧\n"
            "• 🎤 Отправьте голосовое (максимум {max_sec} секунд)\n"
            "• Указывать исходный язык не нужно — определю сам\n\n"
            "<b>Команды</b>\n"
            "/start — перезапустить бота\n"
            "/til — сменить язык интерфейса\n"
            "/help — эта справка"
        ),
        "translating": "⏳ Перевожу...",
        "listening": "🎧 Распознаю речь...",
        "source_label": "оригинал",
        "too_long_voice": (
            "⚠️ Голосовое слишком длинное ({sec} сек). "
            "Максимум — {max_sec} секунд."
        ),
        "too_long_text": (
            "⚠️ Текст слишком длинный. Максимум {max_chars} символов."
        ),
        "empty_voice": "🤔 Не удалось распознать речь. Попробуйте говорить чётче.",
        "error": "❌ Произошла ошибка. Попробуйте чуть позже.",
        "throttled": "⏱ Слишком часто, подождите немного.",
        "unsupported": (
            "🤔 Я умею переводить только <b>текст</b> и <b>голосовые сообщения</b>."
        ),
        "not_admin": "Команда доступна только администратору.",
        "stats": (
            "<b>📊 Статистика</b>\n\n"
            "👥 Пользователей: <b>{users}</b>\n"
            "🔥 Активных за 24ч: <b>{active_24h}</b>\n"
            "✍️ Переводов текста: <b>{texts}</b>\n"
            "🎤 Переводов голоса: <b>{voices}</b>\n\n"
            "🧠 Память (RSS): <b>{rss_mb} MB</b>\n"
            "🗣 Модель Whisper: <b>{whisper}</b>"
        ),
        "whisper_loaded": "загружена ({model})",
        "whisper_unloaded": "не загружена",
    },
    "en": {
        "choose_lang": "Choose the interface language:",
        "lang_saved": "✅ Language switched to English.",
        "start": (
            "👋 Hi, <b>{name}</b>!\n\n"
            "I'm a <b>3-language translator</b>. Send me text in <b>any "
            "language</b> (Uzbek, Russian or English) and I'll reply with "
            "the translation <b>in all three</b>.\n\n"
            "🎤 You can also send a voice message — I'll transcribe it "
            "first, then translate.\n\n"
            "Just type something to start 👇"
        ),
        "help": (
            "<b>How to use</b>\n\n"
            "• Send text — you'll get 🇺🇿 🇷🇺 🇬🇧 translations back\n"
            "• 🎤 Send a voice message (up to {max_sec} seconds)\n"
            "• No need to pick a source language — I detect it\n\n"
            "<b>Commands</b>\n"
            "/start — restart the bot\n"
            "/til — change interface language\n"
            "/help — this help"
        ),
        "translating": "⏳ Translating...",
        "listening": "🎧 Transcribing the voice message...",
        "source_label": "original",
        "too_long_voice": (
            "⚠️ That voice message is too long ({sec}s). "
            "The limit is {max_sec} seconds."
        ),
        "too_long_text": "⚠️ That text is too long. The limit is {max_chars} characters.",
        "empty_voice": "🤔 I couldn't make out any speech. Try speaking more clearly.",
        "error": "❌ Something went wrong. Please try again in a moment.",
        "throttled": "⏱ Too fast — please wait a moment.",
        "unsupported": "🤔 I can only translate <b>text</b> and <b>voice messages</b>.",
        "not_admin": "This command is for the admin only.",
        "stats": (
            "<b>📊 Stats</b>\n\n"
            "👥 Users: <b>{users}</b>\n"
            "🔥 Active in 24h: <b>{active_24h}</b>\n"
            "✍️ Text translations: <b>{texts}</b>\n"
            "🎤 Voice translations: <b>{voices}</b>\n\n"
            "🧠 Memory (RSS): <b>{rss_mb} MB</b>\n"
            "🗣 Whisper model: <b>{whisper}</b>"
        ),
        "whisper_loaded": "loaded ({model})",
        "whisper_unloaded": "not loaded",
    },
}

# Telegram buyruqlar menyusi (BotFather'dagi ro'yxat).
COMMAND_DESCRIPTIONS = {
    "uz": {
        "start": "Botni ishga tushirish",
        "til": "Interfeys tilini o'zgartirish",
        "help": "Yordam",
    },
    "ru": {
        "start": "Запустить бота",
        "til": "Сменить язык интерфейса",
        "help": "Помощь",
    },
    "en": {
        "start": "Start the bot",
        "til": "Change interface language",
        "help": "Help",
    },
}


def t(key: str, lang: str, **kwargs) -> str:
    """Tarjima matnini oladi; til yoki kalit topilmasa o'zbekchaga qaytadi."""
    table = TEXTS.get(lang) or TEXTS["uz"]
    template = table.get(key) or TEXTS["uz"].get(key, key)
    return template.format(**kwargs) if kwargs else template


def normalize_lang(code: str | None) -> str:
    """Telegram'ning `language_code` qiymatini uz/ru/en ga keltiradi."""
    if not code:
        return "uz"
    base = code.split("-")[0].lower()
    if base in LANGS:
        return base
    # Boshqa tillar uchun ingliz interfeysi eng tushunarli variant.
    return "en"
