"""The sloth gate: is it a good moment to chew on a screenshot?

slothlens only works when nobody needs the computer: at night, on AC power,
with an idle CPU and an idle human. The moment you come back, it yields.
Every check fails *open to resting*: if in doubt, the sloth sleeps.
"""
from __future__ import annotations

import ctypes
import datetime as dt
import os
import platform
import re
import shutil
import subprocess
from typing import Optional

try:  # optional, but makes battery and CPU checks precise
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None


def _parse_hhmm(s: str) -> dt.time:
    h, m = s.split(":")
    return dt.time(int(h), int(m))


def in_window(now: dt.datetime, start: str, end: str) -> bool:
    """True if `now` is inside [start, end). Handles windows that wrap midnight."""
    s, e, t = _parse_hhmm(start), _parse_hhmm(end), now.time()
    if s == e:
        return True  # 24h window
    if s < e:
        return s <= t < e
    return t >= s or t < e


def on_ac_power() -> Optional[bool]:
    if psutil is None:
        return None
    try:
        batt = psutil.sensors_battery()
    except Exception:
        return None
    if batt is None:  # desktop, no battery
        return True
    return bool(batt.power_plugged)


def cpu_percent(sample_s: float = 3.0) -> Optional[float]:
    if psutil is not None:
        return float(psutil.cpu_percent(interval=sample_s))
    if hasattr(os, "getloadavg"):
        load1 = os.getloadavg()[0]
        return 100.0 * load1 / (os.cpu_count() or 1)
    return None


def user_idle_seconds() -> Optional[float]:
    """Seconds since the last keyboard/mouse input, or None if we can't tell."""
    system = platform.system()
    try:
        if system == "Darwin":
            out = subprocess.run(["ioreg", "-c", "IOHIDSystem"], capture_output=True, text=True, timeout=5).stdout
            m = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', out)
            return int(m.group(1)) / 1e9 if m else None
        if system == "Windows":
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(lii)
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):  # type: ignore[attr-defined]
                return (ctypes.windll.kernel32.GetTickCount() - lii.dwTime) / 1000.0  # type: ignore[attr-defined]
            return None
        if shutil.which("xprintidle"):
            out = subprocess.run(["xprintidle"], capture_output=True, text=True, timeout=5).stdout.strip()
            return int(out) / 1000.0 if out.isdigit() else None
    except Exception:
        return None
    return None


def why_not(cfg, now: Optional[dt.datetime] = None, *, ignore_clock: bool = False,
            force: bool = False) -> Optional[str]:
    """Return a reason to keep resting, or None if the sloth may eat."""
    if force:
        return None
    now = now or dt.datetime.now()
    if not ignore_clock and not in_window(now, cfg.night_start, cfg.night_end):
        return f"it's {now:%H:%M}, sloth hours are {cfg.night_start}-{cfg.night_end}"
    if cfg.require_ac_power and on_ac_power() is False:
        return "running on battery"
    idle = user_idle_seconds()
    if idle is not None and idle < cfg.min_user_idle_s:
        return f"a human touched the keyboard {int(idle)}s ago"
    cpu = cpu_percent()
    if cpu is not None and cpu > cfg.max_cpu_percent:
        return f"CPU is busy ({cpu:.0f}%)"
    return None
