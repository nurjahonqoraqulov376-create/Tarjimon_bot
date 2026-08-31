"""Ovozni matnga o'girish (faster-whisper), Railway byudjetiga moslangan.

Railway RAM uchun $10/GB/oy oladi. Whisper modelini doim xotirada ushlab
tursak $5 lik kredit yetmaydi, shuning uchun model:

* birinchi ovozli xabar kelganda yuklanadi (lazy load),
* `WHISPER_IDLE_UNLOAD_SEC` davomida ishlatilmasa xotiradan bo'shatiladi.

Model fayllari Docker image ichida oldindan yuklab qo'yilgan, shuning uchun
qayta yuklash tarmoqqa chiqmaydi va bir necha soniya oladi.
"""

from __future__ import annotations

import asyncio
import ctypes
import gc
import logging
import sys
import time

from config import LANGS, Config

log = logging.getLogger(__name__)

_model = None
_model_lock = asyncio.Lock()
# Bir vaqtning o'zida faqat bitta transkripsiya — CPU sarfini cheklaydi.
_run_sem = asyncio.Semaphore(1)
_last_used = 0.0
_config: Config | None = None

# Qo'llab-quvvatlanadigan tillar ehtimoli shundan past bo'lsa — bu tanish
# nutq emas. Haqiqiy nutqda ehtimol odatda 0.8+, shovqinda esa 0.1 atrofida.
MIN_LANG_PROB = 0.25


def setup(config: Config) -> None:
    global _config
    _config = config


def is_loaded() -> bool:
    return _model is not None


def _load_blocking(model_name: str, compute_type: str):
    from faster_whisper import WhisperModel

    log.info("Whisper modeli yuklanmoqda: %s (%s)", model_name, compute_type)
    started = time.monotonic()
    model = WhisperModel(
        model_name,
        device="cpu",
        compute_type=compute_type,
        cpu_threads=2,
    )
    log.info("Whisper yuklandi (%.1f s)", time.monotonic() - started)
    return model


async def _get_model():
    global _model, _last_used
    async with _model_lock:
        if _model is None:
            assert _config is not None, "stt.setup() chaqirilmagan"
            _model = await asyncio.to_thread(
                _load_blocking, _config.whisper_model, _config.whisper_compute
            )
        _last_used = time.monotonic()
        return _model


def _transcribe_blocking(model, path: str) -> tuple[str, str | None]:
    from faster_whisper.audio import decode_audio

    audio = decode_audio(path, sampling_rate=16000)

    # Whisper 99 ta tilni biladi va shovqinli ovozda mutlaqo boshqa tilni
    # tanlab, ma'nosiz matn qaytarishi mumkin. Biz faqat `LANGS` bilan
    # ishlaymiz — shuning uchun tilni o'zimiz shu ro'yxat ichidan tanlab,
    # transcribe'ga majburan uzatamiz.
    language: str | None = None
    try:
        _, _, all_probs = model.detect_language(
            audio, vad_filter=True, language_detection_segments=2
        )
        probs = {code: prob for code, prob in all_probs if code in LANGS}
        if probs:
            language = max(probs, key=probs.get)
            log.info(
                "Ovoz tili: %s (%s)",
                language,
                ", ".join(f"{c}={probs[c]:.2f}" for c in LANGS if c in probs),
            )
            if probs[language] < MIN_LANG_PROB:
                # Barcha tillarning ehtimoli juda past — bu tanish nutq emas
                # (shovqin, musiqa yoki boshqa til). Majburan tarjima qilsak,
                # ma'nosiz "fonetik" matn chiqadi, shuning uchun rad etamiz.
                log.info("Nutq tanilmadi (eng yuqori ehtimol %.2f)", probs[language])
                return "", None
    except Exception as exc:
        log.warning("Til aniqlanmadi, Whisper o'zi tanlaydi: %s", exc)

    segments, info = model.transcribe(
        audio,
        language=language,
        beam_size=1,          # greedy — CPU'da ancha tez
        vad_filter=True,      # jimlikni tashlab ketadi
        condition_on_previous_text=False,
    )
    text = "".join(segment.text for segment in segments).strip()
    detected = language or (info.language if info.language in LANGS else None)
    return text, detected


async def transcribe(path: str) -> tuple[str, str | None]:
    """Audio faylni matnga o'giradi.

    Qaytaradi: (matn, aniqlangan til yoki None).
    """
    global _last_used
    model = await _get_model()
    async with _run_sem:
        result = await asyncio.to_thread(_transcribe_blocking, model, path)
    _last_used = time.monotonic()
    return result


def _release_memory() -> None:
    """Bo'shatilgan xotirani operatsion tizimga qaytaradi (Linux/glibc).

    `gc.collect()` Python obyektlarini o'chiradi, lekin glibc allokatori
    xotirani o'zida ushlab qolishi mumkin. Railway RAM bo'yicha pul olgani
    uchun uni haqiqatan ham qaytarish muhim.
    """
    if not sys.platform.startswith("linux"):
        return
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception as exc:  # musl (Alpine) da malloc_trim yo'q
        log.debug("malloc_trim ishlamadi: %s", exc)


async def idle_unloader() -> None:
    """Fon vazifasi: bo'sh turgan modelni xotiradan bo'shatadi."""
    global _model
    assert _config is not None, "stt.setup() chaqirilmagan"
    timeout = _config.whisper_idle_unload_sec
    if timeout <= 0:
        return

    while True:
        await asyncio.sleep(30)
        if _model is None or time.monotonic() - _last_used < timeout:
            continue
        async with _model_lock:
            # Qulf kutilayotganda model qayta ishlatilgan bo'lishi mumkin.
            if _model is not None and time.monotonic() - _last_used >= timeout:
                log.info("Whisper bo'sh turdi — xotiradan bo'shatilmoqda")
                _model = None
                gc.collect()
                _release_memory()
