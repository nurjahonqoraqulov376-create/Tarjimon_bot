"""Buyruqlar: /start, /til, /help, /stats."""

from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

import db
import stt
from config import Config, LANGS
from i18n import t
from keyboards import LANG_CALLBACK_PREFIX, language_keyboard
from utils import rss_mb

router = Router(name="commands")


@router.message(CommandStart())
async def cmd_start(message: Message, lang: str) -> None:
    name = message.from_user.first_name if message.from_user else ""
    # Ism HTML xabar ichiga qo'yiladi — "<" li ismlar xabarni buzmasligi kerak.
    await message.answer(t("start", lang, name=html.escape(name, quote=False)))
    await message.answer(t("choose_lang", lang), reply_markup=language_keyboard(lang))


@router.message(Command("til", "lang", "language"))
async def cmd_lang(message: Message, lang: str) -> None:
    await message.answer(t("choose_lang", lang), reply_markup=language_keyboard(lang))


@router.callback_query(F.data.startswith(LANG_CALLBACK_PREFIX))
async def on_lang_selected(callback: CallbackQuery, config: Config) -> None:
    chosen = (callback.data or "").removeprefix(LANG_CALLBACK_PREFIX)
    if chosen not in LANGS:
        await callback.answer()
        return

    await db.set_lang(callback.from_user.id, chosen)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            t("lang_saved", chosen), reply_markup=language_keyboard(chosen)
        )
        await callback.message.answer(
            t("help", chosen, max_sec=config.max_voice_sec)
        )


@router.message(Command("help"))
async def cmd_help(message: Message, lang: str, config: Config) -> None:
    await message.answer(t("help", lang, max_sec=config.max_voice_sec))


@router.message(Command("stats"))
async def cmd_stats(message: Message, lang: str, config: Config) -> None:
    if not message.from_user or message.from_user.id != config.admin_id:
        await message.answer(t("not_admin", lang))
        return

    stats = await db.get_stats()
    whisper = (
        t("whisper_loaded", lang, model=config.whisper_model)
        if stt.is_loaded()
        else t("whisper_unloaded", lang)
    )
    await message.answer(
        t("stats", lang, rss_mb=rss_mb(), whisper=whisper, **stats)
    )
