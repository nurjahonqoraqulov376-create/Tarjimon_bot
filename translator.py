"""Matnni uchala tilga (uz/ru/en) tarjima qilish va manba tilini aniqlash.

deep-translator manba tilini qaytarmaydi, `langdetect` esa o'zbek tilini bilmaydi.
Shuning uchun manba til ikki bosqichda aniqlanadi:

1. Heuristika — alifbo, o'zbekcha/inglizcha markerlar va stopword'lar bo'yicha.
2. Tasdiqlash — matn baribir uchala tilga tarjima qilinadi, manba tilga tarjima
   natijasi kirish matniga deyarli teng chiqadi. Bu qo'shimcha so'rov talab
   qilmaydi va heuristikaning xatosini tuzatadi.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache

from deep_translator import GoogleTranslator

from config import LANGS

log = logging.getLogger(__name__)

# Google'ning bepul endpoint'i bitta so'rovda ~5000 belgini qabul qiladi.
MAX_CHUNK = 4500
# Manba tilni tasdiqlash chegarasi: tarjima kirish matniga shunchalik o'xshasa,
# demak bu til matnning o'z tili.
SAME_TEXT_RATIO = 0.92

_RETRIES = 3


# --------------------------------------------------------------------------
# Til aniqlash (heuristika)
# --------------------------------------------------------------------------

_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

# Faqat o'zbek kirillida uchraydigan harflar (rus alifbosida yo'q).
_UZ_CYRILLIC_CHARS = set("ўқғҳЎҚҒҲ")

# Lotin yozuvidagi o'zbekcha tutuq belgilari: o‘, g‘, o', g'
_UZ_APOSTROPHE_RE = re.compile(r"[og][‘’ʻʼ'`]", re.IGNORECASE)

_UZ_WORDS = {
    "va", "bilan", "uchun", "men", "sen", "biz", "siz", "ular", "bu", "shu",
    "qanday", "qanaqa", "nima", "kim", "qayer", "qachon", "yaxshi", "yomon",
    "kerak", "bor", "yoq", "yo", "ha", "emas", "ham", "lekin", "ammo", "chunki",
    "salom", "rahmat", "iltimos", "kechirasiz", "qalay", "qalaysan", "xayr",
    "bugun", "ertaga", "kecha", "hozir", "keyin", "juda", "koproq", "ozgina",
    "boldi", "boladi", "qildim", "qilaman", "aytdi", "dedi", "bordi", "keldi",
    "menga", "senga", "bizga", "sizga", "uni", "meni", "seni", "ishlar",
    "yaxshimisiz", "assalomu", "alaykum", "tarjima", "til", "gap", "so", "soz",
}

_EN_WORDS = {
    "the", "is", "are", "was", "were", "and", "or", "but", "you", "your",
    "what", "when", "where", "who", "how", "why", "this", "that", "these",
    "with", "for", "from", "have", "has", "had", "will", "would", "can",
    "could", "should", "there", "here", "they", "them", "their", "his", "her",
    "hello", "thanks", "thank", "please", "sorry", "good", "bad", "very",
    "about", "into", "over", "after", "before", "because", "which", "been",
    "does", "did", "not", "all", "some", "any", "more", "than", "then",
}

_RU_WORDS = {
    "и", "в", "не", "на", "я", "что", "тот", "быть", "с", "он", "как", "это",
    "по", "но", "они", "мы", "вы", "она", "так", "его", "все", "у", "же",
    "привет", "спасибо", "пожалуйста", "извините", "хорошо", "плохо", "очень",
    "дела", "сейчас", "завтра", "сегодня", "вчера", "меня", "тебя", "нас",
}


def _words(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


def detect_lang(text: str) -> str:
    """Matn tilini uz/ru/en orasidan taxmin qiladi (tarmoqqa chiqmaydi)."""
    stripped = text.strip()
    if not stripped:
        return "uz"

    cyrillic = len(_CYRILLIC_RE.findall(stripped))
    latin = len(_LATIN_RE.findall(stripped))
    words = _words(stripped)

    if cyrillic > latin:
        # Kirill: rus yoki o'zbek kirilli.
        if _UZ_CYRILLIC_CHARS & set(stripped):
            return "uz"
        if words and sum(w in _RU_WORDS for w in words) == 0:
            # Ruscha stopword umuman yo'q — o'zbek kirilli bo'lishi mumkin,
            # lekin ishonch kam, shuning uchun baribir "ru" deymiz.
            return "ru"
        return "ru"

    if latin == 0:
        return "uz"

    # Lotin: o'zbek yoki ingliz.
    uz_score = sum(w in _UZ_WORDS for w in words)
    en_score = sum(w in _EN_WORDS for w in words)

    if _UZ_APOSTROPHE_RE.search(stripped):
        uz_score += 2

    # "q" va "x" harflari inglizchada juda kam, o'zbekchada tez-tez uchraydi.
    low = stripped.lower()
    uz_score += min(low.count("q") + low.count("x"), 4) * 0.5

    if uz_score > en_score:
        return "uz"
    if en_score > uz_score:
        return "en"
    # Teng bo'lsa — inglizcha ehtimoli yuqoriroq (qisqa matnlar uchun).
    return "en"


# --------------------------------------------------------------------------
# Tarjima
# --------------------------------------------------------------------------


def _split_chunks(text: str, limit: int = MAX_CHUNK) -> list[str]:
    """Uzun matnni gap chegaralari bo'yicha bo'laklarga ajratadi."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""
    # Gap oxiri yoki qator boshi bo'yicha bo'lamiz.
    for part in re.split(r"(?<=[.!?…\n])\s+", text):
        while len(part) > limit:
            # Bitta "gap" ham juda uzun bo'lsa — majburan kesamiz.
            if current:
                chunks.append(current)
                current = ""
            chunks.append(part[:limit])
            part = part[limit:]
        if len(current) + len(part) + 1 > limit:
            chunks.append(current)
            current = part
        else:
            current = f"{current} {part}".strip() if current else part
    if current:
        chunks.append(current)
    return chunks


