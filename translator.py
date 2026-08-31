"""Matnni oltala tilga (uz/ru/en/ar/fr/de) tarjima qilish va manba tilini aniqlash.

Ishonchlilik uchun ikkita mustaqil provayder ishlatiladi:

1. **gtx JSON endpoint** (asosiy) — `translate.googleapis.com/translate_a/single`.
   JSON qaytaradi va **aniqlangan manba tilni ham** beradi. Google xato
   sahifasi qaytarsa, u JSON sifatida o'qilmaydi va haqiqiy xato ko'tariladi.
2. **deep-translator** (zaxira) — birinchisi ishlamasa.

Nega bu muhim: `deep-translator` translate.google.com sahifasini "scrape"
qiladi va Google 500 xatosi qaytarganda **xato sahifasining matnini muvaffaqiyatli
tarjima sifatida** qaytaradi ("Error 500 (Server Error)!!1..."). Exception
ko'tarilmagani uchun qayta urinish ham ishlamaydi va foydalanuvchiga axlat
matn boradi. Shuning uchun har bir natija `_looks_like_error_page()` bilan
tekshiriladi.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache

import httpx
from deep_translator import GoogleTranslator

from config import LANGS

log = logging.getLogger(__name__)

# Google'ning bepul endpoint'i bitta so'rovda ~5000 belgini qabul qiladi.
MAX_CHUNK = 4500
# Manba tilni tasdiqlash chegarasi (faqat zaxira yo'l uchun).
SAME_TEXT_RATIO = 0.92

GTX_URL = "https://translate.googleapis.com/translate_a/single"
_TIMEOUT = httpx.Timeout(20.0, connect=10.0)
_HEADERS = {
    # Standart httpx User-Agent'i tez-tez bloklanadi.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

_ATTEMPTS = 3
# Bitta xabar 6 tilga tarjima qilinadi. Oltalasini birdan yuborsak Google'ning
# bepul endpoint'i "unusual traffic" deb bloklab qo'yishi mumkin, shuning uchun
# bir vaqtda nechta so'rov ketishini cheklaymiz.
_MAX_PARALLEL = 3
_client: httpx.AsyncClient | None = None
_gate: asyncio.Semaphore | None = None


def _get_gate() -> asyncio.Semaphore:
    # Semaphore hozirgi event loop'ga bog'lanadi — modul import bo'lganda emas,
    # birinchi ishlatilganda yaratamiz.
    global _gate
    if _gate is None:
        _gate = asyncio.Semaphore(_MAX_PARALLEL)
    return _gate


class TranslationError(RuntimeError):
    """Tarjima xizmatiga ulanib bo'lmadi yoki javob yaroqsiz."""


# --------------------------------------------------------------------------
# Javobni tekshirish
# --------------------------------------------------------------------------

# Google xato sahifalari va bloklash xabarlarining izlari.
_ERROR_SIGNATURES = (
    "that's an error",
    "that’s an error",
    "there was an error",
    "please try again later",
    "that's all we know",
    "that’s all we know",
    "server error)!!",
    "our systems have detected unusual traffic",
    "<!doctype html",
    "<html",
)


def _looks_like_error_page(text: str) -> bool:
    """Tarjima o'rniga Google xato sahifasi kelganini aniqlaydi."""
    low = text.lower()
    return any(sig in low for sig in _ERROR_SIGNATURES)


def _validate(translated: str, provider: str, target: str) -> str:
    if not translated or not translated.strip():
        raise TranslationError(f"{provider}: bo'sh javob ({target})")
    if _looks_like_error_page(translated):
        log.warning(
            "%s xato sahifasini qaytardi (%s): %.120r", provider, target, translated
        )
        raise TranslationError(f"{provider}: xato sahifasi ({target})")
    return translated


# --------------------------------------------------------------------------
# Til aniqlash (heuristika — faqat zaxira yo'l uchun)
# --------------------------------------------------------------------------

_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")
_LATIN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]")
# Arab yozuvi: asosiy blok + qo'shimchalar va taqdimot shakllari.
_ARABIC_RE = re.compile(
    "[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]"
)
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

# Faqat o'zbek kirillida uchraydigan harflar (rus alifbosida yo'q).
_UZ_CYRILLIC_CHARS = set("ўқғҳЎҚҒҲ")

