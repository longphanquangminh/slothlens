"""Configuration: one small JSON file, sensible defaults, env overrides.

Everything lives in ~/.slothlens unless SLOTHLENS_HOME says otherwise.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List

HOME = Path(os.environ.get("SLOTHLENS_HOME", Path.home() / ".slothlens"))

# What screenshots are called around the world. macOS, Windows, GNOME, KDE,
# CleanShot, Flameshot... plus a few languages, because a Vietnamese Mac
# names them "Ảnh màn hình" and a German one "Bildschirmfoto".
DEFAULT_PATTERNS = [
    "Screenshot*",
    "Screen Shot*",
    "Screen Recording*",  # skipped later if not an image
    "CleanShot*",
    "Flameshot*",
    "Capture*",
    "Ảnh màn hình*",
    "Ảnh chụp màn hình*",
    "Bildschirmfoto*",
    "Capture d*écran*",
    "Captura de pantalla*",
    "スクリーンショット*",
    "截屏*",
    "屏幕截图*",
]

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def _default_dirs() -> List[str]:
    home = Path.home()
    candidates = [
        home / "Desktop",
        home / "Pictures" / "Screenshots",
        home / "Pictures",
        home / "Downloads",
    ]
    return [str(p) for p in candidates]


@dataclass
class Config:
    # where to look
    watch_dirs: List[str] = field(default_factory=_default_dirs)
    patterns: List[str] = field(default_factory=lambda: list(DEFAULT_PATTERNS))

    # the brain: any vision model Ollama (or an OpenAI-compatible server) can run
    backend: str = "ollama"  # "ollama" | "openai"
    model: str = "gemma3:4b"
    host: str = "http://127.0.0.1:11434"  # Ollama, or base URL for "openai" backend
    threads: int = 0  # 0 = let the runtime decide; set 2 to keep the fan quiet
    timeout_s: int = 900

    # sloth behaviour
    night_start: str = "00:30"
    night_end: str = "07:00"
    pace_s: int = 20  # rest between screenshots. Sloths digest slowly.
    require_ac_power: bool = True
    max_cpu_percent: float = 35.0  # someone else is using the machine above this
    min_user_idle_s: int = 300  # yield if the human touched the keyboard recently

    # tidy
    archive_dir: str = str(Path.home() / "Pictures" / "slothlens")

    @property
    def db_path(self) -> Path:
        return HOME / "sloth.db"

    @property
    def quarantine_dir(self) -> Path:
        return HOME / "quarantine"


CONFIG_PATH = HOME / "config.json"


def load() -> Config:
    cfg = Config()
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        for k, v in data.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
    # env overrides, handy for cron and for tests
    for k in ("model", "host", "backend", "archive_dir"):
        env = os.environ.get(f"SLOTHLENS_{k.upper()}")
        if env:
            setattr(cfg, k, env)
    env_dirs = os.environ.get("SLOTHLENS_WATCH_DIRS")
    if env_dirs:
        cfg.watch_dirs = [d for d in env_dirs.split(os.pathsep) if d]
    return cfg


def save(cfg: Config) -> Path:
    HOME.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(asdict(cfg), indent=2, ensure_ascii=False), encoding="utf-8")
    return CONFIG_PATH
