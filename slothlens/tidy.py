"""Rename + file screenshots, with a journal so every move can be undone."""
from __future__ import annotations

import datetime as dt
import shutil
import uuid
from pathlib import Path
from typing import List, Tuple

from .config import Config
from .db import DB

Move = Tuple[int, str, str]


def target_for(cfg: Config, row) -> Path:
    when = dt.datetime.fromtimestamp(row["taken_at"])
    ext = Path(row["path"]).suffix.lower()
    folder = Path(cfg.archive_dir).expanduser() / f"{when:%Y-%m}" / (row["category"] or "other")
    return folder / f"{when:%Y-%m-%d}_{row['slug'] or 'screenshot'}{ext}"


def _unique(path: Path, taken: set) -> Path:
    candidate, i = path, 2
    while candidate.exists() or str(candidate) in taken:
        candidate = path.with_name(f"{path.stem}-{i}{path.suffix}")
        i += 1
    return candidate


def plan(cfg: Config, db: DB) -> List[Move]:
    archive = Path(cfg.archive_dir).expanduser().resolve()
    moves, taken = [], set()
    for row in db.all():
        src = Path(row["path"])
        if not src.exists() or archive in src.resolve().parents:
            continue
        dst = _unique(target_for(cfg, row), taken)
        taken.add(str(dst))
        moves.append((row["id"], str(src), str(dst)))
    return moves


def apply(db: DB, moves: List[Move]) -> str:
    batch = uuid.uuid4().hex[:8]
    done = []
    for sid, src, dst in moves:
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src, dst)
        db.update_path(sid, dst)
        done.append((sid, src, dst))
    db.record_moves(batch, done)
    return batch


def undo(db: DB) -> int:
    batch = db.last_batch()
    if not batch:
        return 0
    n = 0
    for m in db.batch_moves(batch):
        if Path(m["dst"]).exists() and not Path(m["src"]).exists():
            Path(m["src"]).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(m["dst"], m["src"])
            db.update_path(m["shot_id"], m["src"])
            n += 1
            _prune_empty(Path(m["dst"]).parent)
        db.mark_undone(m["id"])
    return n


def _prune_empty(folder: Path, levels: int = 3) -> None:
    """Remove the month/category folders tidy created, if undo left them empty."""
    for _ in range(levels):
        try:
            folder.rmdir()  # only succeeds when empty
        except OSError:
            return
        folder = folder.parent


def quarantine(cfg: Config, db: DB, shot_id: int) -> Path:
    row = db.get(shot_id)
    if row is None:
        raise SystemExit(f"no screenshot #{shot_id}")
    src = Path(row["path"])
    cfg.quarantine_dir.mkdir(parents=True, exist_ok=True)
    dst = _unique(cfg.quarantine_dir / src.name, set())
    shutil.move(str(src), str(dst))
    db.update_path(shot_id, str(dst))
    db.record_moves("forget-" + uuid.uuid4().hex[:6], [(shot_id, str(src), str(dst))])
    return dst
