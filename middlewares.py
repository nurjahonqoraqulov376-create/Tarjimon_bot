"""Middleware'lar: foydalanuvchi tilini yuklash va flood'dan himoya."""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

import db
from i18n import normalize_lang, t


class UserLangMiddleware(BaseMiddleware):
    """Foydalanuvchini bazaga yozadi va uning interfeys tilini `data["lang"]` ga qo'yadi."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        default = normalize_lang(user.language_code)
        data["lang"] = await db.touch_user(user.id, user.username, default)
        return await handler(event, data)


class ThrottleMiddleware(BaseMiddleware):
    """Har bir foydalanuvchi uchun so'rovlar orasidagi minimal interval.

    Google'ning bepul tarjima endpoint'i ko'p so'rovda vaqtincha bloklaydi —
    bu himoya botni ham, foydalanuvchini ham asrab qoladi.
    """

    def __init__(self, interval: float, cache_size: int = 10_000) -> None:
        self.interval = interval
        self.cache_size = cache_size
        self._last: OrderedDict[int, float] = OrderedDict()
        self._warned: set[int] = set()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None or self.interval <= 0:
            return await handler(event, data)

        now = time.monotonic()
        last = self._last.get(user.id, 0.0)
        if now - last < self.interval:
            # Ogohlantirishni bir marta yuboramiz — spam bo'lib ketmasin.
            if user.id not in self._warned:
                self._warned.add(user.id)
                text = t("throttled", data.get("lang", "uz"))
                if isinstance(event, Message):
                    await event.answer(text)
                elif isinstance(event, CallbackQuery):
                    await event.answer(text, show_alert=False)
            return None

        self._warned.discard(user.id)
        self._last[user.id] = now
        self._last.move_to_end(user.id)
        while len(self._last) > self.cache_size:
            evicted, _ = self._last.popitem(last=False)
            # `_warned` ham birga tozalanadi, aks holda u cheksiz o'sib boradi.
            self._warned.discard(evicted)

        return await handler(event, data)
