"""Muhit o'zgaruvchilaridan sozlamalarni o'qish."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# Qo'llab-quvvatlanadigan tillar. Kalit tartibi javobdagi tartibni belgilaydi.
LANGS = ("uz", "ru", "en")

LANG_NAMES = {
    "uz": "O'zbekcha",
    "ru": "Русский",
    "en": "English",
}

LANG_FLAGS = {
    "uz": "🇺🇿",
    "ru": "🇷🇺",
    "en": "🇬🇧",
}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip() or default)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "").strip() or default)
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_id: int
    db_path: str
    whisper_model: str
    whisper_compute: str
    whisper_idle_unload_sec: int
    max_voice_sec: int
    throttle_sec: float


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "BOT_TOKEN topilmadi. .env fayliga BOT_TOKEN=... qo'ying "
            "(Railway'da: Variables bo'limiga)."
        )

    return Config(
        bot_token=token,
        admin_id=_int_env("ADMIN_ID", 0),
        db_path=os.getenv("DB_PATH", "").strip() or "bot.db",
        whisper_model=os.getenv("WHISPER_MODEL", "").strip() or "base",
        whisper_compute=os.getenv("WHISPER_COMPUTE", "").strip() or "int8",
        whisper_idle_unload_sec=_int_env("WHISPER_IDLE_UNLOAD_SEC", 300),
        max_voice_sec=_int_env("MAX_VOICE_SEC", 120),
        throttle_sec=_float_env("THROTTLE_SEC", 1.5),
    )
