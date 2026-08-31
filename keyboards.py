"""Inline klaviaturalar."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import LANG_FLAGS, LANG_NAMES, LANGS

LANG_CALLBACK_PREFIX = "setlang:"

# Tillar 6 ta bo'lgani uchun bitta ustunga tizsak klaviatura juda cho'zilib
# ketadi — qatoriga ikkitadan joylashtiramiz.
PER_ROW = 2


def language_keyboard(current: str | None = None) -> InlineKeyboardMarkup:
    """Interfeys tilini tanlash tugmalari. Joriy til ✓ bilan belgilanadi."""
    buttons = [
        InlineKeyboardButton(
            text=f"{LANG_FLAGS[lang]} {LANG_NAMES[lang]}"
            + (" ✓" if lang == current else ""),
            callback_data=f"{LANG_CALLBACK_PREFIX}{lang}",
        )
        for lang in LANGS
    ]
    rows = [buttons[i : i + PER_ROW] for i in range(0, len(buttons), PER_ROW)]
    return InlineKeyboardMarkup(inline_keyboard=rows)
