"""The nap: find uneaten screenshots and chew through them, one at a time."""
from __future__ import annotations

import fnmatch
import hashlib
import os
import time
import unicodedata
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from . import gate
from .config import IMAGE_EXTS, Config
from .db import DB


def _nfc(s: str) -> str:
    # macOS stores "Ảnh màn hình" decomposed (NFD); patterns are NFC.
    return unicodedata.normalize("NFC", s)


def is_screenshot(path: Path, patterns: List[str]) -> bool:
    if path.suffix.lower() not in IMAGE_EXTS:
        return False
    name = _nfc(path.name)
    return any(fnmatch.fnmatch(name, _nfc(p)) for p in patterns)


def sha1_of(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_uneaten(cfg: Config, db: DB) -> List[Tuple[Path, str, float]]:
    """Return (path, sha1, mtime) for screenshots the sloth hasn't seen, newest first."""
    known_paths, known_hashes = db.known_paths(), db.known_hashes()
    archive = Path(cfg.archive_dir).expanduser().resolve()
    seen, found = set(), []
    for d in cfg.watch_dirs:
        root = Path(d).expanduser()
        if not root.is_dir():
            continue
        for entry in root.iterdir():  # not recursive: screenshots land at the top level
            try:
                if not entry.is_file() or not is_screenshot(entry, cfg.patterns):
                    continue
                rp = entry.resolve()
                if rp in seen or archive in rp.parents or str(entry) in known_paths:
                    continue
                seen.add(rp)
                digest = sha1_of(entry)
                if digest in known_hashes:
                    continue
                found.append((entry, digest, entry.stat().st_mtime))
            except OSError:
                continue
    found.sort(key=lambda t: t[2], reverse=True)
    return found


def fmt_secs(s: float) -> str:
    s = int(round(s))
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m"


def nap(cfg: Config, db: DB, eyes, *, ignore_clock: bool = False, force: bool = False,
        limit: Optional[int] = None, log: Callable[[str], None] = print,
        sleep: Callable[[float], None] = time.sleep) -> int:
    """Eat screenshots until there are none left, the night ends, or a human shows up."""
    try:
        os.nice(19)  # the lowest priority the OS offers. Sloth etiquette.
    except (AttributeError, OSError):
        pass

    queue = find_uneaten(cfg, db)
    if limit:
        queue = queue[:limit]
    if not queue:
        log("🦥 nothing to eat. going back to sleep.")
        return 0

    avg = db.stats()["avg_s"] or 120
    log(f"🦥 found {len(queue)} uneaten screenshots. at sloth speed that's about {fmt_secs(avg * len(queue))}.")
    nap_id = db.start_nap()
    eaten, reason = 0, "ran out of screenshots"
    try:
        for i, (path, digest, mtime) in enumerate(queue, 1):
            why = gate.why_not(cfg, ignore_clock=ignore_clock, force=force)
            if why:
                reason = why
                log(f"💤 stopping: {why}. {len(queue) - i + 1} left for tomorrow night.")
                break
            log(f"🌿 [{i}/{len(queue)}] chewing {path.name} ...")
            try:
                analysis, secs, _stats = eyes.look(path)
                db.add_shot(digest, str(path), mtime, analysis, secs, cfg.model)
                eaten += 1
                flag = " 🔒" if analysis["sensitive"] else ""
                todo = f"  ⏰ {analysis['remember']}" if analysis["remember"] else ""
                log(f"   {fmt_secs(secs):>6}  [{analysis['category']}] {analysis['caption']}{flag}{todo}")
            except Exception as exc:  # one bad file never ruins the night
                db.add_shot(digest, str(path), mtime, {}, 0.0, cfg.model, error=repr(exc)[:300])
                log(f"   ⚠️  couldn't digest it: {exc!r}")
            if i < len(queue) and cfg.pace_s:
                sleep(cfg.pace_s)
    except KeyboardInterrupt:
        reason = "interrupted"
        log("\n💤 ok ok, I'm stopping.")
    finally:
        db.end_nap(nap_id, eaten, reason)
    return eaten
