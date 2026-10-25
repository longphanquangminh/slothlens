"""Tests that run without a model: a fake pair of eyes stands in for Gemma."""
from __future__ import annotations

import datetime as dt
import os
import tempfile
import unittest
from pathlib import Path

os.environ["SLOTHLENS_HOME"] = tempfile.mkdtemp()

from slothlens import gate, tidy  # noqa: E402
from slothlens.config import Config  # noqa: E402
from slothlens.db import DB, to_fts_query  # noqa: E402
from slothlens.eyes import clean_slug, normalize, redact  # noqa: E402
from slothlens.nap import find_uneaten, is_screenshot, nap  # noqa: E402

PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS"
       b"\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")


class FakeEyes:
    def __init__(self):
        self.calls = 0

    def look(self, path):
        self.calls += 1
        if "otp" in path.name.lower():
            raw = {"caption": "Bank OTP code 482913 by SMS", "category": "credentials",
                   "key_text": "Your code is 482913", "tags": ["otp", "bank"], "slug": "bank otp",
                   "sensitive": False, "sensitive_reason": "", "remember": ""}
        else:
            raw = {"caption": "CORS error from localhost 5173 calling the API", "category": "error",
                   "key_text": "blocked by CORS policy", "tags": ["CORS", "vite", "cors"],
                   "slug": "CORS error: localhost!!", "sensitive": False, "sensitive_reason": "x",
                   "remember": "Fix CORS before Friday demo"}
        return normalize(raw), 0.01, {}


def make_env(tmp: Path):
    shots = tmp / "Desktop"
    shots.mkdir()
    for name in ["Screenshot 2026-10-20 at 10.00.00.png", "Screenshot otp 2026-10-21.png",
                 "holiday.png", "Screenshot notes.txt"]:
        (shots / name).write_bytes(PNG + name.encode())
    cfg = Config(watch_dirs=[str(shots)], archive_dir=str(tmp / "archive"), pace_s=0)
    return cfg, DB(tmp / "sloth.db")


class GateTests(unittest.TestCase):
    def test_window_wraps_midnight(self):
        at = lambda h, m: dt.datetime(2026, 10, 20, h, m)  # noqa: E731
        self.assertTrue(gate.in_window(at(1, 0), "00:30", "07:00"))
        self.assertFalse(gate.in_window(at(12, 0), "00:30", "07:00"))
        self.assertTrue(gate.in_window(at(23, 30), "23:00", "06:00"))
        self.assertTrue(gate.in_window(at(5, 59), "23:00", "06:00"))
        self.assertFalse(gate.in_window(at(6, 0), "23:00", "06:00"))

    def test_daytime_means_rest(self):
        cfg = Config()
        why = gate.why_not(cfg, dt.datetime(2026, 10, 20, 14, 0))
        self.assertIn("sloth hours", why)
        self.assertIsNone(gate.why_not(cfg, force=True))


