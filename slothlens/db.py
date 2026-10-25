"""SQLite + FTS5. One file, no server, greppable with any SQLite browser."""
from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS shots (
    id               INTEGER PRIMARY KEY,
    sha1             TEXT UNIQUE NOT NULL,
    path             TEXT NOT NULL,
    original_path    TEXT NOT NULL,
    taken_at         REAL NOT NULL,          -- file mtime
    analyzed_at      REAL,
    seconds          REAL,                   -- how long the sloth chewed
    model            TEXT,
    caption          TEXT DEFAULT '',
    category         TEXT DEFAULT '',
    key_text         TEXT DEFAULT '',
    tags             TEXT DEFAULT '',
    slug             TEXT DEFAULT '',
    sensitive        INTEGER DEFAULT 0,
    sensitive_reason TEXT DEFAULT '',
    remember         TEXT DEFAULT '',
    remember_done    INTEGER DEFAULT 0,
    error            TEXT DEFAULT '',
    raw              TEXT DEFAULT ''
);

CREATE VIRTUAL TABLE IF NOT EXISTS shots_fts USING fts5(
    caption, key_text, tags, remember, category,
    content='shots', content_rowid='id', tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS shots_ai AFTER INSERT ON shots BEGIN
  INSERT INTO shots_fts(rowid, caption, key_text, tags, remember, category)
  VALUES (new.id, new.caption, new.key_text, new.tags, new.remember, new.category);
END;
CREATE TRIGGER IF NOT EXISTS shots_ad AFTER DELETE ON shots BEGIN
  INSERT INTO shots_fts(shots_fts, rowid, caption, key_text, tags, remember, category)
  VALUES ('delete', old.id, old.caption, old.key_text, old.tags, old.remember, old.category);
END;
CREATE TRIGGER IF NOT EXISTS shots_au AFTER UPDATE ON shots BEGIN
  INSERT INTO shots_fts(shots_fts, rowid, caption, key_text, tags, remember, category)
  VALUES ('delete', old.id, old.caption, old.key_text, old.tags, old.remember, old.category);
  INSERT INTO shots_fts(rowid, caption, key_text, tags, remember, category)
  VALUES (new.id, new.caption, new.key_text, new.tags, new.remember, new.category);
END;

CREATE TABLE IF NOT EXISTS moves (
    id       INTEGER PRIMARY KEY,
    batch    TEXT NOT NULL,
    shot_id  INTEGER NOT NULL,
    src      TEXT NOT NULL,
    dst      TEXT NOT NULL,
    at       REAL NOT NULL,
    undone   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS naps (
    id        INTEGER PRIMARY KEY,
    started   REAL NOT NULL,
    ended     REAL,
    eaten     INTEGER DEFAULT 0,
    woke_because TEXT DEFAULT ''
);
"""


class DB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    # ---------- shots ----------
    def known_hashes(self) -> set:
        # failed digestions are retried on the next nap
        return {r[0] for r in self.conn.execute("SELECT sha1 FROM shots WHERE error=''")}

    def known_paths(self) -> set:
        return {r[0] for r in self.conn.execute("SELECT path FROM shots WHERE error=''")}

    def add_shot(self, sha1: str, path: str, taken_at: float, analysis: Dict[str, Any],
                 seconds: float, model: str, error: str = "") -> int:
        a = analysis or {}
        cur = self.conn.execute(
            """INSERT OR REPLACE INTO shots
            (sha1, path, original_path, taken_at, analyzed_at, seconds, model, caption, category,
             key_text, tags, slug, sensitive, sensitive_reason, remember, error, raw)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                sha1, path, path, taken_at, time.time(), seconds, model,
                a.get("caption", ""), a.get("category", ""), a.get("key_text", ""),
                " ".join(a.get("tags", []) or []), a.get("slug", ""),
                1 if a.get("sensitive") else 0, a.get("sensitive_reason", ""),
                a.get("remember", ""), error, json.dumps(a, ensure_ascii=False),
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def get(self, shot_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM shots WHERE id=?", (shot_id,)).fetchone()

    def all(self, since: float = 0.0) -> List[sqlite3.Row]:
        return list(self.conn.execute(
            "SELECT * FROM shots WHERE taken_at >= ? AND error='' ORDER BY taken_at DESC", (since,)))

    def update_path(self, shot_id: int, path: str) -> None:
        self.conn.execute("UPDATE shots SET path=? WHERE id=?", (path, shot_id))
        self.conn.commit()

    def rescrub(self, redact) -> int:
        """Re-apply the current redaction rules to everything already stored."""
        changed = 0
        for r in self.conn.execute("SELECT id, caption, key_text, remember, tags, slug FROM shots").fetchall():
            new = [redact(r[k] or "") for k in ("caption", "key_text", "remember", "tags", "slug")]
            if new != [r[k] or "" for k in ("caption", "key_text", "remember", "tags", "slug")]:
                self.conn.execute("UPDATE shots SET caption=?, key_text=?, remember=?, tags=?, slug=?, raw='' WHERE id=?",
                                  (*new, r["id"]))
                changed += 1
        self.conn.commit()
        return changed

    def mark_remembered(self, shot_id: int) -> None:
        self.conn.execute("UPDATE shots SET remember_done=1 WHERE id=?", (shot_id,))
        self.conn.commit()

    def search(self, query: str, limit: int = 10) -> List[sqlite3.Row]:
        fts = to_fts_query(query)
        if not fts:
            return []
        return list(self.conn.execute(
            """SELECT shots.*, bm25(shots_fts, 3.0, 1.0, 2.0, 2.0, 0.5) AS score
               FROM shots_fts JOIN shots ON shots.id = shots_fts.rowid
               WHERE shots_fts MATCH ? ORDER BY score LIMIT ?""",
            (fts, limit),
        ))

    def stats(self) -> Dict[str, Any]:
        row = self.conn.execute(
            """SELECT COUNT(*) n, COALESCE(AVG(seconds),0) avg_s, COALESCE(SUM(seconds),0) total_s,
               COALESCE(SUM(sensitive),0) sensitive,
               COALESCE(SUM(CASE WHEN remember != '' AND remember_done=0 THEN 1 ELSE 0 END),0) todo
               FROM shots WHERE error=''""").fetchone()
        return dict(row)

    # ---------- naps ----------
    def start_nap(self) -> int:
        cur = self.conn.execute("INSERT INTO naps(started) VALUES (?)", (time.time(),))
        self.conn.commit()
        return cur.lastrowid

    def end_nap(self, nap_id: int, eaten: int, reason: str) -> None:
        self.conn.execute("UPDATE naps SET ended=?, eaten=?, woke_because=? WHERE id=?",
                          (time.time(), eaten, reason, nap_id))
        self.conn.commit()

    def last_nap(self) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM naps WHERE ended IS NOT NULL ORDER BY id DESC LIMIT 1").fetchone()

    # ---------- moves ----------
    def record_moves(self, batch: str, moves: Iterable[tuple]) -> None:
        now = time.time()
        self.conn.executemany(
            "INSERT INTO moves(batch, shot_id, src, dst, at) VALUES (?,?,?,?,?)",
            [(batch, sid, src, dst, now) for sid, src, dst in moves],
        )
        self.conn.commit()

    def last_batch(self) -> Optional[str]:
        r = self.conn.execute("SELECT batch FROM moves WHERE undone=0 ORDER BY id DESC LIMIT 1").fetchone()
        return r[0] if r else None

    def batch_moves(self, batch: str) -> List[sqlite3.Row]:
        return list(self.conn.execute("SELECT * FROM moves WHERE batch=? AND undone=0 ORDER BY id DESC", (batch,)))

    def mark_undone(self, move_id: int) -> None:
        self.conn.execute("UPDATE moves SET undone=1 WHERE id=?", (move_id,))
        self.conn.commit()


_WORD = re.compile(r"[\w\-\.]+", re.UNICODE)


def to_fts_query(q: str) -> str:
    """Turn "cors localhost 5173" into a forgiving FTS5 query: every word, prefix-matched."""
    words = [w.strip(".-") for w in _WORD.findall(q)]
    words = [w for w in words if w]
    return " ".join(f'"{w}"*' for w in words)
