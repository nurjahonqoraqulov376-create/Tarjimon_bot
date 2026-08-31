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

NEGA `sl=auto` ISHLATILMAYDI
---------------------------
Google avtomatik aniqlashda ~130 til ichidan tanlaydi va qisqa matnda
muntazam ravishda biz qo'llab-quvvatlamaydigan tilni tanlaydi:

    "Qalaysan"      -> so (somali)    -> tarjima: "Dry" / "Сухой"
    "Rahmat"        -> id (indonez)   -> tarjima: "Grace" / "Милость"
    "Danke schoen"  -> nl (golland)   -> tarjima: "Thank you shoe"

Bitta xato **ikki** joyni buzadi: tarjimaning o'zi noto'g'ri chiqadi va
xabardagi "asl matn" yorlig'i noto'g'ri tilga yopishtiriladi — o'zbekcha matn
"English · asl matn" bo'lib ko'rinadi.

Shuning uchun manba til avval aniqlanadi (`_detect_source`), keyin barcha
tarjimalar **aniq `sl=<manba>`** bilan so'raladi.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache

import httpx
from deep_translator import GoogleTranslator

from config import LANGS

log = logging.getLogger(__name__)

# Google'ning bepul endpoint'i bitta so'rovda ~5000 belgini qabul qiladi.
MAX_CHUNK = 4500
# Ikki matn "aynan bir xil" deb hisoblanadigan o'xshashlik chegarasi.
SAME_TEXT_RATIO = 0.92
# Shundan ko'p bo'lmagan so'zli matn "qisqa" — Google bunda tez-tez adashadi.
SHORT_TEXT_WORDS = 2

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
# Bitta xabar 6 tilga tarjima qilinadi. Hammasini birdan yuborsak Google'ning
# bepul endpoint'i "unusual traffic" deb 302 bilan /sorry/ sahifasiga
# uloqtiradi (sinovda haqiqatan ro'y berdi), shuning uchun cheklaymiz.
_MAX_PARALLEL = 3
# Google bizni bloklaganda (302 -> /sorry/ yoki 429) qolgan tillar uchun ham
# uch martadan urinib ko'rish faqat zarar: javob sekinlashadi va blok yanada
# uzayadi. Blokni ko'rsak, bir muddat to'g'ridan-to'g'ri zaxira provayderga
# o'tamiz.
_GTX_BLOCK_SEC = 120
_BLOCK_STATUSES = frozenset({302, 303, 307, 429})
_gtx_blocked_until = 0.0
_client: httpx.AsyncClient | None = None
_gate: asyncio.Semaphore | None = None


def _gtx_available() -> bool:
    return time.monotonic() >= _gtx_blocked_until


def _note_gtx_error(exc: BaseException) -> None:
    """Xato "bizni bloklashdi" degani bo'lsa, gtx'ni vaqtincha chetlab o'tamiz."""
    global _gtx_blocked_until
    response = getattr(exc, "response", None)
    if getattr(response, "status_code", None) in _BLOCK_STATUSES:
        _gtx_blocked_until = time.monotonic() + _GTX_BLOCK_SEC
        log.warning(
            "gtx bloklandi (HTTP %s) — %d soniya faqat zaxira provayder",
            response.status_code, _GTX_BLOCK_SEC,
        )


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
# Yozuv (script) bo'yicha tillarni chegaralash
# --------------------------------------------------------------------------

_CYRILLIC_RE = re.compile(r"[Ѐ-ԯ]")
_LATIN_RE = re.compile(r"[A-Za-zÀ-ɏ]")
# Arab yozuvi: asosiy blok, qo'shimchalar va taqdimot shakllari.
_ARABIC_RE = re.compile(
    r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]"
)
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

# Har bir yozuvda qaysi tillar bo'lishi mumkin. Yozuv — eng ishonchli dalil:
# arabcha matn hech qachon nemischa bo'lolmaydi, shuning uchun Google nima
# desa ham javobini shu chegara ichiga keltiramiz.
SCRIPT_LANGS: dict[str, tuple[str, ...]] = {
    "arabic": ("ar",),
    "cyrillic": ("ru", "uz"),
    "latin": ("uz", "en", "fr", "de"),
}


