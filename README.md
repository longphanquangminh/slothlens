# 🦥 slothlens

**A sloth that eats your screenshots while you sleep.**

You have 2,000 files called `Screenshot 2026-10-21 at 01.58.44.png`. Some are errors you
meant to google. Some are messages you meant to answer. One is your bank OTP. One is your
`.env` file with a live Stripe key.

slothlens is a local, deliberately slow night-shift agent. After midnight, on AC power,
when nobody is touching the keyboard, it reads your screenshots one at a time with
**Gemma 3 4B running on your own machine through Ollama**, and in the morning it leaves you:

- ⏰ **the things you screenshotted to remember** ("Send the slides to Minh by Friday 5pm")
- 🔒 **the things that shouldn't still be lying around** (OTPs, API keys, wifi passwords)
- 🔎 **full-text search** over everything it has ever seen: `slothlens find "cors 5173"`
- 🗂️ optional **tidy**: `2026-10/error/2026-10-19_cors-error-localhost.png`, with `undo`

No cloud. No account. No API key. The screenshots never leave the laptop, and the
database never stores the secrets it finds: they go through three layers of redaction
before anything is written.

![demo](docs/demo.gif)

```
🦥 found 16 uneaten screenshots. at sloth speed that's about 32m00s.
🌿 [2/16] chewing Screenshot 2026-10-24 at 13.07.15.png ...
    3m36s  [credentials] The Workshop WiFi login details screenshot. 🔒
🌿 [9/16] chewing Screenshot 2026-10-22 at 08.05.50.png ...
    6m37s  [booking] Google Calendar invites technical interview for frontend intern React/TypeScript project  ⏰ Prepare React/TypeScript project walkthrough for interview on Oct 27th, 10:00 AM (GMT+7)
```
(real output, 2 vCPU / 4 GB / no GPU, see [`demo/`](demo))

## Why so slow?

On a 2-core, 4 GB, GPU-less machine Gemma 3 4B needs about four minutes per screenshot.
That is terrible for a chat app and perfect for a job that runs while you sleep:
**~14 screenshots an hour, ~90 a night, $0.00 forever.** (With a GPU or Apple Silicon it's
seconds.) slothlens leans into it:

| Sloth rule | How |
| --- | --- |
| Only works at night | `night_start`/`night_end` window (default 00:30-07:00) |
| Never drains your battery | stops when unplugged (`psutil`) |
| Yields to humans | stops if the keyboard/mouse was used in the last 5 min (macOS, Windows, Linux with `xprintidle`) |
| Yields to other work | stops if CPU is above 35% |
| Lowest priority | `os.nice(19)` |
| Chews one thing at a time | one image per request, 20 s rest between bites |
| Never loses its place | every result is committed to SQLite immediately; tomorrow it resumes |

## Install

```bash
# 1. a local vision model
ollama pull gemma3:4b          # ~3.3 GB. any Ollama vision model works

# 2. slothlens
pip install "slothlens[gates] @ git+https://github.com/longphanquangminh/slothlens"
# or: git clone https://github.com/longphanquangminh/slothlens && cd slothlens && pip install -e ".[gates]"

slothlens init                 # writes ~/.slothlens/config.json
slothlens schedule             # prints the cron / launchd / Task Scheduler line for your OS
```

Try it right now without waiting for midnight:

```bash
slothlens nap --now --limit 3  # ignores the clock, still yields to you and your battery
slothlens digest --html ~/digest.html
```

## Commands

| Command | What it does |
| --- | --- |
| `slothlens nap [--now] [--limit N] [--force]` | eat uneaten screenshots |
| `slothlens status` | eaten / waiting / average chew time / ETA |
| `slothlens digest [--since 24h] [--html FILE] [--no-llm]` | morning report (Markdown to stdout, optional HTML page) |
| `slothlens find "words"` | full-text search (SQLite FTS5, diacritics-insensitive) |
| `slothlens remember` / `done ID` | the to-dos hidden in your screenshots |
| `slothlens tidy [--apply]` / `undo` | rename + file into `archive_dir`, fully reversible |
| `slothlens forget ID` | move a sensitive screenshot to a quarantine folder |
| `slothlens rescrub` | re-apply the latest redaction rules to everything already stored |

## Configuration

`~/.slothlens/config.json` (created by `slothlens init`):

```json
{
  "watch_dirs": ["~/Desktop", "~/Pictures/Screenshots"],
  "model": "gemma3:4b",
  "backend": "ollama",
  "host": "http://127.0.0.1:11434",
  "night_start": "00:30",
  "night_end": "07:00",
  "pace_s": 20,
  "threads": 0
}
```

Swap the brain whenever you like: `"model": "qwen2.5vl:3b"`, `"gemma3:12b"` on a beefier
machine, or `"backend": "openai"` to point at a llama.cpp / LM Studio / vLLM server.

Screenshots are recognised by name in many languages and tools: `Screenshot*`,
`Screen Shot*`, `CleanShot*`, `Ảnh màn hình*`, `Bildschirmfoto*`, `Capture d’écran*`,
`スクリーンショット*`, `截屏*`, and more (see `config.py`).

## How it works

