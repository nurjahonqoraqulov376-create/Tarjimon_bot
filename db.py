"""SQLite: foydalanuvchi sozlamalari va statistika.

Bitta ulanish bot ishlagan davomida ochiq turadi (startup'da `init`,
shutdown'da `close`).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import aiosqlite

_conn: aiosqlite.Connection | None = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id    INTEGER PRIMARY KEY,
    ui_lang    TEXT NOT NULL DEFAULT 'uz',
    username   TEXT,
    created_at TEXT NOT NULL,
    last_seen  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stats (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    text_count  INTEGER NOT NULL DEFAULT 0,
    voice_count INTEGER NOT NULL DEFAULT 0
);

INSERT OR IGNORE INTO stats (id, text_count, voice_count) VALUES (1, 0, 0);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _db() -> aiosqlite.Connection:
    if _conn is None:
        raise RuntimeError("Baza ochilmagan: avval db.init() chaqiring")
    return _conn


async def init(path: str) -> None:
    global _conn
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)

    _conn = await aiosqlite.connect(path)
    await _conn.execute("PRAGMA journal_mode=WAL")
    await _conn.execute("PRAGMA synchronous=NORMAL")
    await _conn.executescript(_SCHEMA)
    await _conn.commit()


async def close() -> None:
    global _conn
    if _conn is not None:
        await _conn.close()
        _conn = None


async def get_lang(user_id: int) -> str | None:
    async with _db().execute(
        "SELECT ui_lang FROM users WHERE user_id = ?", (user_id,)
    ) as cur:
        row = await cur.fetchone()
    return row[0] if row else None


async def set_lang(user_id: int, lang: str) -> None:
    now = _now()
    await _db().execute(
        """
        INSERT INTO users (user_id, ui_lang, created_at, last_seen)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET ui_lang = excluded.ui_lang,
                                           last_seen = excluded.last_seen
        """,
        (user_id, lang, now, now),
    )
    await _db().commit()


async def touch_user(user_id: int, username: str | None, default_lang: str) -> str:
    """Foydalanuvchini yozib qo'yadi va uning interfeys tilini qaytaradi."""
    now = _now()
    await _db().execute(
        """
        INSERT INTO users (user_id, ui_lang, username, created_at, last_seen)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET username = excluded.username,
                                           last_seen = excluded.last_seen
        """,
        (user_id, default_lang, username, now, now),
    )
    await _db().commit()

    async with _db().execute(
        "SELECT ui_lang FROM users WHERE user_id = ?", (user_id,)
    ) as cur:
        row = await cur.fetchone()
    return row[0] if row else default_lang


# SQL ichiga qo'yiladigan ustun nomlari faqat shu ro'yxatdan olinadi.
# Ustun nomini parametr sifatida uzatib bo'lmaydi, shuning uchun oldindan
# tayyor so'rovlarni saqlaymiz — tashqaridan kelgan qiymat SQL'ga tushmaydi.
_BUMP_SQL = {
    "text": "UPDATE stats SET text_count = text_count + 1 WHERE id = 1",
    "voice": "UPDATE stats SET voice_count = voice_count + 1 WHERE id = 1",
}


async def bump(kind: str) -> None:
    """`text` yoki `voice` hisoblagichini bittaga oshiradi."""
    sql = _BUMP_SQL.get(kind)
    if sql is None:
        raise ValueError(f"Noma'lum hisoblagich: {kind!r}")
    await _db().execute(sql)
    await _db().commit()


async def get_stats() -> dict[str, int]:
    async with _db().execute(
        "SELECT text_count, voice_count FROM stats WHERE id = 1"
    ) as cur:
        row = await cur.fetchone()
    async with _db().execute("SELECT COUNT(*) FROM users") as cur:
        users_row = await cur.fetchone()
    async with _db().execute(
        "SELECT COUNT(*) FROM users WHERE last_seen >= datetime('now', '-1 day')"
    ) as cur:
        active_row = await cur.fetchone()

    return {
        "users": users_row[0] if users_row else 0,
        "active_24h": active_row[0] if active_row else 0,
        "texts": row[0] if row else 0,
        "voices": row[1] if row else 0,
    }