def script_of(text: str) -> str:
    """Matn qaysi yozuvda yozilganini aniqlaydi."""
    arabic = len(_ARABIC_RE.findall(text))
    cyrillic = len(_CYRILLIC_RE.findall(text))
    latin = len(_LATIN_RE.findall(text))
    if arabic and arabic >= cyrillic and arabic >= latin:
        return "arabic"
    if cyrillic and cyrillic >= latin:
        return "cyrillic"
    return "latin"


# Google qaytargan, lekin biz qo'llab-quvvatlamaydigan tillarni eng yaqin
# "o'z" tilimizga keltiramiz. Ro'yxat sinovda kuzatilgan haqiqiy
# adashishlarga asoslangan: uz -> so/id, de -> nl, fr -> ca.
_NEAREST = {
    # Turkiy va agglyutinativ tillar — o'zbekcha ko'pincha shular deb o'qiladi.
    "so": "uz", "id": "uz", "ms": "uz", "tr": "uz", "az": "uz", "tk": "uz",
    "kk": "uz", "ky": "uz", "jw": "uz", "jv": "uz", "su": "uz", "tl": "uz",
    "fil": "uz", "sw": "uz", "ha": "uz", "mi": "uz", "haw": "uz", "mg": "uz",
    "ceb": "uz", "ny": "uz", "st": "uz", "zu": "uz", "xh": "uz", "sn": "uz",
    "yo": "uz", "ig": "uz", "sm": "uz", "eu": "uz", "et": "uz", "fi": "uz",
    "hu": "uz", "lv": "uz", "lt": "uz",
    # German tillari.
    "nl": "de", "af": "de", "lb": "de", "da": "de", "sv": "de", "no": "de",
    "nb": "de", "nn": "de", "is": "de", "fy": "de", "yi": "de",
    # Roman tillari.
    "ca": "fr", "oc": "fr", "ht": "fr", "co": "fr", "es": "fr", "it": "fr",
    "pt": "fr", "ro": "fr", "gl": "fr", "la": "fr", "rm": "fr", "wa": "fr",
    # Kirill yozuvidagi tillar.
    "uk": "ru", "be": "ru", "bg": "ru", "sr": "ru", "mk": "ru", "mn": "ru",
    "tg": "ru", "tt": "ru", "ba": "ru", "cv": "ru", "ce": "ru",
    # Arab yozuvidagi tillar.
    "fa": "ar", "ur": "ar", "ps": "ar", "sd": "ar", "ug": "ar", "ku": "ar",
    "ckb": "ar", "he": "ar", "iw": "ar",
    # Ingliz tiliga yaqinlar.
    "sco": "en", "gd": "en", "ga": "en", "cy": "en", "mt": "en",
}


def _to_supported(code: str | None, script: str) -> str | None:
    """Google aytgan til kodini shu yozuvda mumkin bo'lgan tilimizga keltiradi."""
    if not code:
        return None
    base = code.split("-")[0].lower()
    lang = base if base in LANGS else _NEAREST.get(base)
    if lang is None:
        return None
    # Yozuv mos kelmasa ishonmaymiz — masalan lotin matnga "ru" degan javob.
    return lang if lang in SCRIPT_LANGS[script] else None


# --------------------------------------------------------------------------
# Oflayn heuristika — Google bloklanganda ishlaydigan zaxira yo'l
# --------------------------------------------------------------------------

# Faqat o'zbek kirillida uchraydigan harflar (rus alifbosida yo'q).
_UZ_CYRILLIC_CHARS = set("ўқғҳЎҚҒҲ")

# Lotin yozuvidagi o'zbekcha tutuq belgilari: o‘, g‘, o', g'
_UZ_APOSTROPHE_RE = re.compile(r"[og][‘’ʻʼ'`]", re.IGNORECASE)

# O'zbekcha qo'shimchalar — bitta so'zli matnni ham tanishga yordam beradi.
_UZ_SUFFIXES = (
    "lar", "ning", "dan", "ga", "da", "ni", "moq", "yapman", "yapti",
    "gan", "yotgan", "miz", "ngiz", "chi", "lik", "imiz",
)

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
    # Kundalik otlar — qisqa xabarlar ko'pincha shulardan iborat bo'ladi.
    "kitob", "suv", "non", "uy", "ish", "bola", "ona", "ota", "aka", "opa",
    "kun", "tun", "yil", "oy", "hafta", "vaqt", "odam", "dost", "sinf",
    "maktab", "universitet", "shahar", "qishloq", "yol", "mashina", "pul",
    "ovqat", "choy", "osh", "meva", "olma", "gul", "quyosh", "osmon", "havo",
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


