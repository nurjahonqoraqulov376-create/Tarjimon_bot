"""Tarjimon bot — kirish nuqtasi.

Ishga tushirish:  python bot.py
"""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramUnauthorizedError
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats

import db
import stt
import translator
from config import LANGS, Config, load_config
from handlers import build_router
from i18n import COMMAND_DESCRIPTIONS
from middlewares import ThrottleMiddleware, UserLangMiddleware

log = logging.getLogger("tarjimon")


async def set_commands(bot: Bot) -> None:
    """Telegram menyusidagi buyruqlar ro'yxati — har bir til uchun alohida.

    Bu bezak, shuning uchun xatolik bo'lsa ham bot ishga tushaveradi.
    """
    scope = BotCommandScopeAllPrivateChats()
    # `None` — Telegram tanimagan tillar uchun standart ro'yxat.
    for lang in (None, *LANGS):
        commands = [
            BotCommand(command=name, description=text)
            for name, text in COMMAND_DESCRIPTIONS[lang or "uz"].items()
        ]
        try:
            await bot.set_my_commands(commands, scope=scope, language_code=lang)
        except TelegramAPIError as exc:
            log.warning("Buyruqlar menyusi o'rnatilmadi (%s): %s", lang, exc)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    # httpx har bir tarjima so'rovini INFO'da yozadi — loglar shovqinga to'ladi.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    config: Config = load_config()

    await db.init(config.db_path)
    stt.setup(config)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher["config"] = config

    # Tartib muhim: avval til aniqlanadi, keyin throttle uni ishlatadi.
    dispatcher.message.outer_middleware(UserLangMiddleware())
    dispatcher.callback_query.outer_middleware(UserLangMiddleware())
    # Throttle faqat xabarlarga — tugma bosish Google'ga so'rov yubormaydi.
    dispatcher.message.outer_middleware(ThrottleMiddleware(config.throttle_sec))

    dispatcher.include_router(build_router())

    unloader = asyncio.create_task(stt.idle_unloader(), name="whisper-idle-unloader")

    try:
        try:
            me = await bot.get_me()
        except TelegramUnauthorizedError:
            log.error(
                "BOT_TOKEN noto'g'ri — Telegram tokenni qabul qilmadi. "
                "@BotFather dan tokenni qayta oling."
            )
            return
        await set_commands(bot)
        log.info(
            "Bot ishga tushdi: @%s | baza: %s | whisper: %s (%s)",
            me.username, config.db_path, config.whisper_model, config.whisper_compute,
        )
        # Eski to'planib qolgan yangilanishlarni tashlab yuboramiz.
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(
            bot,
            allowed_updates=["message", "callback_query"],
        )
    finally:
        unloader.cancel()
        try:
            await unloader
        except asyncio.CancelledError:
            pass
        await translator.close()
        await db.close()
        await bot.session.close()
        log.info("Bot to'xtatildi")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
