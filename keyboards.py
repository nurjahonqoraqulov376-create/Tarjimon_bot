"""Inline klaviaturalar."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import LANG_FLAGS, LANG_NAMES, LANGS

LANG_CALLBACK_PREFIX = "setlang:"


def language_keyboard(current: str | None = None) -> InlineKeyboardMarkup:
    """Interfeys tilini tanlash tugmalari. Joriy til ✓ bilan belgilanadi."""
    row = [
        InlineKeyboardButton(
            text=f"{LANG_FLAGS[lang]} {LANG_NAMES[lang]}"
            + (" ✓" if lang == current else ""),
            callback_data=f"{LANG_CALLBACK_PREFIX}{lang}",
        )
        for lang in LANGS
    ]
    return InlineKeyboardMarkup(inline_keyboard=[[button] for button in row])