# Lotin yozuvidagi o'zbekcha tutuq belgilari: o‘, g‘, o', g'
_UZ_APOSTROPHE_RE = re.compile(r"[og][‘’ʻʼ'`]", re.IGNORECASE)

_UZ_WORDS = {
    "va", "bilan", "uchun", "men", "sen", "biz", "siz", "ular", "bu", "shu",
    "qanday", "qanaqa", "nima", "kim", "qayer", "qayerdansiz", "qachon",
    "yaxshi", "yomon", "kerak", "bor", "yoq", "yo", "ha", "emas", "ham",
    "lekin", "ammo", "chunki", "salom", "rahmat", "iltimos", "kechirasiz",
    "qalay", "qalaysan", "xayr", "bugun", "ertaga", "kecha", "hozir", "keyin",
    "juda", "koproq", "ozgina", "boldi", "boladi", "qildim", "qilaman",
    "aytdi", "dedi", "bordi", "keldi", "menga", "senga", "bizga", "sizga",
    "uni", "meni", "seni", "ishlar", "yaxshimisiz", "assalomu", "alaykum",
    "tarjima", "til", "gap", "so", "soz",
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

_FR_WORDS = {
    "le", "la", "les", "un", "une", "des", "du", "au", "aux", "et", "est",
    "sont", "je", "tu", "il", "elle", "nous", "vous", "ils", "elles", "que",
    "qui", "quoi", "pour", "avec", "dans", "sur", "pas", "ne", "plus", "mais",
    "comme", "comment", "pourquoi", "quand", "où", "bonjour", "salut", "merci",
    "pardon", "excusez", "bien", "mal", "très", "aujourd", "demain", "hier",
    "maintenant", "avoir", "être", "fait", "faire", "tout", "tous", "toute",
    "cette", "ce", "cet", "mon", "ma", "mes", "ton", "ta", "votre", "vos",
    "son", "sa", "ses", "leur", "chez", "sans", "sous", "aussi", "encore",
    "déjà", "peut", "veux", "veut", "vais", "allez", "ça", "oui", "non",
}

_DE_WORDS = {
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "einem",
    "und", "oder", "aber", "ist", "sind", "war", "waren", "bin", "bist",
    "ich", "du", "er", "sie", "wir", "ihr", "nicht", "kein", "keine", "mit",
    "für", "auf", "von", "zu", "aus", "bei", "nach", "über", "unter", "vor",
    "wie", "was", "wer", "wo", "wann", "warum", "welche", "hallo", "guten",
    "tag", "danke", "bitte", "entschuldigung", "gut", "schlecht", "sehr",
    "heute", "morgen", "gestern", "jetzt", "haben", "hat", "habe", "sein",
    "werden", "wird", "kann", "können", "muss", "soll", "will", "auch",
    "noch", "schon", "immer", "sehen", "machen", "geht", "ja", "nein",
}

# Faqat fransuz/nemis tillariga xos diakritik belgilar.
_FR_DIACRITICS = set("éèêàâçùûîïôœÉÈÊÀÂÇÙÛÎÏÔŒ")
_DE_DIACRITICS = set("äöüßÄÖÜ")


def _words(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


def detect_lang(text: str) -> str:
    """Matn tilini LANGS ichidan taxmin qiladi (tarmoqqa chiqmaydi)."""
    stripped = text.strip()
    if not stripped:
        return "uz"

    arabic = len(_ARABIC_RE.findall(stripped))
    cyrillic = len(_CYRILLIC_RE.findall(stripped))
    latin = len(_LATIN_RE.findall(stripped))
    words = _words(stripped)

    if arabic > cyrillic and arabic > latin:
        return "ar"

    if cyrillic > latin:
        # Kirill: o'zbek kirilliga xos harflar bo'lsa — o'zbekcha, aks holda rus.
        if _UZ_CYRILLIC_CHARS & set(stripped):
            return "uz"
        return "ru"

    if latin == 0:
        return "uz"

    # Lotin yozuvi: o'zbek, ingliz, fransuz yoki nemis.
    scores = {
        "uz": float(sum(w in _UZ_WORDS for w in words)),
        "en": float(sum(w in _EN_WORDS for w in words)),
        "fr": float(sum(w in _FR_WORDS for w in words)),
        "de": float(sum(w in _DE_WORDS for w in words)),
    }

    chars = set(stripped)
    if _UZ_APOSTROPHE_RE.search(stripped):
        scores["uz"] += 2
    if chars & _FR_DIACRITICS:
        scores["fr"] += 2
    if chars & _DE_DIACRITICS:
        scores["de"] += 2

    # "q" va "x" harflari inglizchada juda kam, o'zbekchada tez-tez uchraydi.
    # Fransuzchada esa "que/qui" tufayli "q" ko'p — shuning uchun bu bonusni
    # faqat fransuz/nemis izlari umuman bo'lmaganda beramiz.
    if not scores["fr"] and not scores["de"]:
        low = stripped.lower()
        scores["uz"] += min(low.count("q") + low.count("x"), 4) * 0.5

    best = max(scores, key=lambda lang: scores[lang])
    if scores[best] <= 0:
        # Hech qanday iz yo'q (qisqa matn) — inglizcha ehtimoli yuqoriroq.
        return "en"
    # Teng bo'lsa LANGS tartibi hal qiladi; `max` birinchisini oladi, shuning
    # uchun lug'at tartibi uz -> en -> fr -> de deb ataylab qo'yilgan.
    return best


# --------------------------------------------------------------------------
# Bo'laklarga bo'lish
# --------------------------------------------------------------------------


def _split_chunks(text: str, limit: int = MAX_CHUNK) -> list[str]:
    """Uzun matnni gap chegaralari bo'yicha bo'laklarga ajratadi."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""
    for part in re.split(r"(?<=[.!?…\n])\s+", text):
        while len(part) > limit:
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


# --------------------------------------------------------------------------
# Provayderlar
# --------------------------------------------------------------------------


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=_TIMEOUT,
            headers=_HEADERS,
            limits=httpx.Limits(max_connections=8, max_keepalive_connections=4),
        )
    return _client


async def close() -> None:
    """Bot to'xtaganda HTTP ulanishlarni yopadi."""
    global _client, _gate
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
    # Semaphore yopilgan event loop'ga bog'langan — keyingi ishga tushishda
    # yangisi yaratilsin.
    _gate = None


async def _gtx_chunk(chunk: str, target: str) -> tuple[str, str | None]:
    """gtx JSON endpoint orqali bitta bo'lakni tarjima qiladi."""
    resp = await _get_client().post(
        GTX_URL,
        params={"client": "gtx", "sl": "auto", "tl": target, "dt": "t"},
        data={"q": chunk},
    )
    resp.raise_for_status()
    # Xato sahifasi HTML bo'ladi va bu yerda xato ko'taradi — bizga aynan
    # shu kerak, chunki keyin qayta urinish va zaxira provayder ishlaydi.
    data = resp.json()

    if not isinstance(data, list) or not data or not isinstance(data[0], list):
        raise TranslationError("gtx: kutilmagan javob tuzilishi")

    translated = "".join(seg[0] for seg in data[0] if seg and seg[0])
    detected = data[2] if len(data) > 2 and isinstance(data[2], str) else None
    return translated, detected


async def _translate_gtx(text: str, target: str) -> tuple[str, str | None]:
    parts: list[str] = []
    detected: str | None = None
    for chunk in _split_chunks(text):
        translated, chunk_lang = await _gtx_chunk(chunk, target)
        parts.append(translated)
        detected = detected or chunk_lang
    return _validate(" ".join(parts).strip(), "gtx", target), detected


@lru_cache(maxsize=512)
def _deep_chunk(chunk: str, target: str) -> str:
    """Bitta bo'lakni tarjima qiladi va natijani keshlaydi.

    Tekshiruv ATAYLAB shu yerda — kesh ichida. Agar xato sahifasi kelsa,
    funksiya xato ko'taradi va `lru_cache` hech narsa saqlamaydi. Aks holda
    axlat javob keshga tushib qolar va barcha qayta urinishlar ham o'sha
    axlatni qaytaraverardi.
    """
    raw = GoogleTranslator(source="auto", target=target).translate(chunk) or ""
    return _validate(raw, "deep-translator", target)


def _translate_deep_blocking(text: str, target: str) -> str:
    joined = " ".join(_deep_chunk(chunk, target) for chunk in _split_chunks(text))
    return joined.strip()


async def _translate_deep(text: str, target: str) -> tuple[str, str | None]:
    # deep-translator bloklovchi — alohida threadda ishlatamiz.
    return await asyncio.to_thread(_translate_deep_blocking, text, target), None


async def _translate_one(text: str, target: str) -> tuple[str, str | None]:
    """Bitta tilga tarjima: provayderlar va qayta urinishlar bilan."""
    last_error: Exception | None = None

    for provider_name, provider in (("gtx", _translate_gtx), ("deep", _translate_deep)):
        for attempt in range(1, _ATTEMPTS + 1):
            try:
                async with _get_gate():
                    return await provider(text, target)
            except Exception as exc:
                last_error = exc
                log.warning(
                    "Tarjima muvaffaqiyatsiz [%s -> %s] urinish %d/%d: %s: %s",
                    provider_name, target, attempt, _ATTEMPTS,
                    type(exc).__name__, exc,
                )
                if attempt < _ATTEMPTS:
                    await asyncio.sleep(0.5 * 2 ** (attempt - 1))

    raise TranslationError(f"{target}: {type(last_error).__name__}: {last_error}")


# --------------------------------------------------------------------------
# Asosiy funksiya
# --------------------------------------------------------------------------


@dataclass
class TranslationResult:
    source: str
    """Aniqlangan manba til kodi (uz/ru/en/ar/fr/de)."""
    texts: dict[str, str]
    """Har bir til uchun matn. Manba tilida — asl matnning o'zi."""
    failed: list[str] = field(default_factory=list)
    """Tarjima qilib bo'lmagan tillar (odatda bo'sh)."""


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


async def translate_all(text: str, hint: str | None = None) -> TranslationResult:
    """Matnni `LANGS` dagi barcha tillarga tarjima qiladi va manbani aniqlaydi.

    `hint` — tashqi manbadan (masalan Whisper'dan) kelgan til taxmini.
    Kamida bitta til tarjima qilinsa natija qaytadi; hech biri bo'lmasa
    `TranslationError` ko'tariladi.
    """
    text = text.strip()
    if not text:
        raise ValueError("Bo'sh matn")

    results = await asyncio.gather(
        *(_translate_one(text, lang) for lang in LANGS),
        return_exceptions=True,
    )

    texts: dict[str, str] = {}
    detected_votes: list[str] = []
    failed: list[str] = []
    first_error: Exception | None = None

    for lang, result in zip(LANGS, results):
        if isinstance(result, BaseException):
            failed.append(lang)
            first_error = first_error or result
            continue
        translated, detected = result
        texts[lang] = translated
        if detected in LANGS:
            detected_votes.append(detected)

    if not texts:
        raise TranslationError(str(first_error) if first_error else "noma'lum xato")

    # Manba til: 1) provayder aytgani, 2) tashqi ishora, 3) o'xshashlik,
    # 4) heuristika.
    if detected_votes:
        source = max(set(detected_votes), key=detected_votes.count)
    elif hint in LANGS:
        source = hint
    else:
        ratios = {lang: _similar(text, out) for lang, out in texts.items()}
        best = max(ratios, key=ratios.get)
        source = best if ratios[best] >= SAME_TEXT_RATIO else detect_lang(text)

    # Manba tilda asl matnni ko'rsatamiz — tarjimon uni o'zgartirgan bo'lishi
    # mumkin.
    texts[source] = text
    if source in failed:
        failed.remove(source)

    if failed:
        log.warning("Tarjima qilinmagan tillar: %s", ", ".join(failed))

    return TranslationResult(source=source, texts=texts, failed=failed)


if __name__ == "__main__":
    # Botsiz tez sinov: python translator.py
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    async def _smoke() -> None:
        samples = [
            "Qayerdansiz",
            "Salom, qalaysan? Bugun ishlar yaxshimi?",
            "Привет, как дела? Что нового?",
            "Hello, how are you doing today?",
            "مرحبا، كيف حالك اليوم؟",
            "Bonjour, comment ça va aujourd'hui ?",
            "Hallo, wie geht es dir heute?",
        ]
        for sample in samples:
            res = await translate_all(sample)
            print(f"\n--- {sample!r}  (manba: {res.source}, xato: {res.failed})")
            for lang in LANGS:
                print(f"  {lang}: {res.texts.get(lang)}")

        long_text = "Bu juda uzun matn. " * 400
        res = await translate_all(long_text)
        print(f"\n--- uzun matn ({len(long_text)}) -> en {len(res.texts['en'])} belgi")

        bad = "Error 500 (Server Error)!!1500.That's an error.There was an error."
        print(f"\nXato sahifasi aniqlandimi: {_looks_like_error_page(bad)}")
        await close()

    asyncio.run(_smoke())
