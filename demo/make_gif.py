"""Turn a real terminal transcript into an animated GIF for the README / DEV post.

    python demo/make_gif.py demo/transcript.txt docs/demo.gif

Lines starting with '$ ' are typed out; other lines appear at once. A line that is
exactly '~~ <text>' becomes a dim "time passes" card (e.g. '~~ 2 minutes 41 seconds later').
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 680
PAD = 28
BG = (24, 27, 23)
FG = (222, 226, 214)
DIM = (125, 135, 118)
GREEN = (143, 190, 120)
AMBER = (232, 184, 96)
RED = (230, 120, 100)


def font(size: int, emoji: bool = False):
    paths = [str(Path.home() / ".fonts/JetBrainsMono-Regular.ttf"),
             "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
             "/System/Library/Fonts/Menlo.ttc", "C:/Windows/Fonts/consola.ttf"]
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


EMOJI_MAP = {"🦥 ": "", "🦥": "", "🌿": "»", "💤": "z", "🔒": "[secret]", "⏰": "→", "⚠️": "!", "✓": "✓",
             "🔥": "*", "🗂️": "#", "📍": "@"}


def clean(line: str) -> str:
    for k, v in EMOJI_MAP.items():
        line = line.replace(k, v)
    return line.replace("\u200d", "")


def color_for(line: str):
    if line.startswith("$ "):
        return GREEN
    if "[secret]" in line:
        return AMBER
    if "stopping" in line or "error" in line.lower()[:20]:
        return RED
    if line.startswith("   ") or line.startswith("      "):
        return FG
    return DIM if line.startswith("»") else FG


def wrap(line: str, width: int):
    out = []
    while len(line) > width:
        cut = line.rfind(" ", 0, width)
        cut = cut if cut > width // 2 else width
        out.append(line[:cut])
        line = "      " + line[cut:].lstrip()
    out.append(line)
    return out


def render(lines, f, title):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 38], fill=(38, 42, 36))
    for i, c in enumerate([(237, 106, 94), (245, 191, 79), (98, 197, 84)]):
        d.ellipse([16 + i * 22, 13, 28 + i * 22, 25], fill=c)
    tf = font(15)
    d.text(((W - tf.getlength(title)) // 2, 10), title, fill=DIM, font=tf)
    y = 54
    lh = f.size + 9
    visible = lines[-((H - 70) // lh):]
    for text, col in visible:
        d.text((PAD, y), text, fill=col, font=f)
        y += lh
    return im


def main(src: str, dst: str) -> None:
    f = font(19)
    width = (W - 2 * PAD) // int(f.getlength("m"))
    frames, durations, screen = [], [], []
    title = "slothlens · 2 vCPU · 4 GB RAM · no GPU"
    for raw in Path(src).read_text(encoding="utf-8").splitlines():
        line = clean(raw.rstrip())
        if line.startswith("~~ "):
            card = render(screen + [("", FG), (f"   ⏳ {line[3:]}", DIM)], f, title)
            frames.append(card); durations.append(1400)
            continue
        if line.startswith("$ "):
            for i in range(2, len(line) + 1, 3):
                frames.append(render(screen + [(line[:i] + "▌", GREEN)], f, title)); durations.append(45)
            screen.append((line, GREEN))
            frames.append(render(screen, f, title)); durations.append(500)
            continue
        for part in wrap(line, width):
            screen.append((part, color_for(line)))
        frames.append(render(screen, f, title)); durations.append(260)
    durations[-1] = 4500
    frames = [fr.convert("P", palette=Image.ADAPTIVE, colors=32) for fr in frames]
    frames[0].save(dst, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)
    print(f"wrote {dst}: {len(frames)} frames, {sum(durations) / 1000:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
