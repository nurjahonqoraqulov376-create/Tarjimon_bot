"""Matnli xabarni qo'llab-quvvatlanadigan barcha tillarga tarjima qilish."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import Message

import db
from i18n import t
from translator import TranslationError, translate_all

from .common import MAX_INPUT_CHARS, deliver, render

log = logging.getLogger(__name__)

router = Router(name="text")


@router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message, lang: str) -> None:
    source_text = (message.text or "").strip()
    if not source_text:
        return

    if len(source_text) > MAX_INPUT_CHARS:
        await message.answer(t("too_long_text", lang, max_chars=MAX_INPUT_CHARS))
        return

    status = await message.answer(t("translating", lang))
    try:
        result = await translate_all(source_text)
    except TranslationError as exc:
        log.warning("Tarjima muvaffaqiyatsiz: %s", exc)
        await status.edit_text(t("error", lang))
        return
    except Exception:
        log.exception("Matnni tarjima qilishda kutilmagan xato")
        await status.edit_text(t("error", lang))
        return

    await deliver(message, status, render(result, lang))
    await db.bump("text")
