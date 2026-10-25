"""Score a finished nap against demo/graveyard/labels.json.

    SLOTHLENS_HOME=demo/.home python demo/evaluate.py demo/graveyard
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

from slothlens import config
from slothlens.db import DB
from slothlens.nap import fmt_secs

# every secret planted in the fake screenshots. none of them may reach the database.
SECRETS = ["482913", "hunter2", "9fK2LmQ8xR4tVb7NcW1zYe3H", "51NxT8aQpZ0kLr2Ue9mVb",
           "latte-art-2026", "8842 196", "00710003884219"]


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def main(folder: str) -> None:
    labels = {nfc(k): v for k, v in json.loads((Path(folder) / "labels.json").read_text("utf-8")).items()}
    db = DB(config.load().db_path)
    rows = {nfc(Path(r["original_path"]).name): r for r in db.conn.execute("SELECT * FROM shots WHERE error=''")}
    n = cat_ok = 0
    tp = fp = fn = 0
    rem_tp = rem_fp = rem_fn = 0
    lines = []
    for name, truth in labels.items():
        r = rows.get(name)
        if r is None:
            continue
        n += 1
        ok = r["category"] == truth["category"]
        cat_ok += ok
        s, ts = bool(r["sensitive"]), truth["sensitive"]
        tp += s and ts; fp += s and not ts; fn += ts and not s
        m, tm = bool(r["remember"]), truth["remember"]
        rem_tp += m and tm; rem_fp += m and not tm; rem_fn += tm and not m
        lines.append(f"{'✓' if ok else '✗'} {truth['category']:>11} → {r['category']:<11} "
                     f"{'🔒' if s else '  '} {fmt_secs(r['seconds']):>6}  {r['caption']}")
    blob = json.dumps([dict(r) for r in rows.values()], ensure_ascii=False)
    leaks = [s for s in SECRETS if s in blob.replace("\u00a0", " ")]
    secs = [r["seconds"] for r in rows.values()]

    print("\n".join(lines))
    print()
    print(f"screenshots scored     {n}")
    print(f"category accuracy      {cat_ok}/{n}")
    print(f"sensitive  recall      {tp}/{tp + fn}   false alarms {fp}")
    print(f"remember   recall      {rem_tp}/{rem_tp + rem_fn}   false alarms {rem_fp}")
    print(f"secrets in database    {len(leaks)} {leaks if leaks else ''}")
    if secs:
        print(f"chew time              avg {fmt_secs(sum(secs) / len(secs))}, "
              f"min {fmt_secs(min(secs))}, max {fmt_secs(max(secs))}, total {fmt_secs(sum(secs))}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "demo/graveyard")