# Shundan yuqori ball "haqiqiy dalil" hisoblanadi: lug'atdagi so'z, o'zbekcha
# tutuq belgisi yoki fransuz/nemis diakritikasi topilgan. Taxminiy "q/x"
# bonusi bu chegaraga yetmaydi.
EVIDENCE_SCORE = 1.0


def _latin_scores(text: str) -> dict[str, float]:
    """Lotin yozuvidagi matn uchun har bir tilning dalil ballari."""
    words = _words(text)
    scores = {
        "uz": float(sum(w in _UZ_WORDS for w in words)),
        "en": float(sum(w in _EN_WORDS for w in words)),
        "fr": float(sum(w in _FR_WORDS for w in words)),
        "de": float(sum(w in _DE_WORDS for w in words)),
    }

    chars = set(text)
    if _UZ_APOSTROPHE_RE.search(text):
        scores["uz"] += 2
    if chars & _FR_DIACRITICS:
        scores["fr"] += 2
    if chars & _DE_DIACRITICS:
        scores["de"] += 2

    # O'zbekcha qo'shimchalar — "kitoblar", "uyga" kabi so'zlarni tanitadi.
    scores["uz"] += 0.5 * sum(
        any(w.endswith(sfx) and len(w) > len(sfx) + 1 for sfx in _UZ_SUFFIXES)
        for w in words
    )

    # "q" va "x" harflari inglizchada juda kam, o'zbekchada tez-tez uchraydi.
    # Fransuzchada esa "que/qui" tufayli "q" ko'p — shuning uchun bu bonusni
    # faqat fransuz/nemis izlari umuman bo'lmaganda beramiz.
    if not scores["fr"] and not scores["de"]:
        low = text.lower()
        scores["uz"] += min(low.count("q") + low.count("x"), 4) * 0.5

    return scores


def offline_vote(text: str, prefer: str | None = None) -> tuple[str, float]:
    """Tilni tarmoqqa chiqmasdan taxmin qiladi.

    Qaytaradi: `(til, dalil balli)`. Ball `EVIDENCE_SCORE` dan kichik bo'lsa
    bu shunchaki taxmin — unga tayanmaslik kerak.

    `prefer` — ballar teng chiqqanda ustun turadigan til (odatda
    foydalanuvchining interfeys tili). "Non" ham o'zbekcha, ham fransuzcha:
    kim yozganiga qarab hal qilamiz.
    """
    stripped = text.strip()
    if not stripped:
        return "uz", 0.0

    script = script_of(stripped)
    if script == "arabic":
        # Yozuvning o'zi to'liq dalil — arab yozuvida boshqa tilimiz yo'q.
        return "ar", 10.0

    if script == "cyrillic":
        if _UZ_CYRILLIC_CHARS & set(stripped):
            return "uz", 10.0
        hits = sum(w in _RU_WORDS for w in _words(stripped))
        # Kirillda rus tili — oqilona standart, hatto dalilsiz ham.
        return "ru", float(hits) if hits else EVIDENCE_SCORE

    scores = _latin_scores(stripped)
    best = max(
        scores,
        # Teng bo'lsa `prefer`, undan keyin LANGS tartibi hal qiladi.
        key=lambda lang: (scores[lang], lang == prefer),
    )
    return best, scores[best]


def detect_lang(text: str, prefer: str | None = None) -> str:
    """Matn tilini LANGS ichidan taxmin qiladi (tarmoqqa chiqmaydi).

    Bu **zaxira** yo'l: Google bloklaganda yoki javob bermaganda ishlatiladi.
    """
    lang, score = offline_vote(text, prefer)
    if score <= 0:
        # Hech qanday iz yo'q — interfeys tili bo'lmasa, inglizcha ehtimoli
        # yuqoriroq.
        return prefer or "en"
    return lang


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


def _get_gate() -> asyncio.Semaphore:
    # Semaphore hozirgi event loop'ga bog'lanadi — modul import bo'lganda emas,
    # birinchi ishlatilganda yaratamiz.
    global _gate
    if _gate is None:
        _gate = asyncio.Semaphore(_MAX_PARALLEL)
    return _gate


