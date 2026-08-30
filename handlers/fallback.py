"""Boshqa hech qaysi handler ushlamagan xabarlar."""

from __future__ import annotations

from aiogram import Router
from aiogram.types import Message

from config import Config
from i18n import t

router = Router(name="fallback")


@router.message()
async def on_unhandled(message: Message, lang: str, config: Config) -> None:
    if (message.text or "").startswith("/"):
        # Noma'lum buyruq — yordam ko'rsatamiz.
        await message.answer(t("help", lang, max_sec=config.max_voice_sec))
        return
    # Foto, stiker, hujjat, joylashuv va hokazo.
    await message.answer(t("unsupported", lang))
