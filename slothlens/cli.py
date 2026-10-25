"""slothlens command line.

    slothlens init              write ~/.slothlens/config.json
    slothlens nap [--now]       eat screenshots (only at night, unless --now)
    slothlens status            how much is left, how fast the sloth is
    slothlens digest            the morning report (markdown, or --html file)
    slothlens find "cors 5173"  full-text search over everything it has seen
    slothlens remember          the things you screenshotted to act on later
    slothlens done ID           tick one of those off
    slothlens tidy [--apply]    rename + file screenshots into the archive
    slothlens undo              put the last tidy batch back exactly where it was
    slothlens forget ID         move a sensitive screenshot into quarantine
    slothlens rescrub           re-apply the latest redaction rules to stored data
    slothlens schedule          print the cron / launchd / Task Scheduler line
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

from . import __version__, config, digest, schedule, tidy
from .db import DB
from .eyes import Eyes
from .nap import find_uneaten, fmt_secs, nap


def _since(arg: str) -> float:
    """'24h', '7d', '90m' -> unix timestamp."""
    unit = arg[-1]
    n = float(arg[:-1])
    mult = {"m": 60, "h": 3600, "d": 86400}.get(unit)
    if mult is None:
        raise SystemExit(f"--since wants something like 24h or 7d, got {arg!r}")
    return time.time() - n * mult


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    p = argparse.ArgumentParser(prog="slothlens", description="A sloth that eats your screenshots while you sleep.")
    p.add_argument("--version", action="version", version=f"slothlens {__version__}")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("init", help="write a default config file")

    n = sub.add_parser("nap", help="eat uneaten screenshots")
    n.add_argument("--now", action="store_true", help="ignore the clock (still yields to humans and battery)")
    n.add_argument("--force", action="store_true", help="ignore every gate. not very sloth of you.")
    n.add_argument("--limit", type=int, help="eat at most N screenshots")

    sub.add_parser("status", help="progress and speed")

    d = sub.add_parser("digest", help="morning report")
    d.add_argument("--since", default="24h", help="window, e.g. 24h, 7d (default 24h)")
    d.add_argument("--html", help="also write a pretty HTML digest to this file")
    d.add_argument("--no-llm", action="store_true", help="skip the model's one-line morning note")

    f = sub.add_parser("find", help="search screenshots")
    f.add_argument("query", nargs="+")
    f.add_argument("-n", type=int, default=8)
    f.add_argument("--json", action="store_true")

    sub.add_parser("remember", help="list things you screenshotted to act on")
    dn = sub.add_parser("done", help="mark a remember item as done")
    dn.add_argument("id", type=int)

    t = sub.add_parser("tidy", help="rename and file screenshots")
    t.add_argument("--apply", action="store_true", help="actually move files (default: show the plan)")
    sub.add_parser("undo", help="undo the last tidy")

    fg = sub.add_parser("forget", help="quarantine a screenshot (reversible)")
    fg.add_argument("id", type=int)

    sub.add_parser("rescrub", help="re-apply the latest redaction rules to stored data")
    sub.add_parser("schedule", help="how to run slothlens every night")

    a = p.parse_args(argv)
    if not a.cmd:
        p.print_help()
        return 0

    cfg = config.load()

    if a.cmd == "init":
        path = config.save(cfg)
        print(f"wrote {path}\nwatching: " + ", ".join(cfg.watch_dirs))
        print(f"model: {cfg.model} via {cfg.backend} at {cfg.host}")
        return 0

    if a.cmd == "schedule":
        print(schedule.instructions())
        return 0

    db = DB(cfg.db_path)

    if a.cmd == "nap":
        eyes = Eyes(cfg)
        if not eyes.alive():
            print(f"can't reach {cfg.backend} at {cfg.host}. is it running? (ollama serve)")
            return 2
        nap(cfg, db, eyes, ignore_clock=a.now, force=a.force, limit=a.limit)
        return 0

    if a.cmd == "status":
        s = db.stats()
        left = len(find_uneaten(cfg, db))
        print(f"🦥 eaten: {s['n']}   waiting: {left}   avg chew: {fmt_secs(s['avg_s'])}")
        if left:
            print(f"   at this pace the rest takes {fmt_secs(left * (s['avg_s'] or 120))} of sleep")
        print(f"   flagged sensitive: {s['sensitive']}   open reminders: {s['todo']}")
        last = db.last_nap()
        if last:
            when = dt.datetime.fromtimestamp(last["started"]).strftime("%a %H:%M")
            print(f"   last nap: {when}, ate {last['eaten']}, woke because {last['woke_because']}")
        return 0

    if a.cmd == "digest":
        eyes = None if a.no_llm else Eyes(cfg)
        if eyes is not None and not eyes.alive():
            eyes = None
        report = digest.build(db, since=_since(a.since), eyes=eyes)
        print(digest.to_markdown(report))
        if a.html:
            Path(a.html).write_text(digest.to_html(report), encoding="utf-8")
            print(f"\n(html digest written to {a.html})")
        return 0

    if a.cmd == "find":
        rows = db.search(" ".join(a.query), limit=a.n)
        if a.json:
            print(json.dumps([{"id": r["id"], "path": r["path"], "caption": r["caption"],
                               "category": r["category"]} for r in rows], ensure_ascii=False, indent=2))
            return 0
        if not rows:
            print("🦥 nothing. maybe it's still in the uneaten pile?")
            return 1
        for r in rows:
            when = dt.datetime.fromtimestamp(r["taken_at"]).strftime("%b %d")
            lock = " 🔒" if r["sensitive"] else ""
            print(f"#{r['id']:<4} {when}  [{r['category']}] {r['caption']}{lock}\n      {r['path']}")
        return 0

    if a.cmd == "remember":
        rows = [r for r in db.all() if r["remember"] and not r["remember_done"]]
        if not rows:
            print("🦥 nothing to remember. enjoy the hammock.")
        for r in rows:
            when = dt.datetime.fromtimestamp(r["taken_at"]).strftime("%b %d")
            print(f"#{r['id']:<4} ⏰ {r['remember']}   (screenshotted {when})")
        return 0

    if a.cmd == "done":
        db.mark_remembered(a.id)
        print(f"✓ #{a.id} done. that's one less thing.")
        return 0

    if a.cmd == "tidy":
        plan = tidy.plan(cfg, db)
        if not plan:
            print("🦥 everything is already tidy.")
            return 0
        for _sid, src, dst in plan:
            print(f"{Path(src).name}\n   → {dst}")
        if a.apply:
            batch = tidy.apply(db, plan)
            print(f"\nmoved {len(plan)} files. changed your mind? `slothlens undo` (batch {batch})")
        else:
            print(f"\n{len(plan)} files would move. run `slothlens tidy --apply` to do it.")
        return 0

    if a.cmd == "undo":
        n_back = tidy.undo(db)
        print(f"put {n_back} files back where they were." if n_back else "nothing to undo.")
        return 0

    if a.cmd == "rescrub":
        from .eyes import redact
        n_changed = db.rescrub(redact)
        print(f"🧽 re-scrubbed {n_changed} stored screenshot(s) with the latest redaction rules.")
        return 0

    if a.cmd == "forget":
        dst = tidy.quarantine(cfg, db, a.id)
        print(f"moved to quarantine: {dst}\n(delete that folder when you're sure, or move it back)")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