```
watch dirs ──► find_uneaten (sha1 dedupe) ──► gate: night? plugged in? human idle? CPU idle?
                                                   │ yes                      │ no → sleep, resume tomorrow
                                                   ▼
                        Gemma 3 4B (Ollama, JSON-schema constrained output, one image)
                                                   │
                     normalize + regex redaction (OTPs, keys, card/account numbers, passwords)
                                                   │
                                SQLite + FTS5  ──► digest · find · remember · tidy/undo
```

- **Structured output.** The request passes a JSON Schema in Ollama's `format` field, so the
  model can only answer with valid JSON and a category from a fixed list.
- **Untrusted pixels.** Screenshot text is data, not instructions. The prompt says so, the
  category is schema-constrained, and `normalize()` clamps everything else.
  The demo set includes a screenshot that says "Ignore all previous instructions".
- **Secrets never land in the DB.** Three layers: (1) the model redacts secrets in `key_text`;
  (2) the model lists the exact secret strings it saw in `secret_values`, slothlens scrubs them
  from *every* field and then drops the list (never stored); (3) `redact()` runs regexes for OTP
  codes, `sk-…`/`ghp_…`/AWS/Slack keys, JWTs, `password: …` and long card/account numbers.
- **Name the secret, don't say yes/no.** `secret_seen` is an enum (`none`, `password`,
  `one-time code`, …) generated *after* `key_text`, so the model transcribes evidence before it
  decides. A boolean `sensitive` field made Gemma 4B flag 13 of 14 screenshots.

## Demo + evaluation

```bash
pip install -e ".[gates,demo]" && playwright install chromium
python demo/make_screenshots.py demo/graveyard      # 16 realistic, fully synthetic screenshots + labels
SLOTHLENS_HOME=demo/.home slothlens nap --now
SLOTHLENS_HOME=demo/.home python demo/evaluate.py demo/graveyard
```

Results on the 16-screenshot demo set (`demo/eval_v4.txt`): category 14/16, sensitive 4/4 with
0 false alarms, reminders 6/6 with 3 false alarms, **0 of 6 planted secrets in the database**,
prompt injection ignored, 4m16s per screenshot on average. It's a smoke test, not a benchmark.

## A harder test: realistic screenshots

The first demo set (`demo/graveyard/`) is clean HTML mock-ups. To see how slothlens holds up on
something closer to a real camera roll, `demo/graveyard-real/` has 16 screenshots rendered at real
device sizes: Android phone captures at 1080x2400 (Messenger in Vietnamese, a Vietcombank OTP SMS,
a VCB Digibank transfer, a GrabFood order, a Zalo message with a wifi password) and Retina desktop
captures at 2560x1600 with full browser or app chrome (Chrome DevTools, VS Code, Gmail, Google
Calendar, Google Maps, X, Stack Overflow, Dribbble, GitHub, Discord).

![cropped demo illustrations](docs/presentation-crops/preview.jpg)

Demo scenarios are recreated with fictional details so no private chats, travel records or
credentials need to be published. The cropped images in `docs/presentation-crops/` are for
illustration only; the scores below were measured on the full screenshots in `demo/graveyard-real/`.

Same model, same prompt, same 2 vCPU / 4 GB machine:

| Metric | Mock-up set | Realistic set |
| --- | --- | --- |
| Category accuracy | 14 / 16 | 13 / 16 |
| Sensitive screenshots caught | 4 / 4, 0 false alarms | 3 / 4, 2 false alarms |
| "Remember" to-dos caught | 6 / 6, 3 false alarms | 4 / 6, 7 false alarms |
| Planted secrets in the database | 0 / 6 | 1 / 6 → **0 / 6 after the fix below** |
| Time per screenshot | 4m16s | 4m24s |

Real UIs are harder: small desktop text gets downscaled to Gemma's 896 px input, and phone chrome
competes with the content. Notable misses: the OTP SMS was read as "OTP payment failure" and not
flagged; the Zalo wifi message became "asks about a customer's laptop issue" (still flagged 🔒);
the Messenger request for slides produced no reminder.

**It also found a real bug.** In the VS Code `.env` screenshot Gemma misread the `@` in
`postgres://admin:hunter2@db.internal` as a `6`, so the old regexes missed the password and it
reached the database. The redaction layer now also scrubs credentials in any `scheme://user:...`
string (without needing the `@`, while leaving ports like `localhost:5173` alone) and the values of
`*SECRET*`, `*TOKEN*`, `*PASSWORD*`, `*API_KEY*`, `DATABASE_URL` style variables. If you already have
a database from an older version, run:

```bash
slothlens rescrub     # re-apply the latest redaction rules to everything already stored
```

Reproduce (logs in `demo/logs-real/`, scores before and after the fix included):

```bash
python demo/make_screenshots_real.py demo/graveyard-real
SLOTHLENS_HOME=demo/.home-real slothlens nap --now
SLOTHLENS_HOME=demo/.home-real python demo/evaluate.py demo/graveyard-real
```

## Tests

```bash
python -m unittest discover -s tests     # no model needed: a fake pair of eyes stands in for Gemma
```

## License

MIT. Gemma is provided under the [Gemma Terms of Use](https://ai.google.dev/gemma/terms).