class EyesTests(unittest.TestCase):
    def test_redaction(self):
        self.assertNotIn("482913", redact("Ma OTP cua Quy khach la 482913"))
        self.assertNotIn("9fK2", redact("OPENAI_API_KEY=sk-proj-9fK2LmQ8xR4tVb7NcW1zYe3H"))
        self.assertNotIn("hunter2", redact("password: hunter2"))
        self.assertNotIn("8842", redact("Số tài khoản 0071 0003 8842 196"))
        self.assertIn("2.500.000", redact("2.500.000 VND"))  # amounts survive

    def test_connection_string_redaction(self):
        self.assertNotIn("hunter2", redact("DATABASE_URL=postgres://admin:hunter2@db.internal:5432/cms"))
        # vision models misread '@' as '6': still redacted
        self.assertNotIn("hunter2", redact("postgresql://admin:hunter26db.internal:5432/cms"))
        self.assertNotIn("s3cr3t", redact("JWT_SECRET: s3cr3t-value"))
        # ordinary URLs with ports are untouched
        self.assertEqual(redact("GET http://localhost:8080/api/posts"), "GET http://localhost:8080/api/posts")
        self.assertEqual(redact("origin 'http://localhost:5173' blocked"), "origin 'http://localhost:5173' blocked")
        self.assertNotIn("123456", redact("redis://default:123456@cache:6379"))  # numeric password is not a port

    def test_normalize_is_defensive(self):
        out = normalize({"category": "Credentials", "tags": "A, b ,a", "slug": "Hello, World!!",
                         "secret_seen": "none"})
        self.assertEqual(out["category"], "credentials")
        self.assertTrue(out["sensitive"])  # credentials are always sensitive
        self.assertEqual(out["tags"], ["a", "b"])
        self.assertEqual(out["slug"], "hello-world")
        self.assertEqual(normalize({"category": "cat photo"})["category"], "other")
        self.assertEqual(normalize({"secret_seen": "one-time code"})["sensitive_reason"], "one-time code")
        self.assertFalse(normalize({"secret_seen": "timestamps and hashtags"})["sensitive"])

    def test_model_pointed_secrets_are_scrubbed_and_dropped(self):
        out = normalize({"caption": "Connect to Workshop_Guest_5G using latte-art-2026",
                         "key_text": "Password: latte-art-2026", "remember": "",
                         "slug": "wifi latte-art-2026", "tags": ["wifi", "latte-art-2026"],
                         "secret_seen": "password", "secret_values": ["latte-art-2026"]})
        blob = repr(out)
        self.assertNotIn("latte-art-2026", blob)
        self.assertNotIn("secret_values", out)
        self.assertIn("Workshop_Guest_5G", out["caption"])
        self.assertEqual(out["sensitive_reason"], "password")

    def test_slug(self):
        self.assertEqual(clean_slug("  Ảnh lỗi CORS ở Đà Nẵng!! "), "anh-loi-cors-o-da-nang")
        self.assertEqual(clean_slug(""), "screenshot")


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg, self.db = make_env(self.tmp)

    def test_detects_screenshots_only(self):
        self.assertTrue(is_screenshot(Path("Ảnh màn hình 2026-10-21 lúc 09.14.33.png"), self.cfg.patterns))
        self.assertTrue(is_screenshot(Path("Screen Shot 2020-01-01.JPG"), self.cfg.patterns))
        self.assertFalse(is_screenshot(Path("holiday.png"), self.cfg.patterns))
        self.assertEqual(len(find_uneaten(self.cfg, self.db)), 2)

    def test_nap_search_tidy_undo(self):
        eyes = FakeEyes()
        logs = []
        eaten = nap(self.cfg, self.db, eyes, force=True, log=logs.append, sleep=lambda s: None)
        self.assertEqual(eaten, 2)
        # second nap: nothing new, model never called again
        nap(self.cfg, self.db, eyes, force=True, log=logs.append, sleep=lambda s: None)
        self.assertEqual(eyes.calls, 2)

        hits = self.db.search("cors local")
        self.assertEqual(len(hits), 1)
        self.assertEqual(self.db.search("fts5: near \".\""), [])  # hostile queries don't crash

        otp = [r for r in self.db.all() if r["category"] == "credentials"][0]
        self.assertTrue(otp["sensitive"])
        self.assertNotIn("482913", otp["caption"] + otp["key_text"])

        plan = tidy.plan(self.cfg, self.db)
        self.assertEqual(len(plan), 2)
        self.assertTrue(any("/error/" in dst and dst.endswith("_cors-error-localhost.png") for _, _, dst in plan))
        tidy.apply(self.db, plan)
        self.assertFalse(any(Path(src).exists() for _, src, _ in plan))
        # tidied files are not re-eaten
        self.assertEqual(find_uneaten(self.cfg, self.db), [])
        self.assertEqual(tidy.undo(self.db), 2)
        self.assertTrue(all(Path(src).exists() for _, src, _ in plan))

    def test_fts_query_escaping(self):
        self.assertEqual(to_fts_query('cors "5173"'), '"cors"* "5173"*')
        self.assertEqual(to_fts_query("..."), "")


if __name__ == "__main__":
    unittest.main()
