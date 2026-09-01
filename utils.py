"""Kichik yordamchi funksiyalar."""

from __future__ import annotations

import ctypes
import os
import sys


def rss_mb() -> int:
    """Jarayonning joriy RAM sarfi (MB). Qo'shimcha kutubxonasiz.

    Railway RAM bo'yicha pul oladi, shuning uchun buni /stats da ko'rsatamiz.
    """
    try:
        if sys.platform.startswith("linux"):
            with open("/proc/self/statm", encoding="ascii") as fh:
                pages = int(fh.read().split()[1])
            return pages * os.sysconf("SC_PAGE_SIZE") // (1024 * 1024)

        if sys.platform == "win32":
            class _Counters(ctypes.Structure):
                _fields_ = [
                    ("cb", ctypes.c_uint32),
                    ("PageFaultCount", ctypes.c_uint32),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            kernel32 = ctypes.WinDLL("kernel32")
            psapi = ctypes.WinDLL("psapi")
            # Handle 64-bit bo'lgani uchun restype/argtypes ni aniq beramiz,
            # aks holda ctypes uni 32-bit int ga qisqartiradi.
            kernel32.GetCurrentProcess.restype = ctypes.c_void_p
            psapi.GetProcessMemoryInfo.argtypes = [
                ctypes.c_void_p, ctypes.POINTER(_Counters), ctypes.c_uint32
            ]
            psapi.GetProcessMemoryInfo.restype = ctypes.c_int

            counters = _Counters()
            counters.cb = ctypes.sizeof(counters)
            if psapi.GetProcessMemoryInfo(
                kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
            ):
                return counters.WorkingSetSize // (1024 * 1024)
            return 0

        import resource  # noqa: PLC0415 — faqat POSIX'da mavjud

        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux'da KB, macOS'da bayt.
        return peak // 1024 if sys.platform != "darwin" else peak // (1024 * 1024)
    except Exception:
        return 0


# Telegram xabarining chegarasi. Diqqat: Telegram uzunlikni **UTF-16 kod
# birliklarida** sanaydi, Python esa kod nuqtalarida. 🇺🇿 kabi bayroq emoji
# Python uchun 2 belgi, Telegram uchun esa 4 birlik — shuning uchun oddiy
# `len()` ga tayanib bo'lmaydi.
TELEGRAM_LIMIT = 4096
# Zaxira qoldiramiz: xabar chekkasida qo'shiladigan narsalar bo'lishi mumkin.
SAFE_LIMIT = 3800


def tg_len(text: str) -> int:
    """Telegram xabarni qanday o'lchasa, shunday o'lchaydi (UTF-16 birliklar)."""
    return sum(2 if ord(ch) > 0xFFFF else 1 for ch in text)


def _prefix_len(text: str, limit: int) -> int:
    """`limit` UTF-16 birlikka sig'adigan belgilar sonini qaytaradi."""
    total = 0
    for index, ch in enumerate(text):
        total += 2 if ord(ch) > 0xFFFF else 1
        if total > limit:
            return index
    return len(text)


def _hard_split(text: str, limit: int) -> list[str]:
    """Bitta juda uzun qatorni bo'ladi — so'z chegarasini afzal ko'radi.

    Bo'sh joyda kesish HTML uchun ham xavfsiz: `html.escape` chiqaradigan
    `&amp;` / `&lt;` / `&gt;` ichida bo'sh joy yo'q, ya'ni entity hech qachon
    ikkiga bo'linib qolmaydi. Bo'sh joy topilmasa — entity boshlanishidan
    oldin kesamiz.
    """
    parts: list[str] = []
    while tg_len(text) > limit:
        cut = _prefix_len(text, limit)
        window = text[:cut]
        space = window.rfind(" ")
        if space > cut // 2:
            cut = space + 1
        else:
            # So'z chegarasi yo'q — hech bo'lmasa entity'ni buzmaymiz.
            amp = window.rfind("&")
            if amp > 0 and ";" not in window[amp:]:
                cut = amp
        head, text = text[:cut].rstrip(), text[cut:].lstrip()
        if head:
            parts.append(head)
    if text:
        parts.append(text)
    return parts


def split_for_telegram(text: str, limit: int = SAFE_LIMIT) -> list[str]:
    """Uzun javobni Telegram chegarasiga moslab bo'ladi.

    Qatorlar butunligicha saqlanadi, ya'ni til sarlavhasi o'z matnidan
    ajralib qolmaydi. Bo'sh bo'lak hech qachon qaytmaydi — Telegram bo'sh
    xabarni rad etadi va butun yuborish to'xtab qolardi.
    """
    if tg_len(text) <= limit:
        return [text]

    parts: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current.strip():
            parts.append(current)
        current = ""

    for line in text.split("\n"):
        if tg_len(line) > limit:
            # Qatorning o'zi sig'maydi. To'plangan matnni (odatda til
            # sarlavhasi) qatorga QO'SHIB bo'lamiz — aks holda sarlavha
            # o'z matnidan ajralib, alohida xabar bo'lib ketardi.
            pieces = _hard_split(f"{current}\n{line}" if current else line, limit)
            current = ""
            parts.extend(pieces[:-1])
            # Oxirgi bo'lak to'lmagan bo'lishi mumkin — keyingi qatorlar
            # unga qo'shilaveradi.
            current = pieces[-1] if pieces else ""
            continue
        candidate = f"{current}\n{line}" if current else line
        if tg_len(candidate) > limit:
            flush()
            current = line
        else:
            current = candidate
    flush()
    return parts