@lru_cache(maxsize=512)
def _translate_chunk(chunk: str, target: str) -> str:
    """Bitta bo'lakni tarjima qiladi. Natija keshlanadi."""
    return GoogleTranslator(source="auto", target=target).translate(chunk) or ""


def _translate_sync(text: str, target: str) -> str:
    """Bloklovchi tarjima (thread ichida chaqiriladi), qayta urinish bilan."""
    last_error: Exception | None = None
    for attempt in range(_RETRIES):
        try:
            return " ".join(
                _translate_chunk(chunk, target) for chunk in _split_chunks(text)
            ).strip()
        except Exception as exc:  # deep_translator turli xatolar tashlaydi
            last_error = exc
            log.warning(
                "Tarjima xatosi (%s, urinish %d/%d): %s",
                target, attempt + 1, _RETRIES, exc,
            )
            if attempt < _RETRIES - 1:
                # Alohida thread ichida ishlaymiz — event loop bloklanmaydi.
                time.sleep(0.6 * (2**attempt))
    raise TranslationError(str(last_error)) from last_error


class TranslationError(RuntimeError):
    """Tarjima xizmatiga ulanib bo'lmadi."""


@dataclass
class TranslationResult:
    source: str
    """Aniqlangan manba til kodi (uz/ru/en)."""
    texts: dict[str, str]
    """Har bir til uchun matn. Manba tilida — asl matnning o'zi."""


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


async def translate_all(text: str, hint: str | None = None) -> TranslationResult:
    """Matnni uchala tilga tarjima qiladi va manba tilini aniqlaydi.

    `hint` — tashqi manbadan (masalan Whisper'dan) kelgan til taxmini.
    """
    text = text.strip()
    if not text:
        raise ValueError("Bo'sh matn")

    results = await asyncio.gather(
        *(asyncio.to_thread(_translate_sync, text, lang) for lang in LANGS),
        return_exceptions=True,
    )

    texts: dict[str, str] = {}
    errors: list[Exception] = []
    for lang, result in zip(LANGS, results):
        if isinstance(result, Exception):
            errors.append(result)
        elif result:
            texts[lang] = result

    if not texts:
        raise TranslationError(str(errors[0]) if errors else "noma'lum xato")

    # Manba tilni aniqlash: tarjimasi asl matnga eng o'xshash til.
    ratios = {lang: _similar(text, out) for lang, out in texts.items()}
    best_lang = max(ratios, key=ratios.get)
    if ratios[best_lang] >= SAME_TEXT_RATIO:
        source = best_lang
    elif hint in LANGS:
        source = hint
    else:
        source = detect_lang(text)

    # Manba tilda asl matnni ko'rsatamiz — Google uni "tarjima" qilib
    # o'zgartirib yuborgan bo'lishi mumkin.
    texts[source] = text
    return TranslationResult(source=source, texts=texts)


if __name__ == "__main__":
    # Botsiz tez sinov: python translator.py
    logging.basicConfig(level=logging.INFO)

    async def _smoke() -> None:
        samples = [
            "Salom, qalaysan? Bugun ishlar yaxshimi?",
            "Привет, как дела? Что нового?",
            "Hello, how are you doing today?",
        ]
        for sample in samples:
            res = await translate_all(sample)
            print(f"\n--- {sample!r}")
            print(f"heuristika: {detect_lang(sample)} | aniqlangan: {res.source}")
            for lang in LANGS:
                print(f"  {lang}: {res.texts.get(lang)}")

        long_text = "Bu juda uzun matn. " * 400
        res = await translate_all(long_text)
        print(f"\n--- uzun matn ({len(long_text)} belgi) -> {len(res.texts['en'])} belgi (en)")

    asyncio.run(_smoke())