# Bir xil so'rovni ikki marta yubormaslik uchun kichik kesh. Bot ko'p hollarda
# takrorlanuvchi qisqa iboralarni tarjima qiladi, kesh esa Google'ning
# "unusual traffic" blokiga tushish ehtimolini sezilarli kamaytiradi.
_CACHE_SIZE = 512
# Kalit: (sl, tl, bo'lak) -> (tarjima, Google aniqlagan til).
# Aniqlangan tilni ham saqlaymiz: `sl=auto` so'rovi keshdan olinganda manba
# til yo'qolib qolsa, o'sha matn ikkinchi marta boshqacha yorliq olardi.
_cache: OrderedDict[tuple[str, str, str], tuple[str, str | None]] = OrderedDict()


def _cache_get(key: tuple[str, str, str]) -> tuple[str, str | None] | None:
    value = _cache.get(key)
    if value is not None:
        _cache.move_to_end(key)
    return value


def _cache_put(key: tuple[str, str, str], value: tuple[str, str | None]) -> None:
    _cache[key] = value
    _cache.move_to_end(key)
    while len(_cache) > _CACHE_SIZE:
        _cache.popitem(last=False)


async def close() -> None:
    """Bot to'xtaganda HTTP ulanishlarni yopadi."""
    global _client, _gate
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
    # Semaphore yopilgan event loop'ga bog'langan — keyingi ishga tushishda
    # yangisi yaratilsin.
    _gate = None


async def _gtx_chunk(chunk: str, target: str, source: str) -> tuple[str, str | None]:
    """gtx JSON endpoint orqali bitta bo'lakni tarjima qiladi."""
    resp = await _get_client().post(
        GTX_URL,
        params={"client": "gtx", "sl": source, "tl": target, "dt": "t"},
        data={"q": chunk},
    )
    # 302 — Google "unusual traffic" deb /sorry/ sahifasiga uloqtiradi.
    # raise_for_status() buni ham xato deb ko'taradi va zaxira yo'l ishlaydi.
    resp.raise_for_status()
    # Xato sahifasi HTML bo'ladi va bu yerda xato ko'taradi — bizga aynan
    # shu kerak, chunki keyin qayta urinish va zaxira provayder ishlaydi.
    data = resp.json()

    if not isinstance(data, list) or not data or not isinstance(data[0], list):
        raise TranslationError("gtx: kutilmagan javob tuzilishi")

    translated = "".join(seg[0] for seg in data[0] if seg and seg[0])
    detected = data[2] if len(data) > 2 and isinstance(data[2], str) else None
    return translated, detected


async def _translate_gtx(
    text: str, target: str, source: str = "auto"
) -> tuple[str, str | None]:
    parts: list[str] = []
    detected: str | None = None
    for chunk in _split_chunks(text):
        cached = _cache_get((source, target, chunk))
        if cached is not None:
            translated, chunk_lang = cached
        else:
            translated, chunk_lang = await _gtx_chunk(chunk, target, source)
            # Tekshiruv keshdan OLDIN: axlat javob keshga tushib qolmasin.
            _validate(translated, "gtx", target)
            _cache_put((source, target, chunk), (translated, chunk_lang))
        parts.append(translated)
        detected = detected or chunk_lang
    joined = _validate(" ".join(parts).strip(), "gtx", target)
    return joined, detected or (None if source == "auto" else source)


@lru_cache(maxsize=512)
def _deep_chunk(chunk: str, target: str, source: str) -> str:
    """Bitta bo'lakni tarjima qiladi va natijani keshlaydi.

    Tekshiruv ATAYLAB shu yerda — kesh ichida. Agar xato sahifasi kelsa,
    funksiya xato ko'taradi va `lru_cache` hech narsa saqlamaydi. Aks holda
    axlat javob keshga tushib qolar va barcha qayta urinishlar ham o'sha
    axlatni qaytaraverardi.
    """
    raw = GoogleTranslator(source=source, target=target).translate(chunk) or ""
    return _validate(raw, "deep-translator", target)


def _translate_deep_blocking(text: str, target: str, source: str) -> str:
    joined = " ".join(
        _deep_chunk(chunk, target, source) for chunk in _split_chunks(text)
    )
    return joined.strip()


