"""Barcha router'larni bitta joyga yig'adi.

Tartib muhim: buyruqlar birinchi, `fallback` esa eng oxirida turishi shart —
u ushlanmagan hamma narsani qamrab oladi.
"""

from aiogram import Router

from . import commands, fallback, text, voice


def build_router() -> Router:
    router = Router(name="root")
    router.include_router(commands.router)
    router.include_router(text.router)
    router.include_router(voice.router)
    router.include_router(fallback.router)
    return router


__all__ = ["build_router"]
