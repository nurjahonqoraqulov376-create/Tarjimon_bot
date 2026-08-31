"""Bot interfeysi matnlari: o'zbek, rus, ingliz, arab, fransuz, nemis."""

from __future__ import annotations

from config import LANGS

TEXTS: dict[str, dict[str, str]] = {
    "uz": {
        "choose_lang": "Interfeys tilini tanlang:",
        "lang_saved": "✅ Til o'zbekchaga o'zgartirildi.",
        "start": (
            "👋 Salom, <b>{name}</b>!\n\n"
            "Men <b>6 tilli tarjimonman</b>. Menga <b>istalgan tilda</b> "
            "(o'zbek, rus, ingliz, arab, fransuz yoki nemis) matn yozing — "
            "men uni <b>oltala tilda</b> qaytaraman.\n\n"
            "🎤 Ovozli xabar ham yuborishingiz mumkin — avval matnga "
            "o'giraman, keyin tarjima qilaman.\n\n"
            "Boshlash uchun shunchaki biror narsa yozing 👇"
        ),
        "help": (
            "<b>Qanday ishlataman?</b>\n\n"
            "• Matn yozing — javobda 🇺🇿 🇷🇺 🇬🇧 🇸🇦 🇫🇷 🇩🇪 tarjimalar chiqadi\n"
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
        "partial_fail": (
            "\n\n⚠️ <i>Ba'zi tillarga tarjima qilinmadi, "
            "birozdan keyin urinib ko'ring.</i>"
        ),
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
            "Я <b>переводчик на 6 языков</b>. Напишите мне текст на "
            "<b>любом языке</b> (узбекский, русский, английский, арабский, "
            "французский или немецкий) — я верну перевод <b>на всех шести</b>.\n\n"
            "🎤 Можно отправить и голосовое сообщение — сначала распознаю "
            "речь, потом переведу.\n\n"
            "Просто напишите что-нибудь 👇"
        ),
        "help": (
            "<b>Как пользоваться?</b>\n\n"
            "• Отправьте текст — в ответ придут переводы 🇺🇿 🇷🇺 🇬🇧 🇸🇦 🇫🇷 🇩🇪\n"
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
        "partial_fail": (
            "\n\n⚠️ <i>Не удалось перевести на некоторые языки, "
            "попробуйте позже.</i>"
        ),
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
            "I'm a <b>6-language translator</b>. Send me text in <b>any "
            "language</b> (Uzbek, Russian, English, Arabic, French or German) "
            "and I'll reply with the translation <b>in all six</b>.\n\n"
            "🎤 You can also send a voice message — I'll transcribe it "
            "first, then translate.\n\n"
            "Just type something to start 👇"
        ),
        "help": (
            "<b>How to use</b>\n\n"
            "• Send text — you'll get 🇺🇿 🇷🇺 🇬🇧 🇸🇦 🇫🇷 🇩🇪 translations back\n"
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
        "partial_fail": (
            "\n\n⚠️ <i>Some languages could not be translated, "
            "please try again later.</i>"
        ),
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
    "ar": {
        "choose_lang": "اختر لغة الواجهة:",
        "lang_saved": "✅ تم تغيير اللغة إلى العربية.",
        "start": (
            "👋 مرحبًا، <b>{name}</b>!\n\n"
            "أنا <b>مترجم بست لغات</b>. أرسل لي نصًا <b>بأي لغة</b> "
            "(الأوزبكية، الروسية، الإنجليزية، العربية، الفرنسية أو الألمانية) "
            "وسأعيد لك الترجمة <b>باللغات الست</b>.\n\n"
            "🎤 يمكنك أيضًا إرسال رسالة صوتية — سأحوّلها إلى نص أولًا ثم أترجمها.\n\n"
            "اكتب أي شيء للبدء 👇"
        ),
        "help": (
            "<b>كيفية الاستخدام</b>\n\n"
            "• أرسل نصًا — ستصلك ترجمات 🇺🇿 🇷🇺 🇬🇧 🇸🇦 🇫🇷 🇩🇪\n"
            "• 🎤 أرسل رسالة صوتية (حتى {max_sec} ثانية)\n"
            "• لا حاجة لتحديد لغة المصدر — سأكتشفها بنفسي\n\n"
            "<b>الأوامر</b>\n"
            "/start — إعادة تشغيل البوت\n"
            "/til — تغيير لغة الواجهة\n"
            "/help — هذه المساعدة"
        ),
        "translating": "⏳ جارٍ الترجمة...",
        "listening": "🎧 جارٍ تحويل الصوت إلى نص...",
        "source_label": "النص الأصلي",
        "too_long_voice": (
            "⚠️ الرسالة الصوتية طويلة جدًا ({sec} ثانية). "
            "الحد الأقصى هو {max_sec} ثانية."
        ),
        "too_long_text": "⚠️ النص طويل جدًا. الحد الأقصى {max_chars} حرفًا.",
        "empty_voice": "🤔 لم أتمكن من تمييز أي كلام. حاول التحدث بوضوح أكبر.",
        "error": "❌ حدث خطأ ما. حاول مرة أخرى بعد قليل.",
        "throttled": "⏱ بسرعة كبيرة — انتظر قليلًا من فضلك.",
        "partial_fail": (
            "\n\n⚠️ <i>تعذّرت الترجمة إلى بعض اللغات، حاول مرة أخرى لاحقًا.</i>"
        ),
        "unsupported": "🤔 أستطيع ترجمة <b>النصوص</b> و<b>الرسائل الصوتية</b> فقط.",
        "not_admin": "هذا الأمر متاح للمشرف فقط.",
        "stats": (
            "<b>📊 الإحصائيات</b>\n\n"
            "👥 المستخدمون: <b>{users}</b>\n"
            "🔥 نشطون خلال 24 ساعة: <b>{active_24h}</b>\n"
            "✍️ ترجمات نصية: <b>{texts}</b>\n"
            "🎤 ترجمات صوتية: <b>{voices}</b>\n\n"
            "🧠 الذاكرة (RSS): <b>{rss_mb} MB</b>\n"
            "🗣 نموذج Whisper: <b>{whisper}</b>"
        ),
        "whisper_loaded": "محمّل ({model})",
        "whisper_unloaded": "غير محمّل",
    },
    "fr": {
        "choose_lang": "Choisissez la langue de l'interface :",
        "lang_saved": "✅ Langue changée en français.",
        "start": (
            "👋 Bonjour, <b>{name}</b> !\n\n"
            "Je suis un <b>traducteur en 6 langues</b>. Écrivez-moi un texte "
            "dans <b>n'importe quelle langue</b> (ouzbek, russe, anglais, arabe, "
            "français ou allemand) — je vous renverrai la traduction "
            "<b>dans les six</b>.\n\n"
            "🎤 Vous pouvez aussi envoyer un message vocal — je le transcris "
            "d'abord, puis je traduis.\n\n"
            "Écrivez quelque chose pour commencer 👇"
        ),
        "help": (
            "<b>Comment m'utiliser ?</b>\n\n"
            "• Envoyez un texte — vous recevrez les traductions 🇺🇿 🇷🇺 🇬🇧 🇸🇦 🇫🇷 🇩🇪\n"
            "• 🎤 Envoyez un message vocal (jusqu'à {max_sec} secondes)\n"
            "• Inutile d'indiquer la langue source — je la détecte moi-même\n\n"
            "<b>Commandes</b>\n"
            "/start — redémarrer le bot\n"
            "/til — changer la langue de l'interface\n"
            "/help — cette aide"
        ),
        "translating": "⏳ Traduction en cours...",
        "listening": "🎧 Transcription du message vocal...",
        "source_label": "texte original",
        "too_long_voice": (
            "⚠️ Ce message vocal est trop long ({sec} s). "
            "La limite est de {max_sec} secondes."
        ),
        "too_long_text": (
            "⚠️ Ce texte est trop long. La limite est de {max_chars} caractères."
        ),
        "empty_voice": (
            "🤔 Je n'ai rien pu distinguer. Essayez de parler plus clairement."
        ),
        "error": "❌ Une erreur s'est produite. Réessayez dans un instant.",
        "throttled": "⏱ Trop rapide — patientez un instant.",
        "partial_fail": (
            "\n\n⚠️ <i>Certaines langues n'ont pas pu être traduites, "
            "réessayez plus tard.</i>"
        ),
        "unsupported": (
            "🤔 Je ne peux traduire que du <b>texte</b> et des "
            "<b>messages vocaux</b>."
        ),
        "not_admin": "Cette commande est réservée à l'administrateur.",
        "stats": (
            "<b>📊 Statistiques</b>\n\n"
            "👥 Utilisateurs : <b>{users}</b>\n"
            "🔥 Actifs sur 24 h : <b>{active_24h}</b>\n"
            "✍️ Traductions de texte : <b>{texts}</b>\n"
            "🎤 Traductions vocales : <b>{voices}</b>\n\n"
            "🧠 Mémoire (RSS) : <b>{rss_mb} MB</b>\n"
            "🗣 Modèle Whisper : <b>{whisper}</b>"
        ),
        "whisper_loaded": "chargé ({model})",
        "whisper_unloaded": "non chargé",
    },
    "de": {
        "choose_lang": "Wähle die Sprache der Oberfläche:",
        "lang_saved": "✅ Sprache auf Deutsch umgestellt.",
        "start": (
            "👋 Hallo, <b>{name}</b>!\n\n"
            "Ich bin ein <b>Übersetzer für 6 Sprachen</b>. Schreib mir einen "
            "Text in <b>einer beliebigen Sprache</b> (Usbekisch, Russisch, "
            "Englisch, Arabisch, Französisch oder Deutsch) — ich antworte mit "
            "der Übersetzung <b>in allen sechs</b>.\n\n"
            "🎤 Du kannst auch eine Sprachnachricht senden — ich schreibe sie "
            "zuerst ab und übersetze sie dann.\n\n"
            "Schreib einfach etwas, um zu starten 👇"
        ),
        "help": (
            "<b>So funktioniert es</b>\n\n"
            "• Sende einen Text — du bekommst 🇺🇿 🇷🇺 🇬🇧 🇸🇦 🇫🇷 🇩🇪 Übersetzungen\n"
            "• 🎤 Sende eine Sprachnachricht (bis zu {max_sec} Sekunden)\n"
            "• Die Ausgangssprache musst du nicht angeben — ich erkenne sie\n\n"
            "<b>Befehle</b>\n"
            "/start — Bot neu starten\n"
            "/til — Sprache der Oberfläche ändern\n"
            "/help — diese Hilfe"
        ),
        "translating": "⏳ Übersetze...",
        "listening": "🎧 Sprachnachricht wird transkribiert...",
        "source_label": "Originaltext",
        "too_long_voice": (
            "⚠️ Diese Sprachnachricht ist zu lang ({sec} s). "
            "Das Limit liegt bei {max_sec} Sekunden."
        ),
        "too_long_text": (
            "⚠️ Dieser Text ist zu lang. Das Limit liegt bei {max_chars} Zeichen."
        ),
        "empty_voice": (
            "🤔 Ich konnte nichts verstehen. Sprich bitte etwas deutlicher."
        ),
        "error": "❌ Etwas ist schiefgelaufen. Versuche es gleich noch einmal.",
        "throttled": "⏱ Zu schnell — warte bitte einen Moment.",
        "partial_fail": (
            "\n\n⚠️ <i>Einige Sprachen konnten nicht übersetzt werden, "
            "versuche es später noch einmal.</i>"
        ),
        "unsupported": (
            "🤔 Ich kann nur <b>Text</b> und <b>Sprachnachrichten</b> übersetzen."
        ),
        "not_admin": "Dieser Befehl ist nur für den Administrator.",
        "stats": (
            "<b>📊 Statistik</b>\n\n"
            "👥 Nutzer: <b>{users}</b>\n"
            "🔥 Aktiv in 24 h: <b>{active_24h}</b>\n"
            "✍️ Textübersetzungen: <b>{texts}</b>\n"
            "🎤 Sprachübersetzungen: <b>{voices}</b>\n\n"
            "🧠 Speicher (RSS): <b>{rss_mb} MB</b>\n"
            "🗣 Whisper-Modell: <b>{whisper}</b>"
        ),
        "whisper_loaded": "geladen ({model})",
        "whisper_unloaded": "nicht geladen",
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
    "ar": {
        "start": "تشغيل البوت",
        "til": "تغيير لغة الواجهة",
        "help": "مساعدة",
    },
    "fr": {
        "start": "Démarrer le bot",
        "til": "Changer la langue de l'interface",
        "help": "Aide",
    },
    "de": {
        "start": "Bot starten",
        "til": "Sprache der Oberfläche ändern",
        "help": "Hilfe",
    },
}


def t(key: str, lang: str, **kwargs) -> str:
    """Tarjima matnini oladi; til yoki kalit topilmasa o'zbekchaga qaytadi."""
    table = TEXTS.get(lang) or TEXTS["uz"]
    template = table.get(key) or TEXTS["uz"].get(key, key)
    return template.format(**kwargs) if kwargs else template


def normalize_lang(code: str | None) -> str:
    """Telegram'ning `language_code` qiymatini `LANGS` dagi tilga keltiradi."""
    if not code:
        return "uz"
    base = code.split("-")[0].lower()
    if base in LANGS:
        return base
    # Boshqa tillar uchun ingliz interfeysi eng tushunarli variant.
    return "en"