async def _translate_deep(
    text: str, target: str, source: str = "auto"
) -> tuple[str, str | None]:
    # deep-translator bloklovchi — alohida threadda ishlatamiz.
    out = await asyncio.to_thread(_translate_deep_blocking, text, target, source)
    return out, (None if source == "auto" else source)


async def _translate_one(
    text: str, target: str, source: str = "auto"
) -> tuple[str, str | None]:
    """Bitta tilga tarjima: provayderlar va qayta urinishlar bilan."""
    last_error: Exception | None = None

    for provider_name, provider in (("gtx", _translate_gtx), ("deep", _translate_deep)):
        if provider_name == "gtx" and not _gtx_available():
            continue
        for attempt in range(1, _ATTEMPTS + 1):
            try:
                async with _get_gate():
                    return await provider(text, target, source)
            except Exception as exc:
                last_error = exc
                if provider_name == "gtx":
                    _note_gtx_error(exc)
                    if not _gtx_available():
                        break   # blok — qolgan urinishlar behuda
                log.warning(
                    "Tarjima muvaffaqiyatsiz [%s: %s -> %s] urinish %d/%d: %s: %s",
                    provider_name, source, target, attempt, _ATTEMPTS,
                    type(exc).__name__, exc,
                )
                if attempt < _ATTEMPTS:
                    # Jitter: barcha tillar bir vaqtda qayta urinib, Google'ni
                    # yana bloklashga majburlamasin.
                    await asyncio.sleep(0.5 * 2 ** (attempt - 1) * (1 + random.random()))

    raise TranslationError(f"{target}: {type(last_error).__name__}: {last_error}")


# --------------------------------------------------------------------------
# Manba tilni aniqlash
# --------------------------------------------------------------------------


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _pivot_for(lang: str) -> str:
    """Zond uchun boshqa til — matn haqiqatan tarjima bo'lganini shu ko'rsatadi."""
    return "ru" if lang == "en" else "en"


async def _detect_source(
    text: str, ui_lang: str | None, hint: str | None
) -> tuple[str, dict[str, str]]:
    """Manba tilni aniqlaydi.

    Qaytaradi: `(manba til, yo'l-yo'lakay olingan tarjimalar)`.

    Yozuv (arab/kirill/lotin) tilni allaqachon chegaralaydi; qolganini Google
    aniqlaydi, biz esa uning javobini shu chegara ichiga keltiramiz.
    """
    script = script_of(text)
    allowed = SCRIPT_LANGS[script]
    if len(allowed) == 1:
        return allowed[0], {}

    known: dict[str, str] = {}
    source: str | None = None

    # Bitta so'rov ikki ish qiladi: tilni aniqlaydi va tayyor tarjima beradi.
    pivot = _pivot_for(ui_lang if ui_lang in allowed else allowed[0])
    if _gtx_available():
        try:
            translated, raw = await _translate_gtx(text, pivot)
            mapped = _to_supported(raw, script)
            if mapped:
                source = mapped
                # Tarjimani faqat Google haqiqatan to'g'ri tilni ko'rgan bo'lsa
                # ishlatamiz: "so"/"id" deb o'qigan bo'lsa natija ham axlat.
                if raw and raw.split("-")[0].lower() == mapped:
                    known[pivot] = translated
            else:
                log.info("Google qo'llanmaydigan tilni aytdi: %r", raw)
        except Exception as exc:
            _note_gtx_error(exc)
            log.warning("Til aniqlash so'rovi muvaffaqiyatsiz: %s", exc)

    if source is None:
        source = hint if hint in allowed else detect_lang(text, prefer=ui_lang)
        known.clear()

    if len(_words(text)) > SHORT_TEXT_WORDS:
        # Uzun matnda Google ancha ishonchli — javobiga tegmaymiz.
        return source, known

    # Qisqa matnda Google bitta so'zga qarab hukm chiqaradi va adashadi:
    # "Bonjour" ni inglizcha deb o'qidi. Bizning lug'atimizda haqiqiy dalil
    # bo'lsa (lug'atdagi so'z, diakritika, tutuq belgisi) — o'shanga ishonamiz.
    vote, score = offline_vote(text, prefer=ui_lang)
    if score >= EVIDENCE_SCORE and vote in allowed:
        if vote != source:
            log.info(
                "Qisqa matn %r: Google %r dedi, lug'at dalili %r ko'rsatdi",
                text, source, vote,
            )
            source, known = vote, {}
        # Dalil bor ekan, quyidagi zond faqat zarar keltirishi mumkin.
        return source, known

    # Dalil topilmagan qisqa matn hali ham ikki ma'noli: "Suv" ni Google en
    # (SUV) deydi. Foydalanuvchining interfeys tili kuchli ishora — shu tildan
    # tarjima matnni haqiqatan o'zgartirsa, demak matn o'sha tilda yozilgan.
    # Inglizcha "Hello" ni o'zbekchadan tarjima qilsak o'zgarmaydi va biz
    # Google aytgan tilda qolamiz.
    if ui_lang in allowed and source != ui_lang and _gtx_available():
        probe_target = _pivot_for(ui_lang)
        try:
            out, _ = await _translate_gtx(text, probe_target, source=ui_lang)
            if _similar(text, out) < SAME_TEXT_RATIO:
                log.info(
                    "Qisqa matn %r: %r o'rniga interfeys tili %r tanlandi",
                    text, source, ui_lang,
                )
                source, known = ui_lang, {probe_target: out}
        except Exception as exc:
            log.warning("Interfeys tili zondi muvaffaqiyatsiz: %s", exc)

    return source, known


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


