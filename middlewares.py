"""Middleware'lar: foydalanuvchi tilini yuklash va flood'dan himoya."""

from __future__ import annotations

import asyncio
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
    """Har bir foydalanuvchi so'rovlarini navbatga qo'yadi.

    Google'ning bepul tarjima endpoint'i ko'p so'rovda vaqtincha bloklaydi,
    shuning uchun bitta foydalanuvchining xabarlari **birin-ketin** qayta
    ishlanadi va orasida kamida `interval` bo'ladi.

    NEGA NAVBAT, TASHLAB YUBORISH EMAS
    ----------------------------------
    Ilgari interval ichida kelgan xabar jimgina tashlanardi (`return None`).
    Telegram'da bitta xabar 4096 belgi bilan cheklangan, shuning uchun uzun
    matn yuborilganda **mijozning o'zi** uni bir necha xabarga bo'lib,
    ketma-ket (millisekundlar farqi bilan) yuboradi. Natijada uzun matnning
    faqat **birinchi bo'lagi** tarjima qilinar, qolgani yo'qolardi — tashqi
    ko'rinishda "bot uzun matnni tarjima qilmayapti" bo'lib tuyulardi.

    Endi bunday xabarlar navbatda kutadi. Faqat navbat `max_queue` dan
    oshsa — bu haqiqiy flood — ogohlantirish beriladi.
    """

    def __init__(
        self, interval: float, max_queue: int = 5, cache_size: int = 10_000
    ) -> None:
        self.interval = interval
        self.max_queue = max_queue
        self.cache_size = cache_size
        self._locks: OrderedDict[int, asyncio.Lock] = OrderedDict()
        self._last: dict[int, float] = {}
        self._queued: dict[int, int] = {}

    def _lock_for(self, user_id: int) -> asyncio.Lock:
        lock = self._locks.get(user_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[user_id] = lock
        self._locks.move_to_end(user_id)
        return lock

    def _evict(self) -> None:
        """Faol bo'lmagan eski yozuvlarni tozalaydi — xotira cheksiz o'smasin."""
        while len(self._locks) > self.cache_size:
            for user_id in list(self._locks):
                if not self._queued.get(user_id):
                    del self._locks[user_id]
                    self._last.pop(user_id, None)
                    break
            else:
                # Hammasi band — keyinroq tozalanadi.
                return

    async def _warn(self, event: TelegramObject, lang: str) -> None:
        text = t("throttled", lang)
        if isinstance(event, Message):
            await event.answer(text)
        elif isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=False)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None or self.interval <= 0:
            return await handler(event, data)

        user_id = user.id
        if self._queued.get(user_id, 0) >= self.max_queue:
            # Navbat to'lib ketdi — bu uzun matn emas, haqiqiy flood.
            await self._warn(event, data.get("lang", "uz"))
            return None

        self._queued[user_id] = self._queued.get(user_id, 0) + 1
        try:
            async with self._lock_for(user_id):
                wait = self.interval - (time.monotonic() - self._last.get(user_id, 0.0))
                if wait > 0:
                    await asyncio.sleep(wait)
                self._last[user_id] = time.monotonic()
                return await handler(event, data)
        finally:
            remaining = self._queued.get(user_id, 1) - 1
            if remaining > 0:
                self._queued[user_id] = remaining
            else:
                self._queued.pop(user_id, None)
            self._evict()
