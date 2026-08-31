"""Ovozli xabarni matnga o'girib, barcha tillarga tarjima qilish."""

from __future__ import annotations

import logging
import os
import tempfile

from aiogram import Bot, F, Router
from aiogram.types import Message

import db
import stt
from config import Config
from i18n import t
from translator import TranslationError, translate_all

from .common import deliver, render

log = logging.getLogger(__name__)

router = Router(name="voice")

# Telegram bot API orqali yuklab olish mumkin bo'lgan maksimal hajm.
MAX_FILE_BYTES = 20 * 1024 * 1024


def _media(message: Message):
    return message.voice or message.audio or message.video_note


@router.message(F.voice | F.audio | F.video_note)
async def on_voice(message: Message, lang: str, bot: Bot, config: Config) -> None:
    media = _media(message)
    if media is None:
        return

    duration = getattr(media, "duration", 0) or 0
    if duration > config.max_voice_sec:
        await message.answer(
            t("too_long_voice", lang, sec=duration, max_sec=config.max_voice_sec)
        )
        return

    if (getattr(media, "file_size", 0) or 0) > MAX_FILE_BYTES:
        await message.answer(
            t("too_long_voice", lang, sec=duration, max_sec=config.max_voice_sec)
        )
        return

    status = await message.answer(t("listening", lang))

    # Telegram voice — .oga (OPUS); faster-whisper uni o'zi dekodlaydi.
    handle, path = tempfile.mkstemp(suffix=".oga")
    os.close(handle)
    try:
        file = await bot.get_file(media.file_id)
        if not file.file_path:
            await status.edit_text(t("error", lang))
            return
        await bot.download_file(file.file_path, destination=path)

        transcript, detected = await stt.transcribe(path)
        if not transcript:
            await status.edit_text(t("empty_voice", lang))
            return

        await status.edit_text(t("translating", lang))
        result = await translate_all(transcript, hint=detected, ui_lang=lang)
    except TranslationError as exc:
        log.warning("Ovoz tarjimasi muvaffaqiyatsiz: %s", exc)
        await status.edit_text(t("error", lang))
        return
    except Exception:
        log.exception("Ovozli xabarni qayta ishlashda kutilmagan xato")
        await status.edit_text(t("error", lang))
        return
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

    await deliver(message, status, render(result, lang))
    await db.bump("voice")