async def translate_all(
    text: str, hint: str | None = None, ui_lang: str | None = None
) -> TranslationResult:
    """Matnni `LANGS` dagi barcha tillarga tarjima qiladi va manbani aniqlaydi.

    `hint` — tashqi manbadan (Whisper'dan) kelgan til taxmini.
    `ui_lang` — foydalanuvchining interfeys tili; qisqa, ikki ma'noli
    matnlarda hal qiluvchi ishora bo'ladi.

    Kamida bitta tilga tarjima qilinsa natija qaytadi; hech biri bo'lmasa
    `TranslationError` ko'tariladi.
    """
    text = text.strip()
    if not text:
        raise ValueError("Bo'sh matn")

    source, known = await _detect_source(text, ui_lang, hint)

    targets = [lang for lang in LANGS if lang != source and lang not in known]
    results = await asyncio.gather(
        *(_translate_one(text, lang, source) for lang in targets),
        return_exceptions=True,
    )

    # Manba tilda asl matnni ko'rsatamiz — tarjimon uni o'zgartirgan bo'lishi
    # mumkin.
    texts: dict[str, str] = {source: text, **known}
    failed: list[str] = []
    first_error: Exception | None = None

    for lang, result in zip(targets, results):
        if isinstance(result, BaseException):
            failed.append(lang)
            first_error = first_error or result
            continue
        texts[lang] = result[0]

    # Faqat asl matn qolgan bo'lsa — bu tarjima emas, xato.
    if len(texts) <= 1:
        raise TranslationError(str(first_error) if first_error else "noma'lum xato")

    if failed:
        log.warning("Tarjima qilinmagan tillar: %s", ", ".join(failed))

    return TranslationResult(source=source, texts=texts, failed=failed)


if __name__ == "__main__":
    # Botsiz tez sinov: python translator.py
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    async def _smoke() -> None:
        # (matn, foydalanuvchining interfeys tili, kutilgan manba til)
        samples = [
            ("Kitob", "uz", "uz"),
            ("Qalaysan", "uz", "uz"),
            ("Rahmat", "uz", "uz"),
            ("Salom, qalaysan? Bugun ishlar yaxshimi?", "uz", "uz"),
            ("Привет, как дела? Что нового?", "ru", "ru"),
            ("Hello, how are you doing today?", "uz", "en"),
            ("مرحبا، كيف حالك اليوم؟", "uz", "ar"),
            ("Bonjour, comment ça va aujourd'hui ?", "uz", "fr"),
            ("Danke schoen", "uz", "de"),
        ]
        for sample, ui, want in samples:
            res = await translate_all(sample, ui_lang=ui)
            mark = "OK  " if res.source == want else "XATO"
            print(f"\n{mark} {sample!r} manba={res.source} (kutilgan {want})")
            for lang in LANGS:
                print(f"     {lang}: {res.texts.get(lang)}")

        bad = "Error 500 (Server Error)!!1500.That's an error.There was an error."
        print(f"\nXato sahifasi aniqlandimi: {_looks_like_error_page(bad)}")
        await close()

    asyncio.run(_smoke())
