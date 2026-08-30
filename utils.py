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


def split_for_telegram(text: str, limit: int = 4000) -> list[str]:
    """Uzun javobni Telegram'ning 4096 belgilik chegarasiga moslab bo'ladi."""
    if len(text) <= limit:
        return [text]

    parts: list[str] = []
    current = ""
    for line in text.split("\n"):
        while len(line) > limit:
            if current:
                parts.append(current)
                current = ""
            parts.append(line[:limit])
            line = line[limit:]
        if len(current) + len(line) + 1 > limit:
            parts.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        parts.append(current)
    return parts
