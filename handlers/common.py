"""Handler'lar uchun umumiy: javobni chiroyli ko'rinishga keltirish va yuborish."""

from __future__ import annotations

import html
import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

from config import LANG_FLAGS, LANG_NAMES, LANGS
from i18n import t
from translator import TranslationResult
from utils import split_for_telegram

log = logging.getLogger(__name__)

# Telegram xabarining maksimal uzunligi — undan uzunini yubora olmaydi,
# ya'ni foydalanuvchi yuborishga ulgurgan har qanday matnni qabul qilamiz.
MAX_INPUT_CHARS = 4096


def render(result: TranslationResult, ui_lang: str) -> str:
    """Uchala tildagi natijani bitta xabar matniga yig'adi.

    Manba til birinchi turadi va "asl matn" deb belgilanadi.
    """
    order = [result.source] + [lang for lang in LANGS if lang != result.source]
    blocks = []
    for lang in order:
        text = result.texts.get(lang)
        if not text:
            continue
        header = f"{LANG_FLAGS[lang]} <b>{LANG_NAMES[lang]}</b>"
        if lang == result.source:
            header += f" · <i>{t('source_label', ui_lang)}</i>"
        # quote=False muhim: Telegram HTML'da faqat &amp; &lt; &gt; ni biladi,
        # apostrofni &#x27; ga aylantirsak o'zbekcha "so'rang" buzilib ketadi.
        blocks.append(f"{header}\n{html.escape(text, quote=False)}")
    return "\n\n".join(blocks)


async def deliver(message: Message, status: Message | None, body: str) -> None:
    """Natijani yuboradi: qisqa bo'lsa status xabarini tahrirlaydi, uzun bo'lsa bo'lib yuboradi."""
    parts = split_for_telegram(body)

    if status is not None and len(parts) == 1:
        try:
            await status.edit_text(parts[0])
            return
        except TelegramBadRequest as exc:
            log.debug("Xabarni tahrirlab bo'lmadi, yangisini yuboramiz: %s", exc)

    if status is not None:
        try:
            await status.delete()
        except TelegramBadRequest:
            pass

    for part in parts:
        await message.answer(part)
